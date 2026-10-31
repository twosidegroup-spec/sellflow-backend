"""Vercel serverless entry point.

Exposes the existing FastAPI application unchanged (the web console at /app
and the API at /api/v1 are served by the same app). This adapter only fixes
the import path so `app.main` resolves when the function runs from its own
working directory.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401  (re-exported for the platform)
