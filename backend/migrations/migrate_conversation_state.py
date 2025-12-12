"""Migration script to apply conversation_state table to Neon PostgreSQL"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set!")

# Convert postgres:// to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQL for conversation_state table
MIGRATION_SQL = """
-- Conversation state untuk multi-turn flow management (per session)
CREATE TABLE IF NOT EXISTS conversation_state (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    intent TEXT NOT NULL,
    state TEXT NOT NULL,
    partial_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversation_state_session ON conversation_state(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_state_expires ON conversation_state(expires_at);
"""


def apply_migration():
    """Apply migration to Neon PostgreSQL"""
    try:
        print("🔗 Connecting to Neon PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()

        print("📝 Creating conversation_state table...")
        cur.execute(MIGRATION_SQL)

        print("✅ Migration applied successfully!")
        print("   - Created: conversation_state table")
        print(
            "   - Indexes: idx_conversation_state_session, idx_conversation_state_expires"
        )

        cur.close()
        conn.close()

    except psycopg2.errors.DuplicateTable:
        print("ℹ️  Table already exists, skipping...")
        conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    apply_migration()
