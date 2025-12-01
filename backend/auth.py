"""Authentication middleware and decorators"""

from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, g
from database import get_db


def get_current_user():
    """Get current authenticated user from session token with expiry check"""
    db = get_db()

    # Support multiple token sources: Authorization header (Bearer), X-Session-Token, or cookie
    token = None
    auth_header = request.headers.get("Authorization")
    print(f"[AUTH DEBUG] Authorization header: {auth_header}")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        print(f"[AUTH DEBUG] Token from Bearer: {token[:20]}...")
    if not token:
        token = request.headers.get("X-Session-Token")
        if token:
            print(f"[AUTH DEBUG] Token from X-Session-Token: {token[:20]}...")
    if not token:
        token = request.cookies.get("session_token")
        if token:
            print(f"[AUTH DEBUG] Token from cookie: {token[:20]}...")

    if not token:
        print("[AUTH DEBUG] No token found in any source!")
        return None

    # Database query
    cur = db.execute(
        """
        SELECT users.id, users.name, users.email, users.role, sessions.expires_at
        FROM sessions JOIN users ON sessions.user_id = users.id
        WHERE sessions.session_token = ?
        """,
        (token,),
    )
    row = cur.fetchone()

    if not row:
        return None

    # Expiry check
    expires_at = row["expires_at"]
    if expires_at:
        try:
            # Handle both datetime object (PostgreSQL) and string (SQLite)
            if isinstance(expires_at, datetime):
                exp_dt = expires_at
            else:
                # SQLite returns string; attempt parse
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", ""))
                except ValueError:
                    exp_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")

            # Compare in WIB to match stored timezone policy
            wib_now = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None)
            if exp_dt < wib_now:
                # Session expired -> remove it
                db.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
                db.commit()
                return None
        except Exception:
            # If parsing fails treat as invalid / expired
            db.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
            db.commit()
            return None

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
    }


def require_login(f):
    """Decorator to require authentication"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        g.user = user
        return f(*args, **kwargs)

    return wrapper


def require_admin(f):
    """Decorator to require admin role"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "Forbidden"}), 403
        g.user = user
        return f(*args, **kwargs)

    return wrapper
