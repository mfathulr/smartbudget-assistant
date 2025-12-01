"""Reset database - Drop all tables and reinitialize"""

import os
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
print("Run: python main.py")
print("=" * 60)
