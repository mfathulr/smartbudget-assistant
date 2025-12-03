"""Initialize database and create admin user"""

import os
from flask import Flask
from database import init_db

app = Flask(__name__)

with app.app_context():
    init_db()
    print("\n✅ Database initialized successfully!")
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@smartbudget.app')
    print("👤 Admin account created/verified")
    print(f"   Email: {admin_email}")
    print("   Password: Set via ADMIN_PASSWORD environment variable")
