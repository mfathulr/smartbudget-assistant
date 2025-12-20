# 💰 SmartBudget-Assistant

**AI-powered Personal Finance Management System** with intelligent chatbot assistant for expense tracking, budget management, and financial insights.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Flask 3.0.0](https://img.shields.io/badge/flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL 15+](https://img.shields.io/badge/postgresql-15+-blue.svg)](https://www.postgresql.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status: Active](https://img.shields.io/badge/status-active-success.svg)](https://github.com/mfathulr/smartbudget-assistant)
[![Tests: 127/132](https://img.shields.io/badge/tests-127%2F132%20passing-brightgreen.svg)](backend/tests/)

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Live Demo](#-live-demo)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

---

## 🚀 Live Demo

**[https://smartbudget-assistant.onrender.com](https://smartbudget-assistant.onrender.com)**

> 💡 **Tip:** Use demo credentials or create a new account to test all features. First-time setup takes ~2 minutes.

---

## ✨ Features

### 🎨 Authentication & Security
- 🔐 **Secure User Registration** - Email verification with OTP (One-Time Password)
- 🔑 **Password Recovery** - Forgot password with email reset link
- 🌐 **Bilingual Support** - Indonesian & English interface
- 🎯 **Strong Password Generator** - Built-in password suggestion tool
- ✅ **Modern UI/UX** - Professional glassmorphism design with smooth animations
- 📱 **Fully Responsive** - Optimized for desktop, tablet, and mobile devices

### 🤖 AI Financial Assistant
- 💬 **Intelligent AI Chatbot** - Powered by OpenAI GPT-4o-mini & Google Gemini 2.5 Flash
- 🗣️ **Natural Language Processing** - Understands Indonesian & English commands
- 💸 **Smart Transaction Tracking** - Automatic expense/income recording via conversation
- 📊 **Budget Analytics** - Track spending by category with visual charts
- 🎯 **Savings Goal Management** - Set targets and monitor progress with AI insights
- 💳 **Multi-Account Support** - Manage 10+ payment methods simultaneously
- 🔄 **Intelligent Fund Transfers** - Transfer between accounts and savings with AI validation
- 📈 **Financial Reports** - Monthly summaries, trends, and spending patterns
- 🧠 **Conversation Memory** - Context-aware assistant with persistent chat history
- ⚡ **Real-time Responses** - Instant feedback and transaction confirmation

## 🚀 Tech Stack

### Backend Architecture
- **Language:** Python 3.11+
- **Framework:** Flask 3.0.0 with RESTful API design
- **Database:** PostgreSQL 15+ (Production - Neon), SQLite (Development)
- **AI/ML:** 
  - OpenAI API (GPT-4o-mini for intelligent processing)
  - Google Generative AI (Gemini 2.5 Flash for fast responses)
- **Email Service:** Gmail SMTP for OTP and password reset
- **Server:** Gunicorn 21.2.0 WSGI server
- **Authentication:** Session-based with secure password hashing

### Frontend Technologies
- **Markup:** HTML5 with semantic structure
- **Styling:** CSS3 with responsive design, glassmorphism effects
- **Scripting:** Vanilla JavaScript (no frameworks) for lightweight performance
- **Icons:** FontAwesome 6.4.0
- **Design:** Mobile-first, fully responsive (320px to 4K)
- **Animations:** Pure CSS with smooth transitions

### DevOps & Deployment
- **Hosting:** Render.com Web Service
- **Container Ready:** Gunicorn + render.yaml configuration
- **Version Control:** Git with GitHub
- **Environment Management:** Python-dotenv for secure configuration

## 📦 Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 15+ (production) or SQLite (development)
- OpenAI API key
- Google Gemini API key
- Gmail account for SMTP email service

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/mfathulr/smartbudget-assistant.git
cd smartbudget-assistant
```

2. **Create virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
# Copy example env file
cp .env.example backend/.env

# Edit backend/.env with your credentials
FLASK_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-your-openai-api-key
GOOGLE_API_KEY=your-google-gemini-api-key
DATABASE_URL=sqlite:///smartbudget.db  # For local development

# Email Configuration (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM=your-email@gmail.com
```

> **Note:** For Gmail, you need to create an App Password. See [EMAIL_SETUP.md](EMAIL_SETUP.md) for detailed instructions.

5. **Initialize database**
```bash
cd backend
python -c "from database import init_db; init_db()"
```

6. **Run the application**
```bash
python main.py
```

The application will be available at `http://localhost:8000`

## 🎯 Usage

### Register & Login
1. Navigate to `http://localhost:8000/register.html`
2. Create an account with email and password
3. Verify your email with the OTP code sent to your inbox
4. Login at `http://localhost:8000/login.html`
5. Use "Forgot Password" if you need to reset your password

### Chat with AI Assistant

The AI assistant understands natural language commands in **Indonesian** and **English**:

#### 💰 Record Expenses
```
"catat pengeluaran makan siang 50rb dari cash"
"beli kopi 25000 pakai gopay"
"spent $15 on gas from credit card"
```

#### 💸 Record Income
```
"catat pemasukan gaji 5 juta ke BCA"
"dapat bonus 1 juta masuk ke rekening"
"received payment 2 million from freelance work"
```

#### 🔄 Transfer Funds
```
"transfer 100rb dari cash ke ovo"
"pindahkan 500000 dari BCA ke savings"
"move $100 from checking to emergency fund"
```

#### ✏️ Update Transactions
```
"ubah transaksi id 123 kategorinya jadi transport"
"edit deskripsi transaksi 456 jadi bensin motor"
"change transaction 789 amount to 50000"
```

#### 🎯 Create Savings Goals
```
"buat target tabungan dana darurat 10 juta sampai desember"
"target nabung liburan 5 juta dalam 6 bulan"
"set savings goal for house down payment 500 million by 2027"
```

#### 📊 Query Financial Data
```
"tampilkan pengeluaran bulan ini"
"berapa total pemasukan januari?"
"progress tabungan dana darurat"
"show my spending by category"
"which month did I spend the most?"
```

## 🗂️ Project Structure

```
SmartBudget-Assistant/
├── backend/
│   ├── archive/              # Development & testing files
│   ├── __pycache__/          # Python cache
│   ├── auth.py               # Authentication, OTP, password reset
│   ├── config.py             # Configuration management
│   ├── database.py           # Database connection & initialization
│   ├── embeddings.py         # Vector embeddings for semantic search
│   ├── helpers.py            # Email utilities & helper functions
│   ├── llm_executor.py       # AI model interaction & execution
│   ├── llm_tools.py          # AI function definitions
│   ├── main.py               # Main Flask application & API endpoints
│   ├── memory.py             # Conversation memory management
│   ├── requirements.txt      # Python dependencies
│   ├── schema.sql            # PostgreSQL/SQLite database schema
│   ├── init_admin.py         # Admin user initialization script
│   └── reset_db.py           # Database reset utility
├── public/                           # Frontend Web Application
│   ├── static/
│   │   ├── app.js                   # Core application logic (2800+ lines)
│   │   ├── admin.js                 # Admin dashboard functionality
│   │   ├── modals.js                # Modal content (Terms, Privacy)
│   │   ├── profile.js               # Profile management
│   │   ├── savings-helper.js        # Savings goal utilities
│   │   └── styles.css               # Global styles (responsive design)
│   ├── uploads/
│   │   └── avatars/                 # User profile pictures
│   ├── index.html                   # Main chat interface
│   ├── login.html                   # Login page
│   ├── register.html                # Registration form
│   ├── forgot.html                  # Password recovery
│   ├── reset-password.html          # Password reset
│   ├── profile.html                 # User profile
│   ├── settings.html                # User settings
│   └── admin.html                   # Admin dashboard
├── assets/                           # Images and static resources
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
├── check_encoding.py                 # UTF-8 validation utility
├── render.yaml                       # Render.com deployment config
├── startup.sh                        # Production startup script
├── wsgi.py                           # WSGI entry point (Gunicorn)
├── requirements.txt                  # Root dependencies
├── LICENSE                           # MIT License
├── README.md                         # This file
└── EMAIL_SETUP.md                    # Email configuration guide
```

## 🔧 Configuration

### Environment Variables Setup

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Flask session secret (min 32 chars) | `abcd1234xyz...` | ✅ Yes |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini) | `sk-proj-abc123...` | ✅ Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIzaSyD...` | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` | ✅ Yes (Prod) |
| `SMTP_HOST` | Email server hostname | `smtp.gmail.com` | ✅ Yes |
| `SMTP_PORT` | Email server port | `587` | ✅ Yes |
| `SMTP_USER` | Gmail/SMTP username | `your-email@gmail.com` | ✅ Yes |
| `SMTP_PASSWORD` | Gmail App Password (not regular password) | `xxxx xxxx xxxx xxxx` | ✅ Yes |
| `SMTP_FROM` | Sender email address | `noreply@smartbudget.com` | ✅ Yes |
| `APP_URL` | Application base URL | `https://smartbudget-assistant.onrender.com` | ✅ Yes (Prod) |
| `RECAPTCHA_SITE_KEY` | reCAPTCHA v3 site key | `6Lc...` | ⭕ Optional |
| `RECAPTCHA_SECRET_KEY` | reCAPTCHA v3 secret key | `6Lc...` | ⭕ Optional |
| `SMTP_USER` | Gmail address | Yes |
| `SMTP_PASSWORD` | Gmail App Password | Yes |
| `SMTP_FROM` | From email address | Yes |
| `APP_URL` | Application URL | Yes (Production) |
| `RECAPTCHA_SITE_KEY` | reCAPTCHA v3 site key | Optional |
| `RECAPTCHA_SECRET_KEY` | reCAPTCHA v3 secret key | Optional |

### Supported Payment Accounts

- 💵 **Cash** - Physical currency
- 🏦 **Bank Accounts** - BCA, Maybank, Seabank
- 💳 **Digital Wallets** - GoPay, OVO, ShopeePay
- 🏪 **Fintech** - Jago Bank, ISaku, Superbank, Blu Account
- 🎯 **Savings Goals** - Track progress towards financial targets

## 🚀 Deployment

### Deploy to Render

**Step 1: Prepare Repository**
```bash
git add .
git commit -m "chore: prepare for production deployment"
git push origin main
```

**Step 2: Create Render Web Service**
1. Go to [render.com](https://render.com) and sign up
2. Create new **Web Service**
3. Connect your GitHub account
4. Select `mfathulr/smartbudget-assistant` repository
5. Render will auto-detect `render.yaml` configuration

**Step 3: Configure Environment Variables**

In Render dashboard, set these environment variables:

```env
FLASK_SECRET_KEY=your-random-32-char-secret-key
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_API_KEY=your-google-gemini-key
DATABASE_URL=postgresql://user:password@host/database
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=your-email@gmail.com
APP_URL=https://smartbudget-assistant.onrender.com
```

**Step 4: Deploy**
- Click **Create Web Service**
- Render will automatically build and deploy your app
- Your app will be live at `https://smartbudget-assistant.onrender.com`

> 📋 **Important:** Review [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) for security best practices before deploying to production.

### Environment-Specific Configuration

**Development** (SQLite):
```env
DATABASE_URL=sqlite:///smartbudget.db
```

**Production** (PostgreSQL):
```env
DATABASE_URL=postgresql://user:password@neon.tech/database
```

## 🧪 Testing

The project includes **comprehensive test suite** with **127+ passing tests** covering:

### Test Coverage

- ✅ **Authentication Tests** - Registration, login, OTP verification, password reset
- ✅ **API Endpoint Tests** - All REST endpoints validated
- ✅ **Chat Functionality** - AI response generation and tool execution
- ✅ **Transaction Management** - CRUD operations and validation
- ✅ **Database Schema** - Schema integrity and migrations
- ✅ **Email Services** - SendGrid and SMTP email delivery
- ✅ **Security** - Password hashing, input validation, authorization
- ✅ **Financial Logic** - Budget calculations, savings goals, transfers

### Run Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/test_chat_endpoint.py -v

# Run tests with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run tests in watch mode
pytest-watch backend/tests/
```

### Test Structure

```
backend/tests/
├── conftest.py                    # Pytest fixtures and configuration
├── test_chat_endpoint.py          # Chat API and AI responses
├── test_transactions.py           # Transaction CRUD operations
├── test_auth_profile.py           # User authentication and profile
├── test_authorization.py          # Permission and role-based access
├── test_password_reset.py         # Password recovery flow
├── test_email_sending.py          # Email service delivery
├── test_llm_executor_models.py    # AI model integration
├── test_llm_tools.py              # LLM tool function execution
├── test_savings.py                # Savings goal management
├── test_financial_endpoints.py    # Financial data endpoints
└── ... (11 more test files)
```

## 📝 API Documentation

### Authentication Endpoints

**POST** `/register`
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**POST** `/verify-otp`
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**POST** `/login`
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**POST** `/forgot-password`
```json
{
  "email": "user@example.com"
}
```

**POST** `/reset-password`
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass123!"
}
```

### Chat Endpoint

**POST** `/api/chat` (Requires authentication)
```json
{
  "message": "catat pengeluaran makan 50rb dari cash",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "lang": "id",
  "image": null
}
```

**Response:**
```json
{
  "answer": "✅ Pengeluaran Rp 50.000 untuk makan dari cash telah dicatat.",
  "session_id": "uuid-here"
}
```

### Transaction Endpoints

- **GET** `/api/transactions` - Get all user transactions
- **GET** `/api/transactions/summary` - Monthly spending summary
- **GET** `/api/transactions/{id}` - Get transaction details
- **POST** `/api/transactions` - Create new transaction
- **PUT** `/api/transactions/{id}` - Update transaction
- **DELETE** `/api/transactions/{id}` - Delete transaction

### Account Endpoints

- **GET** `/api/accounts` - List all user accounts
- **POST** `/api/accounts` - Create new account
- **PUT** `/api/accounts/{id}` - Update account
- **DELETE** `/api/accounts/{id}` - Delete account

### Savings Goals Endpoints

- **GET** `/api/savings_goals` - Get all goals
- **POST** `/api/savings_goals` - Create savings goal
- **PUT** `/api/savings_goals/{id}` - Update goal
- **DELETE** `/api/savings_goals/{id}` - Delete goal

### User Profile Endpoints

- **GET** `/api/profile` - Get user profile
- **PUT** `/api/profile` - Update profile
- **POST** `/api/profile/avatar` - Upload profile picture

> 📚 Full API documentation available in [API_DOCS.md](API_DOCS.md) (if provided)

## 🐛 Troubleshooting

### Database Issues

**Error: Database connection failed**
```bash
# Re-initialize database
cd backend
python -c "from database import init_db; init_db()"
```

**Error: Migration failed**
```bash
# Check PostgreSQL connection string
python -c "import psycopg2; psycopg2.connect('postgresql://user:pass@host/db')"
```

### API Key Issues

**Error: OpenAI API key invalid**
- Verify API key in `.env` file (no quotes)
- Check API key has sufficient credits: https://platform.openai.com/account/usage/overview
- Ensure API key is for correct organization

**Error: Google Gemini API key invalid**
- Generate new key: https://makersuite.google.com/app/apikey
- Verify billing is enabled in Google Cloud Console
- Check API key doesn't have IP restrictions

### Email Configuration Issues

**Error: SMTP authentication failed**
```bash
# For Gmail, use App Password (not regular password)
# https://myaccount.google.com/apppasswords
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-character app password
```

**Error: Email not sending**
- Check `SMTP_USER` matches email with app password
- Verify firewall allows SMTP port 587
- Check SendGrid API key in `.env`
- Review logs: `tail -f logs/app.log`

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Use different port
python main.py --port=8001

# Or modify in main.py:
# app.run(host='0.0.0.0', port=8001)
```

### UTF-8 Encoding Issues

```bash
# Validate file encoding
python check_encoding.py

# Fix encoding if needed
iconv -f ISO-8859-1 -t UTF-8 file.py -o file_fixed.py
```

### Performance Issues

**Slow chat responses:**
- Check API rate limits
- Review database query performance
- Monitor token usage in OpenAI/Google dashboard
- Consider upgrading to faster model

**High memory usage:**
- Reduce conversation memory size
- Implement conversation archiving
- Monitor with: `ps aux | grep python`

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

**Muhammad Fathul Radhiansyah**

- 🐙 GitHub: [@mfathulr](https://github.com/mfathulr)
- 🌐 Live Demo: [smartbudget-assistant.onrender.com](https://smartbudget-assistant.onrender.com)
- 📧 Contact: [Email me](mailto:fathul.hakim@example.com)

---

## 🙏 Acknowledgments

- **OpenAI** - GPT-4o-mini API for intelligent processing
- **Google** - Gemini 2.5 Flash API for fast responses
- **Render** - Reliable cloud hosting platform
- **Flask Community** - Excellent documentation and ecosystem
- **PostgreSQL** - Robust database technology
- **FontAwesome** - Beautiful icon library
- All contributors and early testers

---

## 📧 Support & Feedback

Have questions or found a bug? 

- 📝 **Open an Issue**: [GitHub Issues](https://github.com/mfathulr/smartbudget-assistant/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/mfathulr/smartbudget-assistant/discussions)
- 📧 **Email**: Contact through GitHub profile

---

## 📚 Additional Resources

- [EMAIL_SETUP.md](EMAIL_SETUP.md) - Detailed Gmail SMTP configuration guide
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - Security and deployment checklist
- [LICENSE](LICENSE) - MIT License

---

## 🎯 Roadmap

Planned features for future releases:

- [ ] Mobile app (React Native)
- [ ] Real-time expense notifications
- [ ] Advanced analytics and forecasting
- [ ] Multi-user household budgeting
- [ ] Investment portfolio tracking
- [ ] Tax report generation
- [ ] API rate limiting and quotas
- [ ] Advanced security features (2FA, biometrics)

---

<div align="center">

### ⭐ Found this helpful? Please consider starring the repository! ⭐

[![GitHub Stars](https://img.shields.io/github/stars/mfathulr/smartbudget-assistant?style=social)](https://github.com/mfathulr/smartbudget-assistant)
[![GitHub Forks](https://img.shields.io/github/forks/mfathulr/smartbudget-assistant?style=social)](https://github.com/mfathulr/smartbudget-assistant)

**Made with ❤️ by [Muhammad Fathul Radhiansyah](https://github.com/mfathulr)**

</div>
