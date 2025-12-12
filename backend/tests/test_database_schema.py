"""Tests for database operations and schema."""

from database import get_db


def test_database_connection(app_ctx):
    """Test database connection works."""
    db = get_db()
    assert db is not None


def test_users_table_has_required_columns(app_ctx, db_conn):
    """Test users table has all required columns."""
    cur = db_conn.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users'
        """
    )
    columns = {row["column_name"] for row in cur.fetchall()}

    required_columns = {
        "id",
        "name",
        "email",
        "password_hash",
        "role",
        "created_at",
        "ocr_enabled",
        "ai_provider",
        "ai_model",
        "phone",
        "bio",
        "avatar_url",
    }

    assert required_columns.issubset(columns), (
        f"Missing columns: {required_columns - columns}"
    )


def test_transactions_table_exists(app_ctx, db_conn):
    """Test transactions table exists with required columns."""
    cur = db_conn.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'transactions'
        """
    )
    columns = {row["column_name"] for row in cur.fetchall()}

    required_columns = {"id", "user_id", "date", "type", "category", "amount"}

    assert required_columns.issubset(columns), (
        f"Missing columns: {required_columns - columns}"
    )


def test_sessions_table_exists(app_ctx, db_conn):
    """Test sessions table exists for authentication."""
    cur = db_conn.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'sessions'
        )
        """
    )
    result = cur.fetchone()
    assert result["exists"], "sessions table should exist"


def test_savings_goals_table_exists(app_ctx, db_conn):
    """Test savings_goals table exists."""
    cur = db_conn.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'savings_goals'
        )
        """
    )
    result = cur.fetchone()
    assert result["exists"], "savings_goals table should exist"


def test_chat_sessions_table_exists(app_ctx, db_conn):
    """Test chat_sessions table exists for chat history."""
    cur = db_conn.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'chat_sessions'
        )
        """
    )
    result = cur.fetchone()
    assert result["exists"], "chat_sessions table should exist"
