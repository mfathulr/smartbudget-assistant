"""OCR feature migration"""

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
        # Check if columns already exist
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("users")]

        if "ocr_enabled" not in columns:
            print("Adding ocr_enabled column...")
            db.session.execute(
                text("ALTER TABLE users ADD COLUMN ocr_enabled BOOLEAN DEFAULT false")
            )
            db.session.commit()
            print("✓ Added ocr_enabled column")
        else:
            print("✓ ocr_enabled column already exists")

        if "image_urls" not in columns:
            print("Adding image_urls column...")
            db.session.execute(
                text("ALTER TABLE users ADD COLUMN image_urls TEXT DEFAULT NULL")
            )
            db.session.commit()
            print("✓ Added image_urls column")
        else:
            print("✓ image_urls column already exists")

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        db.session.rollback()
