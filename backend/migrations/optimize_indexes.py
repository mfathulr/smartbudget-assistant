"""
Database optimization: Add indexes for frequently queried columns
This improves performance of advisor chat loading and other queries
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db


def add_optimization_indexes():
    """Add indexes to optimize advisor chat performance"""
    db = get_db()

    indexes = [
        # llm_logs table - most critical for advisor performance
        "CREATE INDEX IF NOT EXISTS idx_llm_logs_user_id ON llm_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_llm_logs_user_created ON llm_logs(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_llm_logs_session_id ON llm_logs(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_llm_logs_user_session ON llm_logs(user_id, session_id)",
        # chat_sessions table
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC)",
        # transactions table
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, type)",
        # llm_log_embeddings table
        "CREATE INDEX IF NOT EXISTS idx_llm_log_embeddings_user_id ON llm_log_embeddings(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_llm_log_embeddings_log_id ON llm_log_embeddings(log_id)",
        # sessions table (auth)
        "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)",
        # llm_memory_summary table
        "CREATE INDEX IF NOT EXISTS idx_llm_memory_summary_user_id ON llm_memory_summary(user_id)",
    ]

    try:
        for index_sql in indexes:
            db.execute(index_sql)
        db.commit()
        print("✅ All indexes created successfully!")
        print(f"Created {len(indexes)} indexes for performance optimization")
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        db.rollback()


if __name__ == "__main__":
    add_optimization_indexes()
