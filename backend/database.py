"""Database utilities and connection management"""

import os
from flask import g
from config import DB_TYPE, SCHEMA_PATH, DB_PATH

# Import appropriate database driver based on DB_TYPE
if DB_TYPE == "postgresql":
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3


class _PgAdapter:
    """
    Thin adapter to provide a SQLite-like API for psycopg2 connections
    so existing code using db.execute(...).fetchone()/fetchall() keeps working.
    """

    def __init__(self, conn):
        self._conn = conn

    def _convert_placeholders(self, query: str):
        # Convert SQLite-style placeholders (?) to psycopg2 (%s)
        return query.replace("?", "%s")

    def execute(self, query: str, params=()):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(self._convert_placeholders(query), params or ())
        return cur

    def cursor(self):
        return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db():
    """Get database connection from Flask g object"""
    if "db" not in g:
        if DB_TYPE == "postgresql":
            conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
            # Ensure session timezone is Asia/Jakarta (WIB) so CURRENT_TIMESTAMP is in WIB
            try:
                cur = conn.cursor()
                cur.execute("SET TIME ZONE 'Asia/Jakarta'")
                conn.commit()
                cur.close()
            except Exception as tz_err:
                print(f"[DB WARN] Failed to set session timezone: {tz_err}")
            # Wrap with adapter that exposes .execute/.commit like sqlite3
            g.db = _PgAdapter(conn)
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            g.db = conn
    return g.db


def close_db(exc=None):
    """Close database connection"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(standalone=False):
    """Initialize database from schema.sql

    Args:
        standalone: If True, creates connection directly without Flask's g object
    """
    from werkzeug.security import generate_password_hash

    if standalone:
        # Direct connection without Flask's g
        if DB_TYPE == "postgresql":
            conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
            try:
                cur = conn.cursor()
                cur.execute("SET TIME ZONE 'Asia/Jakarta'")
                conn.commit()
                cur.close()
            except Exception as tz_err:
                print(f"[DB WARN] Failed to set session timezone: {tz_err}")
            db = _PgAdapter(conn)
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            db = conn
    else:
        db = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

        if DB_TYPE == "postgresql":
            # Execute PostgreSQL schema line by line
            cur = db.cursor()
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement:
                    cur.execute(statement)
            db.commit()
            cur.close()
        else:
            # SQLite can use executescript
            db.executescript(schema_sql)
            db.commit()

    print(f"Database schema initialized from schema.sql (DB Type: {DB_TYPE})")

    # Ensure additional columns exist on users table (PostgreSQL-compatible)
    try:
        if DB_TYPE == "postgresql":
            cur = db.cursor()
            # Check if columns exist in PostgreSQL
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            cols = {row["column_name"] for row in cur.fetchall()}

            altered = False
            if "phone" not in cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
                altered = True
            if "bio" not in cols:
                cur.execute("ALTER TABLE users ADD COLUMN bio TEXT")
                altered = True
            if "avatar_url" not in cols:
                cur.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
                altered = True

            if altered:
                db.commit()
                print("Users table altered to add missing columns")
            cur.close()
        else:
            # SQLite PRAGMA check
            cur = db.execute("PRAGMA table_info(users)")
            cols = {row[1] for row in cur.fetchall()}
            altered = False

            if "phone" not in cols:
                db.execute("ALTER TABLE users ADD COLUMN phone TEXT")
                altered = True
            if "bio" not in cols:
                db.execute("ALTER TABLE users ADD COLUMN bio TEXT")
                altered = True
            if "avatar_url" not in cols:
                db.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
                altered = True

            if altered:
                db.commit()
                print("Users table altered to add missing columns")
    except Exception as e:
        print(f"[WARN] Could not ensure extra user columns: {e}")

    # Ensure chat_sessions table exists and session_id column in llm_logs (backward compatibility)
    try:
        if DB_TYPE == "postgresql":
            cur = db.cursor()

            # Check if chat_sessions table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'chat_sessions'
                )
            """)
            result = cur.fetchone()
            table_exists = result["exists"] if result else False

            if not table_exists:
                # Create chat_sessions table
                cur.execute("""
                    CREATE TABLE chat_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title TEXT DEFAULT 'New Chat',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                cur.execute(
                    "CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id)"
                )
                db.commit()
                print("✅ chat_sessions table created")

            # Check if session_id column exists in llm_logs
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'llm_logs' AND column_name = 'session_id'
            """)
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE llm_logs ADD COLUMN session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE"
                )
                cur.execute("CREATE INDEX idx_llm_logs_session ON llm_logs(session_id)")
                db.commit()
                print("✅ llm_logs table updated: added session_id column")

            cur.close()
        else:
            # SQLite - check chat_sessions table
            cur = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_sessions'"
            )
            if not cur.fetchone():
                db.execute("""
                    CREATE TABLE chat_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT DEFAULT 'New Chat',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                db.execute(
                    "CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id)"
                )
                db.commit()
                print("✅ chat_sessions table created")

            # Check session_id column in llm_logs
            cur = db.execute("PRAGMA table_info(llm_logs)")
            cols = {row[1] for row in cur.fetchall()}
            if "session_id" not in cols:
                db.execute(
                    "ALTER TABLE llm_logs ADD COLUMN session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE"
                )
                db.execute("CREATE INDEX idx_llm_logs_session ON llm_logs(session_id)")
                db.commit()
                print("✅ llm_logs table updated: added session_id column")
    except Exception as e:
        print(f"[WARN] Could not ensure chat session tables: {e}")
        import traceback

        traceback.print_exc()

    # Create default admin user if not exists
    try:
        if DB_TYPE == "postgresql":
            cur = db.cursor()
            cur.execute(
                "SELECT id FROM users WHERE email = %s",
                ("muhammadfathul386@gmail.com",),
            )
            if not cur.fetchone():
                password_hash = generate_password_hash("cuwiklucu08")
                cur.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                    (
                        "Admin Fathul",
                        "muhammadfathul386@gmail.com",
                        password_hash,
                        "admin",
                    ),
                )
                db.commit()
                print("✅ Default admin user created: muhammadfathul386@gmail.com")
            else:
                print("ℹ️  Admin user already exists")
            cur.close()
        else:
            cur = db.execute(
                "SELECT id FROM users WHERE email = ?",
                ("muhammadfathul386@gmail.com",),
            )
            if not cur.fetchone():
                password_hash = generate_password_hash("cuwiklucu08")
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (
                        "Admin Fathul",
                        "muhammadfathul386@gmail.com",
                        password_hash,
                        "admin",
                    ),
                )
                db.commit()
                print("✅ Default admin user created: muhammadfathul386@gmail.com")
            else:
                print("ℹ️  Admin user already exists")
    except Exception as e:
        print(f"[WARN] Could not create default admin user: {e}")

    # Close connection if standalone mode
    if standalone:
        db.close()
