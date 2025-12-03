"""Financial Advisor - Main Application"""

import json
import re
import secrets
from datetime import datetime, date, timedelta, timezone

try:
    import google.generativeai as genai
except Exception:
    genai = None  # Optional: allow running without Google Generative AI
from flask import Flask, request, jsonify, send_from_directory, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from openai import OpenAI
import requests as http_requests

# Import modular components
from config import (
    BASE_DIR,
    FLASK_CONFIG,
    GOOGLE_API_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM,
    APP_URL,
    RECAPTCHA_SITE_KEY,
    RECAPTCHA_SECRET_KEY,
)

# SendGrid API key (optional, fallback to SMTP)
import os
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
from database import get_db, close_db, init_db
from auth import require_login, require_admin

# Translation messages for API responses
MESSAGES = {
    "id": {
        "email_required": "Email harus diisi",
        "email_not_registered": "Email tidak terdaftar",
        "incorrect_password": "Password salah",
        "email_password_required": "Email dan password harus diisi",
        "reset_link_sent": "Jika email terdaftar, link reset telah dikirim.",
        "token_password_required": "Token dan password baru wajib diisi",
        "password_min_length": "Password minimal 6 karakter",
        "invalid_token": "Token tidak valid",
        "token_expired": "Token sudah kadaluarsa",
        "password_reset_success": "Password berhasil direset. Silakan login.",
        "password_reset_failed": "Gagal mereset password",
    },
    "en": {
        "email_required": "Email is required",
        "email_not_registered": "Email is not registered",
        "incorrect_password": "Incorrect password",
        "email_password_required": "Email and password are required",
        "reset_link_sent": "If email is registered, reset link has been sent.",
        "token_password_required": "Token and new password are required",
        "password_min_length": "Password must be at least 6 characters",
        "invalid_token": "Invalid token",
        "token_expired": "Token has expired",
        "password_reset_success": "Password successfully reset. Please login.",
        "password_reset_failed": "Failed to reset password",
    },
}


def get_language():
    """Get language from request (query param or Accept-Language header)"""
    lang = request.args.get("lang") or request.headers.get("Accept-Language", "id")
    if lang.startswith("en"):
        return "en"
    return "id"


def get_message(key, lang=None):
    """Get translated message by key"""
    if lang is None:
        lang = get_language()
    return MESSAGES.get(lang, MESSAGES["id"]).get(key, MESSAGES["id"].get(key, ""))


from helpers import get_month_summary, build_financial_context
from llm_tools import TOOLS_DEFINITIONS
from llm_executor import execute_action
from memory import (
    log_message,
    build_memory_context,
    maybe_update_summary,
    get_memory_summary,
    get_recent_dialogue,
    get_effective_config,
)
from memory import SUMMARY_THRESHOLD, MAX_LOG_CONTEXT, MAX_LOG_SOURCE
from embeddings import ensure_log_embeddings, semantic_search

# Initialize Flask app
app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "public" / "static"),
    static_url_path="/static",
)
app.config.update(FLASK_CONFIG)

db_sqlalchemy = SQLAlchemy(app)
migrate = Migrate(app, db_sqlalchemy)
app.teardown_appcontext(close_db)

# Initialize LLM clients
client = OpenAI()


# === Health Check Endpoint (for keep-alive monitoring) ===
@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """Simple health check endpoint for uptime monitoring"""
    return jsonify(
        {
            "status": "ok",
            "service": "SmartBudget-Assistant",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ), 200


# === Public Config Endpoint (safe values only) ===
@app.route("/api/public-config", methods=["GET"])
def public_config():
    return jsonify(
        {
            "recaptcha_site_key": RECAPTCHA_SITE_KEY or "",
            "recaptcha_enabled": bool(RECAPTCHA_SITE_KEY),
            "recaptcha_server_enforced": bool(RECAPTCHA_SECRET_KEY),
        }
    )


def verify_recaptcha_token(token: str, remote_ip: str = None) -> bool:
    """Verify a reCAPTCHA token with Google.
    Accepts v3 (score >= 0.5) and v2 success.
    Returns True if the token is valid; False otherwise.
    """
    if not RECAPTCHA_SECRET_KEY:
        return False
    try:
        payload = {
            "secret": RECAPTCHA_SECRET_KEY,
            "response": token,
        }
        if remote_ip:
            payload["remoteip"] = remote_ip
        r = http_requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=payload,
            timeout=5,
        )
        data = r.json()
        if not data.get("success"):
            return False
        # For v3, a score is provided
        score = data.get("score")
        if score is None:
            return True
        return float(score) >= 0.5
    except Exception:
        return False


# --- Email Utilities ---
def send_email_sendgrid(to_email: str, subject: str, html_content: str, text_content: str) -> bool:
    """Send email via SendGrid API. Returns True if sent, False on error."""
    if not SENDGRID_API_KEY:
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=SMTP_FROM or "noreply@smartbudget.app",
            to_emails=to_email,
            subject=subject,
            plain_text_content=text_content,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"[SENDGRID] Email sent to {to_email} (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"[SENDGRID ERROR] Failed to send email: {e}")
        return False


def send_otp_email(to_email: str, otp_code: str, user_name: str) -> bool:
    """Send OTP verification email. Returns True if sent, False if dev/no SMTP or error."""
    greeting = f"Halo {user_name}," if user_name else "Halo,"
    subject = "Kode Verifikasi Registrasi - SmartBudget Assistant"
    
    html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 40px 20px;">
              <tr>
                <td align="center">
                  <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    <tr>
                      <td style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); padding: 40px 30px; text-align: center;">
                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">🔐 Verifikasi Email</h1>
                        <p style="margin: 8px 0 0 0; color: #bfdbfe; font-size: 14px; font-weight: 400;">SmartBudget Assistant</p>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 40px 30px;">
                        <p style="margin: 0 0 20px 0; color: #111827; font-size: 16px; line-height: 1.6;">{greeting}</p>
                        <p style="margin: 0 0 20px 0; color: #374151; font-size: 15px; line-height: 1.6;">Terima kasih telah mendaftar di SmartBudget Assistant! Gunakan kode verifikasi berikut untuk menyelesaikan pendaftaran Anda:</p>
                        <div style="background: #f3f4f6; border-radius: 12px; padding: 24px; text-align: center; margin: 30px 0;">
                          <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Kode Verifikasi</p>
                          <p style="margin: 0; color: #1e40af; font-size: 36px; font-weight: 700; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</p>
                        </div>
                        <p style="margin: 0 0 20px 0; color: #374151; font-size: 15px; line-height: 1.6;">Kode ini akan kedaluwarsa dalam <strong>10 menit</strong>.</p>
                        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 8px; margin: 24px 0;">
                          <p style="margin: 0; color: #92400e; font-size: 14px; line-height: 1.6;">⚠️ <strong>Jangan bagikan kode ini</strong> kepada siapa pun, termasuk tim SmartBudget Assistant. Kami tidak akan pernah meminta kode verifikasi Anda.</p>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td style="background: #f9fafb; padding: 24px 30px; border-top: 1px solid #e5e7eb;">
                        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 13px; line-height: 1.5;">Jika Anda tidak mendaftar di SmartBudget Assistant, abaikan email ini dengan aman.</p>
                        <p style="margin: 0; color: #9ca3af; font-size: 12px;">© 2025 SmartBudget Assistant</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
    
    text = f"""{greeting}

Terima kasih telah mendaftar di SmartBudget Assistant!

Kode Verifikasi Anda: {otp_code}

Kode ini akan kedaluwarsa dalam 10 menit.

Jangan bagikan kode ini kepada siapa pun.

Jika Anda tidak mendaftar, abaikan email ini.

© 2025 SmartBudget Assistant"""

    # Try SendGrid first
    print(f"[EMAIL] Sending OTP to {to_email}...")
    if send_email_sendgrid(to_email, subject, html, text):
        return True
    
    # Fallback to SMTP if SendGrid not configured
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        print(f"[DEV MODE] OTP for {to_email}: {otp_code}")
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())

        print(f"[EMAIL] OTP sent via SMTP to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send OTP: {e}")
        print(f"[DEV MODE FALLBACK] OTP for {to_email}: {otp_code}")
        return False


def send_password_reset_email(
    to_email: str, reset_token: str, user_name: str = None
) -> bool:
    """Send password reset email. Returns True if email was sent, False if dev mode."""
    
    print(f"[EMAIL] Sending reset email to {to_email}...")
    
    reset_url = f"{APP_URL}/reset-password.html?token={reset_token}"
    greeting = f"Halo {user_name}," if user_name else "Halo,"
    subject = "Reset Password - SmartBudget Assistant"
    
    # HTML email body with professional design
    html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 40px 20px;">
              <tr>
                <td align="center">
                  <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                      <td style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); padding: 40px 30px; text-align: center;">
                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                          🔐 Reset Password
                        </h1>
                        <p style="margin: 8px 0 0 0; color: #bfdbfe; font-size: 14px; font-weight: 400;">
                          SmartBudget Assistant
                        </p>
                      </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                      <td style="padding: 40px 30px;">
                        <p style="margin: 0 0 20px 0; color: #111827; font-size: 16px; line-height: 1.6;">
                          {greeting}
                        </p>
                        <p style="margin: 0 0 20px 0; color: #374151; font-size: 15px; line-height: 1.6;">
                          Kami menerima permintaan untuk mereset password akun SmartBudget Assistant Anda yang terdaftar dengan email <strong>{to_email}</strong>.
                        </p>
                        <p style="margin: 0 0 20px 0; color: #374151; font-size: 15px; line-height: 1.6;">
                          Jika ini adalah Anda, silakan klik tombol di bawah untuk melanjutkan proses reset password. Jika bukan Anda yang meminta, abaikan email ini dengan aman.
                        </p>
                        
                        <!-- CTA Button -->
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin: 35px 0;">
                          <tr>
                            <td align="center">
                              <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); color: #ffffff; font-size: 16px; font-weight: 600; text-decoration: none; padding: 14px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3);">
                                Reset Password Sekarang
                              </a>
                            </td>
                          </tr>
                        </table>
                        
                        <p style="margin: 25px 0 10px 0; color: #6b7280; font-size: 14px; line-height: 1.5;">
                          Atau salin dan tempel tautan berikut ke browser Anda:
                        </p>
                        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px 16px; word-break: break-all;">
                          <a href="{reset_url}" style="color: #2563eb; font-size: 13px; text-decoration: none;">
                            {reset_url}
                          </a>
                        </div>
                      </td>
                    </tr>
                    
                    <!-- Security Notice -->
                    <tr>
                      <td style="padding: 0 30px 40px 30px;">
                        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px 20px; border-radius: 6px;">
                          <p style="margin: 0; color: #92400e; font-size: 13px; line-height: 1.5;">
                            <strong>⚠️ Penting:</strong> Tautan ini akan kedaluwarsa dalam <strong>1 jam</strong> untuk keamanan akun Anda.
                          </p>
                        </div>
                      </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                      <td style="background-color: #f9fafb; padding: 30px; border-top: 1px solid #e5e7eb;">
                        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 13px; line-height: 1.5;">
                          Jika Anda <strong>tidak meminta</strong> reset password, Anda dapat mengabaikan email ini dengan aman. Password Anda tidak akan diubah.
                        </p>
                        <p style="margin: 0; color: #9ca3af; font-size: 12px; line-height: 1.5;">
                          Email ini dikirim secara otomatis, mohon jangan membalas email ini.
                        </p>
                        <hr style="margin: 20px 0; border: none; border-top: 1px solid #e5e7eb;">
                        <p style="margin: 0; color: #9ca3af; font-size: 11px; text-align: center;">
                          © 2025 SmartBudget Assistant. All rights reserved.
                        </p>
                      </td>
                    </tr>
                    
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
    
    # Plain text alternative
    text = f"""
SmartBudget Assistant - Reset Password
{"=" * 50}

Halo,

Kami menerima permintaan untuk mereset password akun SmartBudget Assistant Anda.

Klik tautan berikut untuk mereset password:
{reset_url}

PENTING:
• Tautan ini akan kedaluwarsa dalam 1 jam
• Jika Anda tidak meminta reset password, abaikan email ini
• Password Anda tidak akan diubah kecuali Anda mengklik tautan di atas

---
Email otomatis - Jangan balas email ini
© 2025 SmartBudget Assistant
        """
    
    # Try SendGrid first
    if send_email_sendgrid(to_email, subject, html, text):
        return True
    
    # Fallback to SMTP if SendGrid not configured
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        print(
            f"[EMAIL] Dev mode - No email provider configured. Host:{SMTP_HOST}, User:{SMTP_USER}"
        )
        return False
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())

        print(f"[EMAIL] ✅ Reset email sent via SMTP to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send reset email: {e}")
        return False


# --- Utilities ---
def _normalize_date_iso(value: str | None) -> str | None:
    """Normalize natural-language date to ISO YYYY-MM-DD if possible.
    Returns ISO string or None if cannot parse.
    """
    if not value:
        return None
    s = (value or "").strip()
    import re as _re

    if _re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    try:
        import dateparser as _dp  # type: ignore

        dt = _dp.parse(s, locales=["id", "en"]) if _dp else None
        if dt:
            return dt.date().isoformat()
    except Exception:
        pass
    return None


def _wib_today_iso() -> str:
    from datetime import datetime, timedelta, timezone

    wib = timezone(timedelta(hours=7))
    return datetime.now(wib).date().isoformat()


# === SIMPLE FALLBACK INTENT PARSER ===
def parse_financial_intent(raw_text: str, today_str: str):
    """Very lightweight parser to extract an expense/income when LLM did not call a tool.
    Returns dict compatible with add_transaction tool or None.
    Patterns handled:
    - record/ catat/ tambah (income|expense) ... (for) <amount>
    - '<amount>' plus keywords like 'expense', 'pengeluaran', 'pemasukan'
    - amount expressions with 'ribu', 'juta', 'jt', or separators '.'/','
    """
    text = raw_text.lower()
    # Determine type
    tx_type = None
    if any(k in text for k in ["expense", "pengeluaran", "biaya"]):
        tx_type = "expense"
    elif any(k in text for k in ["income", "pemasukan", "masuk"]):
        tx_type = "income"
    if not tx_type:
        return None

    # Amount extraction
    # Examples: 25,000 ; 25.000 ; 25000 ; 25 ribu ; 14 juta ; 14jt ; 30k
    amt = None
    # juta / jt pattern (e.g. 14jt, 14 juta, 2.5 juta)
    m_juta = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:juta|jt)\b", text)
    if m_juta:
        base = (
            m_juta.group(1).replace(".", ".").replace(",", ".")
        )  # normalize to dot decimal
        try:
            amt = float(base) * 1000000
        except ValueError:
            pass
    # ribu pattern
    if amt is None:
        m_ribu = re.search(r"(\d+[\d\.,]*)\s*ribu", text)
        if m_ribu:
            base = m_ribu.group(1).replace(".", "").replace(",", "")
            try:
                amt = float(base) * 1000
            except ValueError:
                pass
    # plain number with thousand separators
    if amt is None:
        m_num = re.search(r"(\d{1,3}(?:[\.,]\d{3})+|\d{3,})", text)
        if m_num:
            num_raw = m_num.group(1).replace(".", "").replace(",", "")
            try:
                amt = float(num_raw)
            except ValueError:
                pass
    # short forms like 25k
    if amt is None:
        m_k = re.search(r"(\d+(?:\.\d+)?)\s*k\b", text)
        if m_k:
            try:
                amt = float(m_k.group(1)) * 1000
            except ValueError:
                pass
    if amt is None:
        return None
    if amt <= 0:
        return None

    # Category heuristics
    category = "Umum"
    if any(w in text for w in ["coffee", "kopi", "cafe"]):
        category = "Makan"
    elif any(w in text for w in ["food", "makan", "resto", "lunch", "dinner"]):
        category = "Makan"
    elif any(w in text for w in ["gaji", "salary", "payroll"]):
        category = "Gaji"
    elif any(w in text for w in ["transport", "gojek", "grab", "bus"]):
        category = "Transport"

    # Account detection (fallback: Cash)
    account = "Cash"
    account_keywords = {
        "maybank": "Maybank",
        "bca": "BCA",
        "seabank": "Seabank",
        "shopeepay": "Shopeepay",
        "gopay": "Gopay",
        "jago": "Jago",
        "isaku": "ISaku",
        "ovo": "Ovo",
        "superbank": "Superbank",
        "blu": "Blu Account (Saving)",
    }
    for keyword, acc_name in account_keywords.items():
        if keyword in text:
            account = acc_name
            break

    # Description: reuse original trimmed to 80 chars
    description = raw_text.strip()[:80]

    return {
        "type": tx_type,
        "amount": amt,
        "category": category,
        "description": description,
        "date": today_str,
        "account": account,
    }


gemini_model = None
if GOOGLE_API_KEY and genai is not None:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    except Exception as e:
        print(f"Warning: Gemini configuration failed: {e}")


# === STATIC ROUTES ===
@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR / "public"), "index.html")


@app.route("/<path:filename>")
def serve_public(filename):
    return send_from_directory(str(BASE_DIR / "public"), filename)


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(str(BASE_DIR / "public" / "uploads"), filename)


# === AUTH ROUTES ===
@app.route("/api/register/send-otp", methods=["POST"])
def register_send_otp():
    db = get_db()
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    print(
        f"[DEBUG] Register OTP request - name: {name}, email: {email}, password len: {len(password) if password else 0}"
    )

    # Skip reCAPTCHA verification for now (keys may be invalid)
    # TODO: Get valid reCAPTCHA v3 keys from https://www.google.com/recaptcha/admin
    # if RECAPTCHA_SECRET_KEY:
    #     captcha_token = (data.get("captchaToken") or "").strip()
    #     if captcha_token:
    #         remote_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    #         verified = verify_recaptcha_token(captcha_token, remote_ip)
    #         print(f"[DEBUG] reCAPTCHA verification: {verified}")
    #         if not verified:
    #             return jsonify({"error": "Captcha verification failed"}), 400

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    cur = db.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        return jsonify({"error": "Email already registered"}), 400

    # Generate 6-digit OTP
    otp_code = str(secrets.randbelow(1000000)).zfill(6)

    # Store OTP with user data (expires in 10 minutes)
    wib = timezone(timedelta(hours=7))
    expires_at = (datetime.now(wib) + timedelta(minutes=10)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    password_hash = generate_password_hash(password)

    # Delete old OTPs for this email
    db.execute("DELETE FROM registration_otps WHERE email = ?", (email,))

    # Insert new OTP
    db.execute(
        "INSERT INTO registration_otps (email, otp_code, name, password_hash, expires_at) VALUES (?, ?, ?, ?, ?)",
        (email, otp_code, name, password_hash, expires_at),
    )
    db.commit()

    # Send OTP email
    email_sent = send_otp_email(email, otp_code, name)

    resp = {"status": "ok", "message": "OTP sent to your email"}
    if not email_sent:
        # Dev mode: expose OTP to client to allow testing without SMTP
        resp["dev_mode"] = True
        resp["otp"] = otp_code
    return jsonify(resp), 200


@app.route("/api/register/verify-otp", methods=["POST"])
def register_verify_otp():
    try:
        db = get_db()
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        otp_code = data.get("otp", "").strip()

        print(f"[DEBUG] Verify OTP - email: {email}, otp: {otp_code}")

        if not email or not otp_code:
            return jsonify({"error": "Email and OTP required"}), 400

        # Get OTP record
        cur = db.execute(
            "SELECT * FROM registration_otps WHERE email = ? AND otp_code = ?",
            (email, otp_code),
        )
        otp_record = cur.fetchone()

        if not otp_record:
            print(f"[DEBUG] No OTP record found for {email} with code {otp_code}")
            return jsonify({"error": "Invalid OTP code"}), 400

        # Check if OTP expired
        wib = timezone(timedelta(hours=7))
        now = datetime.now(wib)

        # Handle both string and datetime types from database
        expires_at = otp_record["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")

        # Ensure timezone is set
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=wib)

        if now > expires_at:
            db.execute("DELETE FROM registration_otps WHERE email = ?", (email,))
            db.commit()
            return jsonify({"error": "OTP expired. Please request a new one"}), 400

        print(f"[DEBUG] Creating user account for {email}")
        # Create user account
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (otp_record["name"], email, otp_record["password_hash"], "user"),
        )

        # Delete used OTP
        db.execute("DELETE FROM registration_otps WHERE email = ?", (email,))
        db.commit()

        print(f"[DEBUG] Registration successful for {email}")
        return jsonify({"status": "ok", "message": "Registration successful"}), 201

    except Exception as e:
        print(f"[ERROR] Verify OTP failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Server error during verification"}), 500


@app.route("/api/login", methods=["POST"])
def login_api():
    db = get_db()
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    remember = bool(data.get("remember"))
    lang = get_language()

    # Skip reCAPTCHA verification for now (keys may be invalid)
    # TODO: Get valid reCAPTCHA v3 keys from https://www.google.com/recaptcha/admin
    # if RECAPTCHA_SECRET_KEY:
    #     captcha_token = (data.get("captchaToken") or "").strip()
    #     if not captcha_token:
    #         return jsonify({"error": "Captcha verification required"}), 400
    #     remote_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    #     if not verify_recaptcha_token(captcha_token, remote_ip):
    #         return jsonify({"error": "Captcha verification failed"}), 400

    if not email or not password:
        return jsonify({"error": get_message("email_password_required", lang)}), 400

    cur = db.execute(
        "SELECT id, name, email, password_hash, role FROM users WHERE email = ?",
        (email,),
    )
    user = cur.fetchone()

    # Check if email exists
    if not user:
        return jsonify({"error": get_message("email_not_registered", lang)}), 404

    # Check if password is correct
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": get_message("incorrect_password", lang)}), 401

    token = secrets.token_urlsafe(32)
    # expiry (WIB): 30 days if remember, else 7 days
    wib = timezone(timedelta(hours=7))
    days = 30 if remember else 7
    expires_at = (datetime.now(wib) + timedelta(days=days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    db.execute(
        "INSERT INTO sessions (user_id, session_token, expires_at) VALUES (?, ?, ?)",
        (user["id"], token, expires_at),
    )
    db.commit()

    return jsonify(
        {
            "status": "ok",
            "token": token,
            "remember": remember,
            "user": {
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
        }
    ), 200


@app.route("/api/logout", methods=["POST"])
@require_login
def logout_api():
    db = get_db()
    token = request.headers.get("X-Session-Token") or request.cookies.get(
        "session_token"
    )
    if token:
        db.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
        db.commit()
    return jsonify({"status": "ok"}), 200


# === PASSWORD RESET ROUTES ===
@app.route("/api/password/forgot", methods=["POST"])
def password_forgot_api():
    db = get_db()
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    lang = get_language()

    if not email:
        return jsonify({"error": get_message("email_required", lang)}), 400

    cur = db.execute("SELECT id, name FROM users WHERE email = ?", (email,))
    row = cur.fetchone()

    # If email not registered, return explicit error (per product request)
    if not row:
        return jsonify({"error": get_message("email_not_registered", lang)}), 404

    user_id = row["id"]
    user_name = row["name"]
    token = secrets.token_urlsafe(32)
    wib = timezone(timedelta(hours=7))
    expires_at = (datetime.now(wib) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Remove any existing tokens for this user
        db.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
        # Insert new token
        db.execute(
            "INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at),
        )
        db.commit()
    except Exception:
        db.rollback()
        # Return server error on DB failure
        return jsonify({"error": "Failed to process reset request"}), 500

    # Try to send email
    email_sent = send_password_reset_email(email, token, user_name)

    response_data = {"status": "ok", "message": get_message("reset_link_sent", lang)}

    # If email not sent (dev mode), include reset URL for testing
    if not email_sent:
        reset_url = f"/reset-password.html?token={token}"
        response_data["reset_url"] = reset_url
        response_data["dev_mode"] = True

    return jsonify(response_data), 200


@app.route("/api/password/reset", methods=["POST"])
def password_reset_api():
    db = get_db()
    data = request.get_json() or {}
    token = (data.get("token") or "").strip()
    new_password = (data.get("password") or "").strip()
    lang = get_language()

    if not token or not new_password:
        return jsonify({"error": get_message("token_password_required", lang)}), 400
    if len(new_password) < 6:
        return jsonify({"error": get_message("password_min_length", lang)}), 400

    cur = db.execute(
        "SELECT user_id, expires_at FROM password_resets WHERE token = ?",
        (token,),
    )
    row = cur.fetchone()
    if not row:
        return jsonify({"error": get_message("invalid_token", lang)}), 400

    # Expiry check
    expires_at = row["expires_at"]
    try:
        if isinstance(expires_at, datetime):
            exp_dt = expires_at
        else:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", ""))
            except ValueError:
                exp_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return jsonify({"error": get_message("invalid_token", lang)}), 400

    wib_now = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None)
    if exp_dt < wib_now:
        # Remove expired token
        db.execute("DELETE FROM password_resets WHERE token = ?", (token,))
        db.commit()
        return jsonify({"error": get_message("token_expired", lang)}), 400

    # Update password and cleanup tokens for this user
    user_id = row["user_id"]
    try:
        password_hash = generate_password_hash(new_password)
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
        )
        db.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
        db.commit()
        return jsonify(
            {"status": "ok", "message": get_message("password_reset_success", lang)}
        ), 200
    except Exception as e:
        db.rollback()
        return jsonify(
            {"error": f"{get_message('password_reset_failed', lang)}: {str(e)}"}
        ), 500


# === PROFILE ROUTES ===
@app.route("/api/me", methods=["GET"])
@require_login
def me_api():
    user = g.user
    db = get_db()
    cur = db.execute(
        "SELECT name, email, avatar_url, phone, bio, role FROM users WHERE id = ?",
        (user["id"],),
    )
    user_data = cur.fetchone()
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "name": user_data["name"],
            "email": user_data["email"],
            "avatar_url": user_data["avatar_url"],
            "phone": user_data["phone"],
            "bio": user_data["bio"],
            "role": user_data["role"],
        }
    ), 200


@app.route("/api/me", methods=["PUT"])
@require_login
def update_profile_api():
    db = get_db()
    user_id = g.user["id"]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    bio = data.get("bio", "").strip()

    if not name:
        return jsonify({"error": "Nama tidak boleh kosong"}), 400

    try:
        db.execute(
            "UPDATE users SET name = ?, phone = ?, bio = ? WHERE id = ?",
            (name, phone, bio, user_id),
        )
        db.commit()

        cur = db.execute(
            "SELECT name, email, avatar_url, phone, bio FROM users WHERE id = ?",
            (user_id,),
        )
        updated_user = cur.fetchone()

        return jsonify(
            {
                "status": "ok",
                "message": "Profil berhasil diperbarui",
                "user": {
                    "name": updated_user["name"],
                    "email": updated_user["email"],
                    "avatar_url": updated_user["avatar_url"],
                    "phone": updated_user["phone"],
                    "bio": updated_user["bio"],
                },
            }
        ), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Gagal memperbarui profil: {str(e)}"}), 500


@app.route("/api/me/password", methods=["PUT"])
@require_login
def update_password_api():
    db = get_db()
    user_id = g.user["id"]
    data = request.get_json() or {}
    current_password = data.get("current_password")
    new_password = data.get("password", "").strip()

    if not new_password:
        return jsonify({"error": "Password baru tidak boleh kosong"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password minimal harus 6 karakter"}), 400

    if current_password:
        cur = db.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
        if not user or not check_password_hash(user["password_hash"], current_password):
            return jsonify({"error": "Password saat ini salah"}), 403

    try:
        password_hash = generate_password_hash(new_password)
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
        )
        db.commit()
        return jsonify({"status": "ok", "message": "Password berhasil diupdate"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Gagal mengupdate password: {str(e)}"}), 500


# === ADMIN ROUTES ===
@app.route("/api/admin/users", methods=["GET", "POST"])
@require_admin
def admin_users_api():
    db = get_db()

    if request.method == "GET":
        cur = db.execute(
            "SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC"
        )
        rows = [
            {
                "id": r["id"],
                "name": r["name"],
                "email": r["email"],
                "role": r["role"],
                "created_at": r["created_at"],
            }
            for r in cur.fetchall()
        ]
        return jsonify(rows), 200

    elif request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        role = data.get("role", "user").strip().lower()

        if not name or not email or not password:
            return jsonify({"error": "Name, email, and password are required"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        if role not in ["admin", "user"]:
            return jsonify({"error": "Invalid role"}), 400

        cur = db.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            return jsonify({"error": "Email already registered"}), 400

        try:
            password_hash = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, password_hash, role),
            )
            db.commit()
            return jsonify(
                {"status": "ok", "message": "User created successfully"}
            ), 201
        except Exception as e:
            db.rollback()
            return jsonify({"error": f"Failed to create user: {str(e)}"}), 500


@app.route("/api/admin/users/<int:user_id>", methods=["PUT", "DELETE"])
@require_admin
def admin_user_detail_api(user_id):
    db = get_db()

    if request.method == "PUT":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        role = data.get("role", "").strip().lower()
        password = data.get("password", "")

        if not name or not email or not role:
            return jsonify({"error": "Name, email, and role are required"}), 400
        if role not in ["admin", "user"]:
            return jsonify({"error": "Invalid role"}), 400

        try:
            if password:
                if len(password) < 6:
                    return jsonify(
                        {"error": "Password must be at least 6 characters"}
                    ), 400
                password_hash = generate_password_hash(password)
                db.execute(
                    "UPDATE users SET name = ?, email = ?, role = ?, password_hash = ? WHERE id = ?",
                    (name, email, role, password_hash, user_id),
                )
            else:
                db.execute(
                    "UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?",
                    (name, email, role, user_id),
                )
            db.commit()
            return jsonify(
                {"status": "ok", "message": "User updated successfully"}
            ), 200
        except Exception as e:
            db.rollback()
            return jsonify({"error": f"Failed to update user: {str(e)}"}), 500

    elif request.method == "DELETE":
        try:
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM savings_goals WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            db.commit()
            return jsonify(
                {"status": "ok", "message": "User deleted successfully"}
            ), 200
        except Exception as e:
            db.rollback()
            return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500


# === TRANSACTION ROUTES ===
@app.route("/api/transactions", methods=["GET", "POST"])
@require_login
def transactions_api():
    user_id = g.user["id"]
    db = get_db()

    if request.method == "POST":
        data = request.get_json() or {}
        raw_date = data.get("date")
        if raw_date:
            nd = _normalize_date_iso(raw_date)
            if not nd:
                return jsonify(
                    {
                        "success": False,
                        "message": "need_date",
                        "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                    }
                ), 400
            date_str = nd
        else:
            date_str = _wib_today_iso()
        tx_type = data.get("type")
        category = data.get("category") or "uncategorized"
        description = data.get("description") or ""
        amount = float(data.get("amount") or 0)
        account = data.get("account") or ""

        # Clarification-friendly validation
        if tx_type not in ("income", "expense", "transfer"):
            return jsonify(
                {
                    "success": False,
                    "message": "need_type",
                    "ask_user": "Apakah ini pemasukan (income), pengeluaran (expense), atau transfer?",
                }
            ), 400
        if amount <= 0:
            return jsonify(
                {
                    "success": False,
                    "message": "need_amount",
                    "ask_user": "Mohon sebutkan jumlah transaksi dalam rupiah (harus > 0).",
                }
            ), 400
        if tx_type == "expense" and not (data.get("category") or "").strip():
            return jsonify(
                {
                    "success": False,
                    "message": "need_category",
                    "ask_user": "Mohon sebutkan kategori pengeluaran (contoh: Makan, Transport, Belanja).",
                }
            ), 400
        if tx_type == "income" and not (data.get("category") or "").strip():
            return jsonify(
                {
                    "success": False,
                    "message": "need_category",
                    "ask_user": "Mohon sebutkan kategori pemasukan (contoh: Gaji, Bonus, Penjualan, Investasi).",
                }
            ), 400

        db.execute(
            """INSERT INTO transactions (user_id, date, type, category, description, amount, account)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date_str, tx_type, category, description, amount, account),
        )
        db.commit()
        return jsonify({"status": "ok"})

    # GET with filters
    params = [user_id]
    where = ["user_id = ?"]

    if request.args.get("account"):
        where.append("account = ?")
        params.append(request.args.get("account"))
    if request.args.get("start_date"):
        where.append("date >= ?")
        params.append(request.args.get("start_date"))
    if request.args.get("end_date"):
        where.append("date <= ?")
        params.append(request.args.get("end_date"))
    if request.args.get("type"):
        where.append("type = ?")
        params.append(request.args.get("type"))
    if request.args.get("category"):
        where.append("category = ?")
        params.append(request.args.get("category"))
    if request.args.get("q"):
        where.append("description LIKE ?")
        params.append(f"%{request.args.get('q')}%")

    sql = f"""SELECT id, date, type, category, description, amount, account, created_at
        FROM transactions WHERE {" AND ".join(where)} ORDER BY date DESC, id DESC"""

    cur = db.execute(sql, params)
    rows = [
        {
            "id": r["id"],
            "date": r["date"],
            "type": r["type"],
            "category": r["category"],
            "description": r["description"],
            "amount": r["amount"],
            "account": r["account"],
            "created_at": r["created_at"],
        }
        for r in cur.fetchall()
    ]
    return jsonify(rows)


@app.route("/api/transactions/<int:tx_id>", methods=["PUT", "DELETE"])
@require_login
def transaction_detail_api(tx_id):
    db = get_db()
    user_id = g.user["id"]

    cur = db.execute(
        "SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id)
    )
    if not cur.fetchone():
        return jsonify({"error": "Transaksi tidak ditemukan"}), 404

    if request.method == "PUT":
        data = request.get_json() or {}
        date_str = data.get("date") or _wib_today_iso()
        tx_type = data.get("type")
        category = data.get("category") or "uncategorized"
        description = data.get("description") or ""
        amount = float(data.get("amount") or 0)
        account = data.get("account") or ""

        if tx_type not in ("income", "expense", "transfer"):
            return jsonify(
                {"error": "type harus 'income', 'expense', atau 'transfer'"}
            ), 400
        if amount <= 0:
            return jsonify({"error": "amount harus > 0"}), 400

        db.execute(
            """UPDATE transactions SET date = ?, type = ?, category = ?, description = ?, amount = ?, account = ?
            WHERE id = ? AND user_id = ?""",
            (date_str, tx_type, category, description, amount, account, tx_id, user_id),
        )
        db.commit()
        return jsonify({"status": "ok", "message": "Transaksi berhasil diupdate"})

    elif request.method == "DELETE":
        db.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id)
        )
        db.commit()
        return jsonify({"status": "ok", "message": "Transaksi berhasil dihapus"})


@app.route("/api/summary", methods=["GET"])
@require_login
def summary_api():
    user_id = g.user["id"]
    today = date.today()
    year = int(request.args.get("year") or today.year)
    month = int(request.args.get("month") or today.month)
    summary = get_month_summary(user_id, year, month)
    return jsonify(summary)


@app.route("/api/balance", methods=["GET"])
@require_login
def balance_api():
    user_id = g.user["id"]
    db = get_db()
    account_filter = request.args.get("account")
    where_clause = "user_id = ? AND type IN ('income', 'expense')"
    params = [user_id]

    if account_filter:
        where_clause += " AND account = ?"
        params.append(account_filter)

    cur = db.execute(
        f"""SELECT SUM(CASE WHEN type = 'income' THEN amount
                           WHEN type = 'expense' THEN -amount
                           ELSE 0 END) AS balance
        FROM transactions WHERE {where_clause}""",
        params,
    )
    row = cur.fetchone()

    def _num(v):
        if v is None:
            return 0
        try:
            return float(v)
        except Exception:
            return 0

    return jsonify({"balance": _num(row["balance"] if row else None)})


@app.route("/api/accounts", methods=["GET"])
@require_login
def accounts_api():
    user_id = g.user["id"]
    db = get_db()
    accounts_list = [
        "Cash",
        "BCA",
        "Maybank",
        "Seabank",
        "Shopeepay",
        "Gopay",
        "Jago",
        "ISaku",
        "Ovo",
        "Superbank",
        "Blu Account (Saving)",
    ]

    accounts = []
    total_all = 0.0
    for acc in accounts_list:
        cur = db.execute(
            """SELECT SUM(CASE WHEN type = 'income' THEN amount
                               WHEN type = 'expense' THEN -amount
                               ELSE amount END) AS balance
            FROM transactions WHERE user_id = ? AND account = ?""",
            (user_id, acc),
        )
        row = cur.fetchone()

        def _num(v):
            if v is None:
                return 0
            try:
                return float(v)
            except Exception:
                return 0

        balance = _num(row["balance"] if row else None)
        accounts.append({"account": acc, "balance": balance})
        total_all += balance

    return jsonify({"accounts": accounts, "total_all": total_all})


@app.route("/api/transfer", methods=["POST"])
@require_login
def transfer_api():
    user_id = g.user["id"]
    db = get_db()
    data = request.get_json() or {}

    amount = float(data.get("amount") or 0)
    from_account = data.get("from_account") or ""
    to_account = data.get("to_account") or ""
    raw_date = data.get("date")
    if raw_date:
        nd = _normalize_date_iso(raw_date)
        if not nd:
            return jsonify(
                {
                    "success": False,
                    "message": "need_date",
                    "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                }
            ), 400
        date_str = nd
    else:
        date_str = _wib_today_iso()
    description = (
        data.get("description") or f"Transfer dari {from_account} ke {to_account}"
    )

    if amount <= 0:
        return jsonify(
            {
                "success": False,
                "message": "need_amount",
                "ask_user": "Mohon sebutkan jumlah transfer dalam rupiah (harus > 0).",
            }
        ), 400
    if not from_account:
        return jsonify(
            {
                "success": False,
                "message": "need_account",
                "ask_user": "Mohon sebutkan akun asal transfer (contoh: BCA, Cash, Gopay).",
            }
        ), 400
    if not to_account:
        return jsonify(
            {
                "success": False,
                "message": "need_account",
                "ask_user": "Mohon sebutkan akun tujuan transfer (contoh: BCA, Cash, Gopay).",
            }
        ), 400
    if from_account == to_account:
        return jsonify(
            {
                "success": False,
                "message": "need_account",
                "ask_user": "Akun asal dan tujuan tidak boleh sama. Mohon pilih akun yang berbeda.",
            }
        ), 400

    try:
        db.execute("BEGIN")
        db.execute(
            """INSERT INTO transactions (user_id, date, type, category, description, amount, account)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                date_str,
                "transfer",
                f"Ke {to_account}",
                description,
                -amount,
                from_account,
            ),
        )
        db.execute(
            """INSERT INTO transactions (user_id, date, type, category, description, amount, account)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                date_str,
                "transfer",
                f"Dari {from_account}",
                description,
                amount,
                to_account,
            ),
        )
        db.commit()
        return jsonify(
            {
                "status": "ok",
                "message": f"Transfer {amount} dari {from_account} ke {to_account} berhasil",
            }
        )
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Transfer gagal: {str(e)}"}), 500


# === SAVINGS ROUTES ===
@app.route("/api/savings", methods=["GET", "POST", "PUT", "DELETE"])
@require_login
def savings_api():
    user_id = g.user["id"]
    db = get_db()

    if request.method == "GET":
        cur = db.execute(
            """SELECT id, name, target_amount, current_amount, description, target_date
            FROM savings_goals WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,),
        )
        rows = [
            {
                "id": r["id"],
                "name": r["name"],
                "target_amount": r["target_amount"],
                "current_amount": r["current_amount"],
                "description": r["description"],
                "target_date": r["target_date"],
                "progress_pct": round(
                    (r["current_amount"] / r["target_amount"] * 100)
                    if r["target_amount"] > 0
                    else 0,
                    1,
                ),
            }
            for r in cur.fetchall()
        ]
        return jsonify(rows)

    elif request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name") or "Untitled Goal"
        target_amount = float(data.get("target_amount") or 0)
        current_amount = float(data.get("current_amount") or 0)
        description = data.get("description") or ""
        target_date = data.get("target_date")

        if target_amount <= 0:
            return jsonify({"error": "target_amount harus > 0"}), 400

        db.execute(
            """INSERT INTO savings_goals (user_id, name, target_amount, current_amount, description, target_date)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, name, target_amount, current_amount, description, target_date),
        )
        db.commit()
        return jsonify({"status": "ok", "message": "Savings goal created"})

    elif request.method == "PUT":
        data = request.get_json() or {}
        goal_id = data.get("id")

        if not goal_id:
            return jsonify({"error": "id harus disediakan"}), 400

        cur = db.execute(
            "SELECT id FROM savings_goals WHERE id = ? AND user_id = ?",
            (goal_id, user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "Target tabungan tidak ditemukan"}), 404

        updates = []
        params = []

        if "name" in data and data["name"]:
            updates.append("name = ?")
            params.append(data["name"])
        if "target_amount" in data and float(data.get("target_amount", 0)) > 0:
            updates.append("target_amount = ?")
            params.append(float(data["target_amount"]))
        if "description" in data:
            updates.append("description = ?")
            params.append(data["description"])
        if "target_date" in data:
            td = (data.get("target_date") or "").strip()
            if td:
                nd = _normalize_date_iso(td)
                if not nd:
                    return jsonify(
                        {
                            "success": False,
                            "message": "need_date",
                            "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                        }
                    ), 400
                td = nd
            updates.append("target_date = ?")
            params.append(td or None)

        if not updates:
            return jsonify(
                {
                    "success": False,
                    "message": "no_updates",
                    "ask_user": "Tidak ada field yang bisa diupdate. Mohon sebutkan field yang ingin diubah (name, target_amount, description, target_date).",
                }
            )

        params.extend([goal_id, user_id])
        sql = f"UPDATE savings_goals SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        db.execute(sql, params)
        db.commit()
        return jsonify({"status": "ok", "message": "Target tabungan berhasil diupdate"})

    elif request.method == "DELETE":
        data = request.get_json() or {}
        goal_id = data.get("id")

        if not goal_id:
            return jsonify({"error": "id harus disediakan"}), 400

        db.execute(
            "DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id)
        )
        db.commit()
        return jsonify({"status": "ok", "message": "Savings goal deleted"})


@app.route("/api/transfer_to_savings", methods=["POST"])
@require_login
def transfer_to_savings_api():
    user_id = g.user["id"]
    db = get_db()
    data = request.get_json() or {}

    amount = float(data.get("amount") or 0)
    from_account = data.get("from_account") or ""
    goal_id = data.get("goal_id")
    raw_date = data.get("date")
    if raw_date:
        nd = _normalize_date_iso(raw_date)
        if not nd:
            return jsonify(
                {
                    "success": False,
                    "message": "need_date",
                    "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                }
            ), 400
        date_str = nd
    else:
        date_str = _wib_today_iso()

    if amount <= 0:
        return jsonify(
            {
                "success": False,
                "message": "need_amount",
                "ask_user": "Mohon sebutkan jumlah yang ingin ditabung (harus > 0).",
            }
        ), 400
    if not from_account:
        return jsonify(
            {
                "success": False,
                "message": "need_account",
                "ask_user": "Mohon sebutkan akun sumber dana (contoh: BCA, Cash, Gopay).",
            }
        ), 400
    if not goal_id:
        return jsonify(
            {
                "success": False,
                "message": "need_goal",
                "ask_user": "Mohon pilih target tabungan yang ingin dituju.",
            }
        ), 400

    try:
        db.execute("BEGIN")

        goal_cur = db.execute(
            "SELECT name, current_amount FROM savings_goals WHERE id = ? AND user_id = ?",
            (goal_id, user_id),
        )
        goal = goal_cur.fetchone()
        if not goal:
            return jsonify({"error": "Target tabungan tidak ditemukan"}), 404

        db.execute(
            """INSERT INTO transactions (user_id, date, type, category, description, amount, account)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                date_str,
                "expense",
                "Tabungan",
                f"Menabung untuk: {goal['name']}",
                amount,
                from_account,
            ),
        )

        new_amount = float(goal["current_amount"]) + float(amount)
        db.execute(
            "UPDATE savings_goals SET current_amount = ? WHERE id = ?",
            (new_amount, goal_id),
        )

        db.commit()
        return jsonify(
            {"status": "ok", "message": "Dana berhasil ditransfer ke tabungan."}
        )
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Transfer ke tabungan gagal: {str(e)}"}), 500


# === LLM CHAT ROUTE ===
@app.route("/api/chat", methods=["POST"])
@require_login
def chat_api():
    user_id = g.user["id"]
    # Use WIB date for prompts
    today = datetime.now(timezone(timedelta(hours=7))).date()
    data = request.get_json() or {}
    user_message = (data.get("message") or "").strip()

    print(f"\n{'=' * 60}")
    print("[DEBUG] === CHAT API ENDPOINT DIPANGGIL ===")
    print(f"[DEBUG] User ID: {user_id}")
    print(f"[DEBUG] User Message: {user_message}")
    print(f"{'=' * 60}\n")

    if not user_message:
        return jsonify({"error": "message kosong"}), 400

    year = int(data.get("year") or today.year)
    month = int(data.get("month") or today.month)
    lang = data.get("lang", "id")
    provider = data.get("model_provider", "google")

    print(f"[DEBUG] Provider: {provider}")
    print(f"[DEBUG] Language: {lang}")
    print(f"[DEBUG] Year/Month: {year}/{month}\n")

    # Get or create session
    session_id = data.get("session_id")
    if not session_id:
        # Create new session
        db = get_db()
        db.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
            (user_id, "New Chat"),
        )
        db.commit()
        cur = db.execute(
            "SELECT id FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        session_id = row["id"] if row else None

    # Log user message with session
    log_message(user_id, "user", user_message, session_id=session_id)

    ctx = build_financial_context(user_id, year, month)
    mem_ctx = build_memory_context(user_id)
    db = get_db()
    row = db.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
    user_name = row["name"] if row else "Teman"

    wib = timezone(timedelta(hours=7))
    time_str = datetime.now(wib).strftime("%H:%M WIB, %A, %d %B %Y")

    if lang == "en":
        base_prompt = (
            f"You are FIN, a concise finance assistant for {user_name}. "
            f"Current time: {time_str}. After executing tools, output status lines (✅/❌) before explanation. "
            f"CRITICAL RULES:\n"
            f"1. For INCOME: 'category' is REQUIRED (e.g., Salary, Bonus, Sales). ASK if not specified.\n"
            f"2. For EXPENSE: 'category' is required. ASK if unclear.\n"
            f"3. For TRANSFER: Both 'from_account' and 'to_account' are required. ASK if not specified.\n"
            f"4. For SAVINGS GOAL: 'name' and 'target_amount' are required. ASK if missing.\n"
            f"5. ALWAYS ask for missing information BEFORE executing any database action.\n"
            f"6. NEVER use auto-detected values for critical fields - always confirm with user first."
        )
        user_prompt = f"Today: {today.isoformat()}\nContext:\n{ctx}\n\nMemory:\n{mem_ctx}\n\nUser: {user_message}"
    else:
        base_prompt = (
            f"Kamu FIN, asisten keuangan ringkas untuk {user_name}. "
            f"Waktu: {time_str}. Setelah eksekusi tool tampilkan baris status (✅/❌) sebelum penjelasan. "
            f"ATURAN KRITIS:\n"
            f"1. Untuk PEMASUKAN: 'category' WAJIB jelas (contoh: Gaji, Bonus, Penjualan). TANYA jika tidak disebutkan.\n"
            f"2. Untuk PENGELUARAN: 'category' wajib ada. TANYA jika tidak jelas.\n"
            f"3. Untuk TRANSFER: 'from_account' dan 'to_account' wajib. TANYA jika tidak disebutkan.\n"
            f"4. Untuk TARGET TABUNGAN: 'name' dan 'target_amount' wajib. TANYA jika tidak ada.\n"
            f"5. SELALU tanya informasi yang kurang SEBELUM eksekusi aksi database.\n"
            f"6. JANGAN gunakan nilai auto-detected untuk field kritis - selalu konfirmasi dengan user dulu."
        )
        user_prompt = f"Tanggal: {today.isoformat()}\nKonteks:\n{ctx}\n\nMemori:\n{mem_ctx}\n\nUser: {user_message}"

    # PROVIDER: OPENAI
    if provider == "openai":
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=TOOLS_DEFINITIONS,
                tool_choice="auto",
            )
            msg = resp.choices[0].message

            if msg.tool_calls:
                print(f"\n{'=' * 60}")
                print("[DEBUG] LLM memanggil TOOL(s)!")
                print(f"[DEBUG] Jumlah tool calls: {len(msg.tool_calls)}")
                print(f"{'=' * 60}\n")

                results = []
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)

                    print(f"\n{'=' * 60}")
                    print(f"[DEBUG] Tool Call: {fn_name}")
                    print(f"[DEBUG] Arguments: {fn_args}")
                    print(f"{'=' * 60}\n")

                    result = execute_action(user_id, fn_name, fn_args)
                    results.append(result)

                    print(f"\n{'=' * 60}")
                    print(f"[DEBUG] Tool Result: {result}")
                    print(f"{'=' * 60}\n")

                summary = "\n".join(
                    [
                        ("✅" if r["success"] else "❌") + " " + r["message"]
                        for r in results
                    ]
                )
                # If any tool signals clarification, ask user immediately
                clarification_types = [
                    "need_category",
                    "need_type",
                    "need_amount",
                    "need_account",
                    "need_name",
                    "need_goal",
                    "need_date",
                    "no_updates",
                ]
                any_ask = next(
                    (
                        r.get("ask_user")
                        for r in results
                        if (not r["success"]) and r.get("ask_user")
                    ),
                    None,
                )
                if any_ask:
                    log_message(
                        user_id,
                        "assistant",
                        any_ask,
                        {"awaiting_clarification": True},
                        session_id=session_id,
                    )
                    return jsonify({"answer": any_ask, "session_id": session_id}), 200
                needs_clarification = any(
                    (not r["success"]) and (r.get("message") in clarification_types)
                    for r in results
                )
                if needs_clarification:
                    clarification_msg = next(
                        (
                            r.get("ask_user")
                            for r in results
                            if r.get("message") in clarification_types
                        ),
                        "Mohon lengkapi informasi yang diperlukan.",
                    )
                    log_message(
                        user_id,
                        "assistant",
                        clarification_msg,
                        {"awaiting_clarification": True},
                        session_id=session_id,
                    )
                    return jsonify(
                        {"answer": clarification_msg, "session_id": session_id}
                    ), 200

                # If any failure without ask_user, return only summary to avoid mixed messages
                if any(not r["success"] for r in results):
                    log_message(user_id, "assistant", summary, session_id=session_id)
                    maybe_update_summary(user_id)
                    return jsonify({"answer": summary, "session_id": session_id}), 200

                # All good → add a brief explanation
                explain_prompt = (
                    "Ringkas hasil (maks 5 kalimat) tanpa ubah simbol."
                    if lang != "en"
                    else "Summarize results (max 5 sentences) keep symbols."
                )
                follow = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": base_prompt},
                        {"role": "assistant", "content": summary},
                        {"role": "user", "content": explain_prompt},
                    ],
                )
                answer = summary + "\n\n" + follow.choices[0].message.content.strip()
                log_message(user_id, "assistant", answer, session_id=session_id)
                maybe_update_summary(user_id)
                return jsonify({"answer": answer, "session_id": session_id}), 200

            # Fallback: no tool calls
            # DISABLED auto-parse untuk mencegah double recording
            # Biarkan LLM handle dengan response text biasa
            answer = msg.content
            log_message(user_id, "assistant", answer, session_id=session_id)
            maybe_update_summary(user_id)
            return jsonify({"answer": answer, "session_id": session_id}), 200

        except Exception as e:
            return jsonify({"error": f"OpenAI error: {e}"}), 500

    # PROVIDER: GEMINI
    if provider == "google" and gemini_model:
        try:
            safety = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ]
            hint = """Jika perlu lakukan aksi kembalikan JSON dalam blok ```json``` dengan field 'action' dan 'data'.

ATURAN KRITIS - WAJIB DIIKUTI:
1. PEMASUKAN (income/record_income):
   - 'amount' WAJIB
   - 'category' WAJIB dan harus spesifik (Gaji, Bonus, Penjualan, Investasi - BUKAN "Lainnya")
   - Jika kategori tidak disebutkan, TANYA DULU jangan langsung catat

2. PENGELUARAN (expense/record_expense):
   - 'amount' WAJIB
   - 'category' WAJIB (Makan, Transport, Belanja, dll.)
   - Jika tidak jelas, TANYA DULU

3. TRANSFER (transfer_funds):
   - 'amount' WAJIB
   - 'from_account' WAJIB (akun sumber)
   - 'to_account' WAJIB (akun tujuan)
   - Jika ada yang kurang, TANYA DULU

4. TARGET TABUNGAN (create_savings_goal):
   - 'name' WAJIB (nama target)
   - 'target_amount' WAJIB (jumlah target)
   - Jika ada yang kurang, TANYA DULU

5. TRANSFER KE TABUNGAN (transfer_to_savings):
   - 'amount' WAJIB
   - 'from_account' WAJIB
   - 'goal_id' WAJIB (ID target tabungan)
   - Jika ada yang kurang, TANYA DULU

PRINSIP: JANGAN mencatat apapun ke database jika informasi tidak lengkap. TANYA dulu untuk klarifikasi.

Action tersedia:
- add_transaction / record_expense / record_income
- update_transaction (wajib: id)
- delete_transaction (wajib: id)
- transfer_funds
- create_savings_goal
- update_savings_goal (wajib: id)
- transfer_to_savings"""
            prompt = f"{base_prompt}\n\n{user_prompt}\n\n{hint}"

            resp = gemini_model.generate_content(
                prompt, safety_settings=safety, stream=False
            )
            text = resp.text

            jm = re.search(r"```json\s*({.*?})\s*```", text, re.DOTALL)
            if jm:
                try:
                    print(f"\n{'=' * 60}")
                    print("[DEBUG] GEMINI: JSON action block ditemukan!")
                    print(f"[DEBUG] JSON content: {jm.group(1)}")
                    print(f"{'=' * 60}\n")

                    obj = json.loads(jm.group(1))
                    action = obj.get("action")
                    data_obj = obj.get("data", {})

                    print(f"\n{'=' * 60}")
                    print(f"[DEBUG] GEMINI Tool Call: {action}")
                    print(f"[DEBUG] GEMINI Arguments: {data_obj}")
                    print(f"{'=' * 60}\n")

                    res = execute_action(user_id, action, data_obj)

                    print(f"\n{'=' * 60}")
                    print(f"[DEBUG] GEMINI Tool Result: {res}")
                    print(f"{'=' * 60}\n")

                    # Handle special case: need clarification (category, type, amount, account, name, goal, etc.)
                    clarification_types = [
                        "need_category",
                        "need_type",
                        "need_amount",
                        "need_account",
                        "need_name",
                        "need_goal",
                        "need_date",
                        "no_updates",
                    ]
                    if not res["success"] and res.get("message") in clarification_types:
                        answer = res.get(
                            "ask_user", "Mohon lengkapi informasi yang diperlukan."
                        )
                        log_message(
                            user_id,
                            "assistant",
                            answer,
                            {"awaiting_clarification": True},
                            session_id=session_id,
                        )
                        return jsonify(
                            {"answer": answer, "session_id": session_id}
                        ), 200

                    # If tool requests clarification, ask user and stop
                    if (not res.get("success")) and res.get("ask_user"):
                        answer = res.get("ask_user")
                        log_message(
                            user_id,
                            "assistant",
                            answer,
                            {"awaiting_clarification": True},
                            session_id=session_id,
                        )
                        return jsonify(
                            {"answer": answer, "session_id": session_id}
                        ), 200

                    prefix = "✅" if res["success"] else "❌"
                    remaining = text.replace(jm.group(0), "").strip()
                    # On failure, avoid appending model's remaining text to prevent mixed messages
                    if not res["success"]:
                        answer = prefix + " " + res["message"]
                        log_message(user_id, "assistant", answer, session_id=session_id)
                        return jsonify(
                            {"answer": answer, "session_id": session_id}
                        ), 200

                    # Success: include concise remaining text as explanation
                    answer = prefix + " " + res["message"]
                    if remaining:
                        answer += "\n\n" + remaining
                    log_message(user_id, "assistant", answer, session_id=session_id)
                    maybe_update_summary(user_id)
                    return jsonify({"answer": answer, "session_id": session_id}), 200
                except Exception as je:
                    print(f"[DEBUG] Gemini JSON parse error: {je}")

            # Fallback: no JSON action block found
            # DISABLED auto-parse untuk mencegah double recording
            # Biarkan Gemini handle dengan response text biasa
            answer = text
            log_message(user_id, "assistant", answer, session_id=session_id)
            maybe_update_summary(user_id)
            return jsonify({"answer": answer, "session_id": session_id}), 200

        except Exception as ge:
            return jsonify({"error": f"Gemini error: {ge}"}), 500

    return jsonify({"error": "Provider tidak valid"}), 400


# === MEMORY ENDPOINTS ===
@app.route("/api/memory/summary", methods=["GET"])
@require_login
def memory_summary_api():
    user_id = g.user["id"]
    refresh = request.args.get("refresh") == "1"
    if refresh:
        summary = maybe_update_summary(user_id)
    else:
        summary = get_memory_summary(user_id) or maybe_update_summary(user_id)

    db = get_db()
    total_logs = (
        db.execute(
            "SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]
        or 0
    )
    recent = get_recent_dialogue(user_id)
    cfg = get_effective_config(user_id)

    return jsonify(
        {
            "summary_text": summary["summary_text"] if summary else None,
            "interaction_count": summary["interaction_count"] if summary else 0,
            "updated_at": summary["updated_at"] if summary else None,
            "total_logs": total_logs,
            "recent_dialogue": recent,
            "config": cfg,
        }
    ), 200


@app.route("/api/memory/clear", methods=["DELETE"])
@require_login
def memory_clear_api():
    """Clear all chat history and LLM logs for the user to save memory."""
    user_id = g.user["id"]
    db = get_db()

    try:
        # Count logs before deletion for confirmation
        count_row = db.execute(
            "SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ?", (user_id,)
        ).fetchone()
        logs_count = count_row["c"] if count_row else 0

        # Delete embeddings first (foreign key constraint)
        db.execute("DELETE FROM llm_log_embeddings WHERE user_id = ?", (user_id,))

        # Delete logs
        db.execute("DELETE FROM llm_logs WHERE user_id = ?", (user_id,))

        # Delete memory summary
        db.execute("DELETE FROM llm_memory_summary WHERE user_id = ?", (user_id,))

        db.commit()

        return jsonify(
            {
                "status": "ok",
                "message": f"Berhasil menghapus {logs_count} riwayat chat dan memory",
                "deleted_logs": logs_count,
            }
        ), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Gagal menghapus riwayat: {str(e)}"}), 500


@app.route("/api/memory/logs/<int:log_id>", methods=["DELETE"])
@require_login
def memory_delete_log_api(log_id):
    """Delete a specific chat log entry by ID."""
    user_id = g.user["id"]
    db = get_db()

    try:
        # Verify log belongs to user
        cur = db.execute(
            "SELECT id FROM llm_logs WHERE id = ? AND user_id = ?", (log_id, user_id)
        )
        if not cur.fetchone():
            return jsonify({"error": "Log tidak ditemukan atau bukan milik Anda"}), 404

        # Delete embedding first (if exists)
        db.execute("DELETE FROM llm_log_embeddings WHERE log_id = ?", (log_id,))

        # Delete log
        db.execute(
            "DELETE FROM llm_logs WHERE id = ? AND user_id = ?", (log_id, user_id)
        )

        db.commit()

        return jsonify(
            {"status": "ok", "message": "Chat berhasil dihapus", "deleted_id": log_id}
        ), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Gagal menghapus chat: {str(e)}"}), 500


@app.route("/api/memory/logs", methods=["GET", "DELETE"])
@require_login
def memory_logs_api():
    """Get chat history or delete multiple logs by timeframe."""
    user_id = g.user["id"]
    db = get_db()

    if request.method == "GET":
        # Get chat history with optional filters
        limit = int(request.args.get("limit") or 50)
        offset = int(request.args.get("offset") or 0)
        since = request.args.get("since")  # ISO timestamp
        until = request.args.get("until")  # ISO timestamp

        where = ["user_id = ?"]
        params = [user_id]

        if since:
            where.append("created_at >= ?")
            params.append(since)
        if until:
            where.append("created_at <= ?")
            params.append(until)

        sql = f"""SELECT id, role, content, created_at 
                  FROM llm_logs 
                  WHERE {" AND ".join(where)} 
                  ORDER BY created_at DESC 
                  LIMIT ? OFFSET ?"""
        params.extend([limit, offset])

        cur = db.execute(sql, params)
        logs = [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in cur.fetchall()
        ]

        total_count = db.execute(
            f"SELECT COUNT(*) AS c FROM llm_logs WHERE {' AND '.join(where)}",
            params[: len(where)],
        ).fetchone()["c"]

        return jsonify(
            {"logs": logs, "total": total_count, "limit": limit, "offset": offset}
        ), 200

    elif request.method == "DELETE":
        # Delete logs by timeframe or IDs
        data = request.get_json() or {}
        log_ids = data.get("ids")  # Array of log IDs
        since = data.get("since")
        until = data.get("until")

        if log_ids:
            # Delete specific IDs
            placeholders = ",".join(["?"] * len(log_ids))
            params = log_ids + [user_id]

            # Count first
            count_row = db.execute(
                f"SELECT COUNT(*) AS c FROM llm_logs WHERE id IN ({placeholders}) AND user_id = ?",
                params,
            ).fetchone()
            count = count_row["c"] if count_row else 0

            # Delete embeddings
            db.execute(
                f"DELETE FROM llm_log_embeddings WHERE log_id IN ({placeholders})",
                log_ids,
            )

            # Delete logs
            db.execute(
                f"DELETE FROM llm_logs WHERE id IN ({placeholders}) AND user_id = ?",
                params,
            )

            db.commit()
            return jsonify(
                {
                    "status": "ok",
                    "message": f"Berhasil menghapus {count} chat",
                    "deleted_count": count,
                }
            ), 200

        elif since or until:
            # Delete by timeframe
            where = ["user_id = ?"]
            params = [user_id]

            if since:
                where.append("created_at >= ?")
                params.append(since)
            if until:
                where.append("created_at <= ?")
                params.append(until)

            # Count first
            count_row = db.execute(
                f"SELECT COUNT(*) AS c FROM llm_logs WHERE {' AND '.join(where)}",
                params,
            ).fetchone()
            count = count_row["c"] if count_row else 0

            # Get IDs to delete embeddings
            id_rows = db.execute(
                f"SELECT id FROM llm_logs WHERE {' AND '.join(where)}", params
            ).fetchall()
            log_ids_to_delete = [r["id"] for r in id_rows]

            if log_ids_to_delete:
                placeholders = ",".join(["?"] * len(log_ids_to_delete))
                db.execute(
                    f"DELETE FROM llm_log_embeddings WHERE log_id IN ({placeholders})",
                    log_ids_to_delete,
                )

            # Delete logs
            db.execute(f"DELETE FROM llm_logs WHERE {' AND '.join(where)}", params)

            db.commit()
            return jsonify(
                {
                    "status": "ok",
                    "message": f"Berhasil menghapus {count} chat dari timeframe yang dipilih",
                    "deleted_count": count,
                }
            ), 200

        else:
            return jsonify(
                {"error": "Harus menyertakan 'ids' atau 'since'/'until'"}
            ), 400


@app.route("/api/sessions", methods=["GET", "POST"])
@require_login
def sessions_api():
    """Manage chat sessions."""
    user_id = g.user["id"]
    db = get_db()

    if request.method == "GET":
        # List all sessions for user
        cur = db.execute(
            """SELECT s.id, s.title, s.created_at, s.updated_at,
                      COUNT(l.id) as message_count,
                      MAX(l.created_at) as last_message_at
               FROM chat_sessions s
               LEFT JOIN llm_logs l ON s.id = l.session_id
               WHERE s.user_id = ?
               GROUP BY s.id
               ORDER BY s.updated_at DESC""",
            (user_id,),
        )
        sessions = [
            {
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "message_count": r["message_count"] or 0,
                "last_message_at": r["last_message_at"],
            }
            for r in cur.fetchall()
        ]
        return jsonify({"sessions": sessions}), 200

    elif request.method == "POST":
        # Create new session
        data = request.get_json() or {}
        title = data.get("title") or "New Chat"

        db.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
            (user_id, title),
        )
        db.commit()

        cur = db.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        session = cur.fetchone()

        return jsonify(
            {
                "status": "ok",
                "message": "Session created",
                "session": {
                    "id": session["id"],
                    "title": session["title"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                },
            }
        ), 201


@app.route("/api/sessions/<int:session_id>", methods=["GET", "PUT", "DELETE"])
@require_login
def session_detail_api(session_id):
    """Get, update, or delete a specific session."""
    user_id = g.user["id"]
    db = get_db()

    # Verify session belongs to user
    cur = db.execute(
        "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    session = cur.fetchone()
    if not session:
        return jsonify({"error": "Session tidak ditemukan"}), 404

    if request.method == "GET":
        # Get session with messages
        logs_cur = db.execute(
            "SELECT id, role, content, created_at FROM llm_logs WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        messages = [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
            }
            for r in logs_cur.fetchall()
        ]

        return jsonify(
            {
                "session": {
                    "id": session["id"],
                    "title": session["title"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "messages": messages,
                }
            }
        ), 200

    elif request.method == "PUT":
        # Update session title
        data = request.get_json() or {}
        title = data.get("title")

        if not title or not title.strip():
            return jsonify({"error": "Title tidak boleh kosong"}), 400

        db.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (title, session_id, user_id),
        )
        db.commit()

        return jsonify(
            {"status": "ok", "message": "Session title updated", "title": title}
        ), 200

    elif request.method == "DELETE":
        # Delete session (CASCADE will automatically delete llm_logs and llm_log_embeddings)
        try:
            print(f"\n{'=' * 60}")
            print("[DEBUG] DELETE SESSION ENDPOINT CALLED")
            print(f"[DEBUG] Session ID: {session_id}")
            print(f"[DEBUG] User ID: {user_id}")

            # Count logs before deletion for confirmation
            count_row = db.execute(
                "SELECT COUNT(*) AS c FROM llm_logs WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            logs_count = count_row["c"] if count_row else 0
            print(f"[DEBUG] Logs to delete: {logs_count}")

            # Count embeddings before
            emb_row = db.execute(
                """SELECT COUNT(*) AS c FROM llm_log_embeddings 
                   WHERE log_id IN (SELECT id FROM llm_logs WHERE session_id = ?)""",
                (session_id,),
            ).fetchone()
            emb_count = emb_row["c"] if emb_row else 0
            print(f"[DEBUG] Embeddings to delete: {emb_count}")

            # Delete the session (CASCADE handles the rest)
            print("[DEBUG] Executing DELETE FROM chat_sessions...")
            cursor = db.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            # For PostgreSQL, use cursor.rowcount instead of changes()
            affected = cursor.rowcount if hasattr(cursor, "rowcount") else "unknown"
            print(f"[DEBUG] Rows affected: {affected}")

            db.commit()
            print("[DEBUG] ✅ Commit successful")

            # Verify deletion
            verify = db.execute(
                "SELECT COUNT(*) AS c FROM llm_logs WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            remaining = verify["c"] if verify else 0
            print(f"[DEBUG] Logs remaining: {remaining}")
            print(f"{'=' * 60}\n")

            return jsonify(
                {
                    "status": "ok",
                    "message": "Session berhasil dihapus",
                    "deleted_logs": logs_count,
                    "deleted_embeddings": emb_count,
                }
            ), 200

        except Exception as e:
            print(f"[DEBUG] ❌ ERROR: {e}")
            print(f"{'=' * 60}\n")
            db.rollback()
            return jsonify({"error": f"Gagal menghapus session: {str(e)}"}), 500


@app.route("/api/sessions/sync", methods=["GET"])
@require_login
def sync_sessions_api():
    """Auto-cleanup and sync sessions with database.
    Removes empty sessions and orphaned logs.
    """
    user_id = g.user["id"]
    db = get_db()

    deleted_sessions = []
    orphaned_logs = 0

    # 1. Find and delete empty sessions (no messages)
    empty_cur = db.execute(
        """
        SELECT cs.id, cs.title
        FROM chat_sessions cs
        LEFT JOIN llm_logs l ON cs.id = l.session_id
        WHERE cs.user_id = ? AND l.id IS NULL
    """,
        (user_id,),
    )
    empty_sessions = empty_cur.fetchall()

    for session in empty_sessions:
        db.execute("DELETE FROM chat_sessions WHERE id = ?", (session["id"],))
        deleted_sessions.append(
            {"id": session["id"], "title": session["title"], "reason": "empty"}
        )

    # 2. Handle orphaned logs (assign to "Old Messages" session)
    orphan_cur = db.execute(
        "SELECT COUNT(*) AS c FROM llm_logs WHERE user_id = ? AND session_id IS NULL",
        (user_id,),
    )
    orphaned_logs = orphan_cur.fetchone()["c"]

    if orphaned_logs > 0:
        # Create or get "Old Messages" session
        old_session_cur = db.execute(
            "SELECT id FROM chat_sessions WHERE user_id = ? AND title = ?",
            (user_id, "Old Messages"),
        )
        old_session = old_session_cur.fetchone()

        if old_session:
            old_session_id = old_session["id"]
        else:
            db.execute(
                """
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
                (user_id, "Old Messages"),
            )
            old_session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Assign orphaned logs to this session
        db.execute(
            "UPDATE llm_logs SET session_id = ? WHERE user_id = ? AND session_id IS NULL",
            (old_session_id, user_id),
        )

    db.commit()

    return jsonify(
        {
            "status": "ok",
            "deleted_sessions": deleted_sessions,
            "orphaned_logs_migrated": orphaned_logs,
        }
    ), 200


@app.route("/api/sessions/ids", methods=["GET"])
@require_login
def list_session_ids_api():
    """Get list of valid session IDs for current user.
    Used by frontend to verify which sessions exist in DB.
    """
    user_id = g.user["id"]
    db = get_db()

    cur = db.execute(
        "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    sessions = cur.fetchall()

    return jsonify(
        {
            "session_ids": [s["id"] for s in sessions],
            "sessions": [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "created_at": s["created_at"],
                    "updated_at": s["updated_at"],
                }
                for s in sessions
            ],
        }
    ), 200


@app.route("/api/memory/search", methods=["GET"])
@require_login
def memory_search_api():
    user_id = g.user["id"]
    query = (request.args.get("q") or "").strip()
    top_k = int(request.args.get("top_k") or 5)
    if not query:
        return jsonify({"error": "q parameter kosong"}), 400

    # Ensure embeddings exist for recent logs
    stats = ensure_log_embeddings(user_id, batch_size=200)
    results = semantic_search(user_id, query, top_k=top_k)
    return jsonify({"results": results, "embedding_update": stats}), 200


@app.route("/api/memory/config", methods=["GET", "PUT"])
@require_login
def memory_config_api():
    user_id = g.user["id"]
    db = get_db()
    if request.method == "GET":
        cfg = get_effective_config(user_id)
        cur = db.execute(
            "SELECT embedding_provider FROM llm_memory_config WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        embedding_provider = row["embedding_provider"] if row else "openai"
        cfg["embedding_provider"] = embedding_provider
        return jsonify(cfg), 200

    # PUT
    data = request.get_json() or {}
    summary_threshold = data.get("summary_threshold")
    max_log_context = data.get("max_log_context")
    max_source = data.get("max_source")
    embedding_provider = data.get("embedding_provider")

    # Basic validation
    def _pos_int(val, name):
        if val is None:
            return None
        try:
            iv = int(val)
            if iv <= 0:
                raise ValueError
            return iv
        except Exception:
            raise ValueError(f"{name} harus integer > 0")

    try:
        st = _pos_int(summary_threshold, "summary_threshold")
        mc = _pos_int(max_log_context, "max_log_context")
        ms = _pos_int(max_source, "max_source")
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    if embedding_provider and embedding_provider not in ("openai", "local"):
        return jsonify({"error": "embedding_provider harus 'openai' atau 'local'"}), 400

    # Upsert logic
    cur = db.execute(
        "SELECT user_id FROM llm_memory_config WHERE user_id = ?", (user_id,)
    )
    exists = cur.fetchone() is not None
    if exists:
        updates = []
        params = []
        if st is not None:
            updates.append("summary_threshold = ?")
            params.append(st)
        if mc is not None:
            updates.append("max_log_context = ?")
            params.append(mc)
        if ms is not None:
            updates.append("max_source = ?")
            params.append(ms)
        if embedding_provider:
            updates.append("embedding_provider = ?")
            params.append(embedding_provider)
        if not updates:
            return jsonify({"status": "ok", "message": "Tidak ada perubahan"}), 200
        params.append(user_id)
        sql = (
            "UPDATE llm_memory_config SET "
            + ", ".join(updates)
            + ", updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
        )
        db.execute(sql, params)
    else:
        db.execute(
            "INSERT INTO llm_memory_config (user_id, summary_threshold, max_log_context, max_source, embedding_provider) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                st or SUMMARY_THRESHOLD,
                mc or MAX_LOG_CONTEXT,
                ms or MAX_LOG_SOURCE,
                embedding_provider or "openai",
            ),
        )
    db.commit()
    new_cfg = get_effective_config(user_id)
    cur = db.execute(
        "SELECT embedding_provider FROM llm_memory_config WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    new_cfg["embedding_provider"] = row["embedding_provider"] if row else "openai"
    return jsonify({"status": "ok", "config": new_cfg}), 200


# === MAIN ===
if __name__ == "__main__":
    with app.app_context():
        init_db()

    print("\n=== Financial Advisor Backend ===")
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        methods = ", ".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        print(f"  {rule.endpoint:35s} {methods:20s} {rule.rule}")
    print("=================================\n")

    # Startup security/config logs (safe)
    print("[Startup] reCAPTCHA site key present:", bool(RECAPTCHA_SITE_KEY))
    print("[Startup] reCAPTCHA server enforcement:", bool(RECAPTCHA_SECRET_KEY))
    if not RECAPTCHA_SECRET_KEY:
        print(
            "[Startup] Info: reCAPTCHA not enforced (SECRET missing). Login will not require captcha."
        )

    app.run(host="0.0.0.0", port=8000, debug=False)
