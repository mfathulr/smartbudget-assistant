# Financial Advisor - Project Structure

## 📁 Active Files (Production Ready)

### Backend (`/backend`)

#### Core Application
- **`main.py`** - Flask application dengan semua endpoints (chat, transactions, savings, auth)
- **`config.py`** - Configuration (database URL, API keys, paths)
- **`database.py`** - Database connection & initialization
- **`schema.sql`** - Database schema (users, transactions, savings, chat sessions, logs)

#### Business Logic
- **`llm_executor.py`** - Execute tool actions (transactions, transfers, savings)
- **`llm_tools.py`** - Tool definitions untuk LLM (OpenAI/Gemini format)
- **`helpers.py`** - Financial helpers (month summary, context building)
- **`memory.py`** - Chat memory & conversation logging
- **`embeddings.py`** - Semantic search dengan embeddings
- **`auth.py`** - Authentication decorators

#### Utilities
- **`init_admin.py`** - Script untuk create admin user
- **`reset_db.py`** - Reset database (drop & recreate tables)
- **`requirements.txt`** - Python dependencies

#### Data
- **`finance.db`** - SQLite database file
- **`.env`** - Environment variables (DATABASE_URL, API keys)
- **`server.log`** - Application logs

### Frontend (`/public`)

#### HTML Pages
- **`index.html`** - Main dashboard (chat, transactions, savings)
- **`login.html`** - Login page
- **`register.html`** - Registration page
- **`profile.html`** - User profile page
- **`settings.html`** - Settings page
- **`admin.html`** - Admin panel

#### JavaScript (`/public/static`)
- **`app.js`** - Main application logic (chat, transactions, UI)
- **`admin.js`** - Admin panel functionality
- **`profile.js`** - Profile page logic
- **`savings-helper.js`** - Savings goal helper functions
- **`styles.css`** - All application styles

#### Assets
- **`avatar-placeholder.png`** - Default user avatar

### Uploads
- **`/public/uploads/avatars/`** - User avatar uploads

---

## 🗄️ Archive Files (`/archive`)

File-file yang sudah tidak digunakan tapi disimpan untuk reference:

### Documentation
- `SESSION_SYNC_GUIDE.md` - Guide untuk session sync (dihapus)
- `DATABASE_MIGRATION.md` - Migration guide
- `MODULAR_STRUCTURE.md` - Old modular structure docs
- `README_MODULAR.md` - Old readme
- `QUICK_START_TESTING.md` - Testing guide
- `TESTING_DEBUG_GUIDE.md` - Debug guide
- `DIAGNOSIS_REPORT.md` - Old diagnosis report

### Bug Fix Reports
- `BUGFIX_ACCOUNT_NORMALIZATION_TRANSFER.md`
- `BUGFIX_DOUBLE_RECORDING.md`
- `BUGFIX_GEMINI_ACTION_MISMATCH.md`
- `ENHANCEMENT_COMPREHENSIVE_VALIDATION.md`

### Scripts (Not Used)
- `check_constraints.py` - Check FK constraints
- `check_sessions.py` - Check session status
- `cleanup_sessions.py` - Cleanup empty sessions
- `fix_cascade.py` - Fix CASCADE constraints
- `migrate_sessions.py` - Migrate orphan logs
- `test_cascade.py` - Test CASCADE delete
- `check_users.py` - Check user data
- `db_helpers.py` - Database helper functions (unused)

### Test Files
- `test_chat_api.py` - Chat API tests
- `test_db_execution.py` - Database execution tests
- `test_debug_prints.py` - Debug print tests
- `run_tests.ps1` - PowerShell test runner
- `notebook.ipynb` - Jupyter notebook experiments

### Frontend (Removed)
- `session-sync.js` - Auto-sync utility (removed for performance)
- `migrate-chat-data.js` - Migration script (not needed)

### Backup
- `main.py.backup` - Backup of main.py
- `DIAGNOSIS_REPORT.py` - Old diagnosis script

---

## 🚀 Quick Start for Testing

### 1. Start Backend
```bash
cd backend
.\.venv\Scripts\Activate.ps1
python main.py
```

### 2. Open Browser
```
http://localhost:5050
```

### 3. Test Features
- ✅ Register/Login
- ✅ Chat with AI assistant
- ✅ Add transactions (income/expense)
- ✅ Create savings goals
- ✅ View monthly summary
- ✅ Profile management

---

## 📊 Current Architecture

### Chat Storage
- **Frontend**: localStorage (`chatData`)
  - Sessions dengan messages
  - No database sync (simple & fast)

### LLM Integration
- **OpenAI**: gpt-4o-mini (primary)
- **Google Gemini**: gemini-2.0-flash-exp (fallback)

### Database
- **Type**: PostgreSQL (Neon) for production, SQLite for development
- **Tables**: users, transactions, savings_goals, chat_sessions, llm_logs, llm_log_embeddings
- **Timezone**: WIB (Asia/Jakarta, UTC+7)

### Authentication
- **Method**: Session token in localStorage
- **Decorators**: @require_login, @require_admin

---

## 🎯 Performance Optimizations

1. **No sync background** - Removed auto-sync untuk kecepatan
2. **Simple localStorage** - Tidak ada complex sync logic
3. **Direct operations** - Create/delete session langsung tanpa API call
4. **Minimal polling** - Tidak ada background polling yang memperlambat

---

## 📝 Notes

- Semua file di `/archive` aman untuk dihapus jika diperlukan
- File production hanya yang ada di `/backend` dan `/public`
- Database bisa direset dengan `python reset_db.py`
- Admin user bisa dibuat dengan `python init_admin.py`
