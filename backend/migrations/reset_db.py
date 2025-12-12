"""Reset database - Drop all tables and reinitialize"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from config import DB_TYPE

if DB_TYPE != "postgresql":
    print("This script is for PostgreSQL only.")
    exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not set!")
    exit(1)

print("=" * 60)
print("🚨 DATABASE RESET SCRIPT 🚨")
print("=" * 60)
print(f"Database: {DATABASE_URL[:50]}...")
print("\nThis will DELETE ALL DATA in the database!")
print("=" * 60)

confirm = input("\nType 'YES' to confirm reset: ")
if confirm != "YES":
    print("Reset cancelled.")
    exit(0)

print("\n🔄 Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("🗑️  Dropping all tables...")

# Drop tables in correct order (reverse of foreign key dependencies)
tables = [
    "llm_log_embeddings",
    "llm_logs",
    "chat_sessions",
    "llm_memory_summary",
    "llm_memory_config",
    "sessions",
    "savings_goals",
    "transactions",
    "users",
]

for table in tables:
    try:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        print(f"  ✅ Dropped {table}")
    except Exception as e:
        print(f"  ⚠️  Could not drop {table}: {e}")

conn.commit()
print("\n✅ All tables dropped!")

cur.close()
conn.close()

print("\n🔧 Reinitializing database with schema.sql...")

# Reinitialize database
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
    print("✅ Database reinitialized!")

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

print("=" * 60)
print("✅ Database reset complete!")
