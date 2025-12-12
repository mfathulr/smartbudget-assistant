"""Initialize database and create admin user"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from database import init_db
from config import FLASK_CONFIG

app = Flask(__name__)
app.config.update(FLASK_CONFIG)
db = SQLAlchemy(app)

with app.app_context():
    init_db()
    print("\n✅ Database initialized successfully!")

    # Auto-enable OCR for all admin users
    try:
        result = db.session.execute(
            text("UPDATE users SET ocr_enabled = true WHERE role = 'admin'")
        )
        db.session.commit()
        if result.rowcount > 0:
            print(f"🔓 OCR enabled for {result.rowcount} admin user(s)")
    except Exception as e:
        print(f"⚠️  Warning: Could not enable OCR for admins: {e}")
        db.session.rollback()

    admin_email = os.getenv("ADMIN_EMAIL", "admin@smartbudget.app")
    print("👤 Admin account created/verified")
    print(f"   Email: {admin_email}")
    print("   Password: Set via ADMIN_PASSWORD environment variable")
