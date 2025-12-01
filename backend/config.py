"""Configuration module for Financial Advisor"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "finance.db"
SCHEMA_PATH = BASE_DIR / "backend" / "schema.sql"

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Database configuration
# Use DATABASE_URL for PostgreSQL (Neon), fallback to SQLite for local dev
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Neon uses postgres://, but SQLAlchemy needs postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DB_TYPE = "postgresql" if DATABASE_URL else "sqlite"

# Flask config
FLASK_CONFIG = {
    "SQLALCHEMY_DATABASE_URI": DATABASE_URL or f"sqlite:///{DB_PATH}",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-key"),
}
