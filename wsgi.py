"""
WSGI entry point for Gunicorn
This file makes it easier for Gunicorn to find the Flask app
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import Flask app
from main import app

if __name__ == "__main__":
    app.run()
