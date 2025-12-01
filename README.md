# 💰 SmartBudget-Assistant

AI-powered Personal Finance Management System with intelligent chatbot assistant for expense tracking, budget management, and financial insights.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

- 🤖 **AI SmartBudget Assistant** - Powered by OpenAI GPT-4 & Google Gemini
- 💸 **Smart Transaction Tracking** - Natural language expense/income recording
- 📊 **Budget Management** - Track spending by category with visual insights
- 🎯 **Savings Goals** - Set and monitor financial targets
- 💳 **Multi-Account Support** - Manage multiple payment methods (Cash, BCA, OVO, Gopay, etc.)
- 🔄 **Fund Transfers** - Transfer between accounts and savings goals
- 📈 **Financial Reports** - Monthly summaries and analytics
- 🔐 **Secure Authentication** - User management with session handling
- 🧠 **Conversation Memory** - Context-aware chatbot with long-term memory

## 🚀 Tech Stack

**Backend:**
- Python 3.11+
- Flask 3.0
- SQLite Database
- OpenAI API (GPT-4o-mini)
- Google Generative AI (Gemini 2.5 Flash)

**Frontend:**
- Vanilla JavaScript
- HTML5/CSS3
- Responsive Design

## 📦 Installation

### Prerequisites
- Python 3.11 or higher
- pip
- Virtual environment (recommended)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/SmartBudget-Assistant.git
cd SmartBudget-Assistant
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

# Edit backend/.env with your API keys
FLASK_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-your-openai-api-key
GOOGLE_API_KEY=your-google-api-key
```

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
3. Login at `http://localhost:8000/login.html`

### Chat with AI Assistant

The AI assistant understands natural language commands:

**Record Expenses:**
```
"catat pengeluaran makan siang 50rb dari cash"
"beli kopi 25000 pakai gopay"
```

**Record Income:**
```
"catat pemasukan gaji 5 juta ke BCA"
"dapat bonus 1 juta masuk ke rekening"
```

**Transfer Funds:**
```
"transfer 100rb dari cash ke ovo"
"pindahkan 500000 dari BCA ke savings"
```

**Update Transactions:**
```
"ubah transaksi id 123 kategorinya jadi transport"
"edit deskripsi transaksi 456 jadi bensin motor"
```

**Create Savings Goals:**
```
"buat target tabungan dana darurat 10 juta sampai desember"
"target nabung liburan 5 juta dalam 6 bulan"
```

**Query Financial Data:**
```
"tampilkan pengeluaran bulan ini"
"berapa total pemasukan januari?"
"progress tabungan dana darurat"
```

## 🗂️ Project Structure

```
SmartBudget-Assistant/
├── backend/
│   ├── archive/          # Development & testing files
│   ├── __pycache__/      # Python cache
│   ├── auth.py           # Authentication & authorization
│   ├── config.py         # Configuration management
│   ├── database.py       # Database connection & init
│   ├── embeddings.py     # Vector embeddings for semantic search
│   ├── helpers.py        # Helper functions
│   ├── llm_executor.py   # LLM action execution
│   ├── llm_tools.py      # LLM tool definitions
│   ├── main.py           # Main Flask application
│   ├── memory.py         # Conversation memory management
│   ├── requirements.txt  # Python dependencies
│   ├── schema.sql        # Database schema
│   └── finance.db        # SQLite database (created at runtime)
├── public/
│   ├── static/           # CSS, JS files
│   ├── uploads/avatars/  # User avatars
│   ├── index.html        # Dashboard
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── profile.html      # User profile
│   ├── settings.html     # App settings
│   └── admin.html        # Admin panel
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore rules
├── render.yaml          # Render deployment config
├── startup.sh           # Startup script
└── README.md            # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_SECRET_KEY` | Flask session secret key | Yes |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes |
| `GOOGLE_API_KEY` | Google API key for Gemini | Yes |

### Supported Accounts

- Cash
- BCA
- Maybank
- Seabank
- Shopeepay
- Gopay
- Jago
- ISaku
- Ovo
- Superbank
- Blu Account (saving)

## 🚀 Deployment

### Deploy to Render

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/SmartBudget-Assistant.git
git push -u origin main
```

2. **Connect to Render**
   - Go to [render.com](https://render.com)
   - Create new Web Service
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Set environment variables** in Render dashboard:
   - `OPENAI_API_KEY`
   - `GOOGLE_API_KEY`

4. **Deploy!** Render will automatically deploy your app

## 🧪 Testing

The project includes comprehensive testing scripts in `backend/archive/`:

- `test_chat_api.py` - API endpoint testing
- `test_debug_prints.py` - Debug print validation
- `test_db_execution.py` - Database operation testing

Run tests:
```bash
cd backend/archive
python test_chat_api.py
```

## 📝 API Documentation

### Authentication Endpoints

**POST /register**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

**POST /login**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

### Chat Endpoint

**POST /chat**
```json
{
  "message": "catat pengeluaran makan 50rb",
  "provider": "openai",  // or "gemini"
  "language": "id"       // id or en
}
```

### Transaction Endpoints

- `GET /transactions` - Get all transactions
- `GET /transactions/summary` - Monthly summary
- `POST /transactions` - Create transaction
- `PUT /transactions/<id>` - Update transaction
- `DELETE /transactions/<id>` - Delete transaction

### Savings Goals Endpoints

- `GET /savings_goals` - Get all goals
- `POST /savings_goals` - Create goal
- `PUT /savings_goals/<id>` - Update goal
- `DELETE /savings_goals/<id>` - Delete goal

## 🐛 Troubleshooting

### Database Issues
```bash
cd backend
python -c "from database import init_db; init_db()"
```

### API Key Errors
- Verify `.env` file exists in `backend/` directory
- Check API keys are valid and have sufficient credits
- Ensure no quotes around API keys in `.env`

### Port Already in Use
```bash
# Change port in backend/main.py
app.run(host='0.0.0.0', port=8001)  # Use different port
```

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

Your Name - [GitHub Profile](https://github.com/yourusername)

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- Google for Gemini API
- Flask community for excellent documentation
- All contributors and testers

## 📧 Support

For support, email your-email@example.com or open an issue on GitHub.

---

⭐ **Star this repo if you find it helpful!** ⭐
