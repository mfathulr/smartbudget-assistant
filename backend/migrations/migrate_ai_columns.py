#!/usr/bin/env python3
"""
Migration script untuk menambahkan kolom ai_provider dan ai_model ke tabel users.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load .env file from parent directory
backend_dir = Path(__file__).resolve().parent.parent
env_file = backend_dir / ".env"
load_dotenv(env_file)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("[1] Checking if ai_provider column exists...")
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'ai_provider'
    """)

    if cur.fetchone():
        print("    ✅ ai_provider column already exists")
    else:
        print("    ❌ ai_provider column not found - adding...")
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN ai_provider TEXT DEFAULT 'google'
        """)
        print("    ✅ ai_provider column added")

    print("[2] Checking if ai_model column exists...")
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'ai_model'
    """)

    if cur.fetchone():
        print("    ✅ ai_model column already exists")
    else:
        print("    ❌ ai_model column not found - adding...")
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN ai_model TEXT DEFAULT 'gemini-2.0-flash-lite'
        """)
        print("    ✅ ai_model column added")

    conn.commit()
    print("\n✅ Migration completed successfully!")

    # Verify
    print("\n[3] Verifying users table structure:")
    cur.execute("""
        SELECT column_name, data_type, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        ORDER BY ordinal_position
    """)

    for col in cur.fetchall():
        col_name, data_type, default = col
        default_str = f" (DEFAULT: {default})" if default else ""
        print(f"    - {col_name}: {data_type}{default_str}")

    cur.close()
    conn.close()

except psycopg2.Error as e:
    print(f"❌ Database error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
