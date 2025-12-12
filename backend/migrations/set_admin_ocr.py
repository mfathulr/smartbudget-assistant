"""Set admin OCR enablement"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FLASK_CONFIG
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config.update(FLASK_CONFIG)
db = SQLAlchemy(app)

with app.app_context():
    try:
        # Enable OCR for all admin users
        result = db.session.execute(
            text("UPDATE users SET ocr_enabled = true WHERE role = 'admin'")
        )
        db.session.commit()
        print(f"✓ Enabled OCR for {result.rowcount} admin user(s)")

        # Show current status
        result = db.session.execute(
            text(
                "SELECT id, name, email, role, ocr_enabled FROM users ORDER BY role DESC, id"
            )
        )
        print("\nCurrent user status:")
        print("-" * 80)
        for row in result:
            status = "✓ Yes" if row.ocr_enabled else "✗ No"
            print(
                f"ID: {row.id:3d} | {row.name:20s} | {row.email:30s} | {row.role:6s} | OCR: {status}"
            )

    except Exception as e:
        print(f"Error: {e}")
        db.session.rollback()
