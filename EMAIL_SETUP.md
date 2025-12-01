# Email Configuration Guide

## Mengapa Muncul "Tautan reset (pengujian lokal)"?

Tautan tersebut muncul karena sistem bekerja dalam **mode pengujian/development**. Saat SMTP email belum dikonfigurasi, sistem akan otomatis menampilkan tautan reset password di halaman untuk memudahkan testing tanpa perlu setup email server dulu.

## Cara Mengaktifkan Pengiriman Email

### 1. Menggunakan Gmail (Recommended untuk Testing)

#### A. Setup App Password di Gmail
1. Buka Google Account: https://myaccount.google.com/
2. Pilih **Security** → **2-Step Verification** (aktifkan jika belum)
3. Scroll ke bawah, pilih **App passwords**
4. Generate password baru untuk "Mail" / "Other (Custom name)"
5. Salin 16-digit app password yang muncul

#### B. Konfigurasi di `.env`
Buka file `backend/.env` dan tambahkan:

```env
# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=noreply@financialadvisor.com
APP_URL=http://localhost:8000
```

**Ganti:**
- `your-email@gmail.com` → Email Gmail Anda
- `xxxx xxxx xxxx xxxx` → App password yang tadi di-generate
- `APP_URL` → URL aplikasi (untuk production ganti dengan domain asli)

### 2. Menggunakan Email Provider Lain

#### Outlook/Hotmail
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```env
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

#### Mailgun (Recommended untuk Production)
```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-password
```

#### SendGrid
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

### 3. Testing

Setelah konfigurasi:

1. **Restart server backend:**
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   python main.py
   ```

2. **Test forgot password:**
   - Buka http://localhost:8000/forgot.html
   - Masukkan email yang terdaftar
   - Submit

3. **Cek hasil:**
   - Jika SMTP berhasil: Email akan dikirim ke inbox (cek Spam juga)
   - Jika SMTP gagal/belum setup: Tautan reset akan muncul di halaman (mode dev)

## Troubleshooting

### Email Tidak Terkirim
1. Pastikan App Password benar (untuk Gmail)
2. Cek apakah 2FA aktif (Gmail wajib)
3. Cek firewall/antivirus tidak memblokir port 587
4. Lihat log error di terminal backend

### Email Masuk ke Spam
- Ini normal untuk development
- Untuk production, gunakan:
  - Domain verified (SPF, DKIM, DMARC)
  - Professional email service (Mailgun, SendGrid)

### Testing Tanpa Email (Dev Mode)
- Kosongkan atau hapus konfigurasi SMTP di `.env`
- Tautan reset akan otomatis muncul di halaman forgot password
- Klik tautan tersebut untuk langsung ke halaman reset

## Production Checklist

Untuk deployment production:

- [ ] Gunakan email service profesional (Mailgun/SendGrid/AWS SES)
- [ ] Set `APP_URL` ke domain production
- [ ] Gunakan `SMTP_FROM` dengan domain terverifikasi
- [ ] Jangan commit `.env` ke Git (sudah ada di `.gitignore`)
- [ ] Test email di staging environment dulu
- [ ] Setup email templates yang lebih cantik (optional)
- [ ] Add email logging/monitoring

## Keamanan

⚠️ **PENTING:**
- **Jangan** commit API keys/passwords ke Git
- **Jangan** share App Password
- Gunakan environment variables untuk semua credentials
- Untuk production, gunakan secret management (HashiCorp Vault, AWS Secrets Manager, dll)

## Support

Jika mengalami masalah:
1. Cek log backend terminal untuk error details
2. Test SMTP credentials dengan tool online seperti https://www.gmass.co/smtp-test
3. Baca dokumentasi provider email yang digunakan
