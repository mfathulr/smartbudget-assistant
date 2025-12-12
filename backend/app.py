"""Flask application factory wrapper.

This factory imports the existing `main.py` application and returns the
configured Flask app. It keeps current route definitions intact while
allowing a cleaner entry point for runners and tests.
"""

from typing import Any


def create_app(*args: Any, **kwargs: Any):
    # Importing here to preserve existing side-effect route registrations.
    from main import app  # type: ignore

    return app
