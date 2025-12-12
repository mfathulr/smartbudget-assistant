"""Configuration module for Financial Advisor"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "backend" / "schema.sql"

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Database configuration - PostgreSQL (Neon) ONLY
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required! "
        "Please set DATABASE_URL in your .env file with your Neon PostgreSQL connection string."
    )

# Neon uses postgres://, but psycopg2 needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DB_TYPE = "postgresql"  # Always PostgreSQL

# Email configuration (SMTP)
SMTP_HOST = os.environ.get("SMTP_HOST")  # e.g., smtp.gmail.com
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@financialadvisor.com")
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")

# Flask config
FLASK_CONFIG = {
    "SQLALCHEMY_DATABASE_URI": DATABASE_URL or f"sqlite:///{DB_PATH}",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-key"),
}

# reCAPTCHA (optional)
RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "")

# OCR / Vision AI Configuration
ENABLE_OCR_FEATURE = os.environ.get("ENABLE_OCR_FEATURE", "true").lower() == "true"
GOOGLE_VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY") or GOOGLE_API_KEY
