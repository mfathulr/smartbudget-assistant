-- Tabel user dengan password hashing untuk autentikasi
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    avatar_url TEXT,
    phone TEXT,
    bio TEXT,
    ocr_enabled BOOLEAN DEFAULT FALSE,
    ai_provider TEXT DEFAULT 'google',
    -- 'google' or 'openai'
    ai_model TEXT DEFAULT 'gemini-2.0-flash-lite',
    -- default model
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel sessions untuk tracking login users
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabel password reset (untuk fitur lupa password)
CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabel untuk OTP registrasi
CREATE TABLE IF NOT EXISTS registration_otps (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel transaksi harian
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    type TEXT NOT NULL,
    -- 'income' atau 'expense'
    category TEXT NOT NULL,
    description TEXT,
    amount NUMERIC NOT NULL,
    account TEXT,
    -- misal: 'cash', 'bca', 'gopay', dll
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabel savings goals untuk tracking target tabungan
CREATE TABLE IF NOT EXISTS savings_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_amount NUMERIC NOT NULL,
    current_amount NUMERIC DEFAULT 0,
    description TEXT,
    target_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabel goal keuangan (belum terlalu dipakai di logic, tapi disiapkan)
CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_amount NUMERIC NOT NULL,
    current_amount NUMERIC DEFAULT 0,
    target_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ============= LLM MEMORY TABLES =============
-- Chat sessions untuk mengelompokkan percakapan
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT DEFAULT 'New Chat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Log setiap percakapan user <-> assistant untuk long-term memory
CREATE TABLE IF NOT EXISTS llm_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    -- NULL untuk backward compatibility dengan log lama
    role TEXT NOT NULL,
    -- 'user' atau 'assistant'
    content TEXT NOT NULL,
    -- isi pesan
    meta_json TEXT,
    -- optional metadata (tool calls dsb)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- Ringkasan terkompres preferensi / pola finansial per user
CREATE TABLE IF NOT EXISTS llm_memory_summary (
    user_id INTEGER PRIMARY KEY,
    summary_text TEXT,
    -- ringkasan pola, preferensi, akun utama, kategori dominan
    interaction_count INTEGER DEFAULT 0,
    -- jumlah log yang tercakup dalam summary
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Konfigurasi per user untuk parameter memori (override default constants)
CREATE TABLE IF NOT EXISTS llm_memory_config (
    user_id INTEGER PRIMARY KEY,
    summary_threshold INTEGER DEFAULT 12,
    -- berapa banyak interaksi baru sebelum regenerasi summary
    max_log_context INTEGER DEFAULT 8,
    -- jumlah percakapan terbaru yang diinject ke prompt
    max_source INTEGER DEFAULT 200,
    -- jumlah maksimum log yang dipakai saat bikin summary
    embedding_provider TEXT DEFAULT 'openai',
    -- 'openai' atau 'local'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Embedding vektor untuk tiap log (dipakai untuk pencarian semantik)
-- Disimpan sebagai JSON array float (embedding) agar simpel
CREATE TABLE IF NOT EXISTS llm_log_embeddings (
    id SERIAL PRIMARY KEY,
    log_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    embedding TEXT NOT NULL,
    -- JSON list floats
    model TEXT NOT NULL,
    -- nama model embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (log_id) REFERENCES llm_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Conversation state untuk multi-turn flow management (per session)
CREATE TABLE IF NOT EXISTS conversation_state (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    intent TEXT NOT NULL,
    -- "add_transaction", "edit_transaction", "delete_transaction", "transfer", "create_goal"
    state TEXT NOT NULL,
    -- "AWAITING_*", "CONFIRMING", "IDLE"
    partial_data TEXT NOT NULL,
    -- JSON object dengan field yang sudah dikumpulkan
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    -- TTL: 1 jam dari last update
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- Index untuk mempercepat pencarian berdasarkan user dan session
CREATE INDEX IF NOT EXISTS idx_llm_logs_user ON llm_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_llm_logs_session ON llm_logs(session_id);

CREATE INDEX IF NOT EXISTS idx_conversation_state_session ON conversation_state(session_id);

CREATE INDEX IF NOT EXISTS idx_conversation_state_expires ON conversation_state(expires_at);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_llm_log_embeddings_user ON llm_log_embeddings(user_id);

CREATE INDEX IF NOT EXISTS idx_llm_log_embeddings_log ON llm_log_embeddings(log_id);