"""Simple bootstrap runner using the app factory."""

import os
import sys
from pathlib import Path

# Ensure backend directory is in Python path for correct imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import create_app


def get_bind_host() -> str:
    return os.environ.get("FLASK_HOST", "0.0.0.0")


def get_bind_port() -> int:
    try:
        return int(os.environ.get("FLASK_PORT", "8000"))
    except ValueError:
        return 8000


app = create_app()

if __name__ == "__main__":
    app.run(host=get_bind_host(), port=get_bind_port())
