"""Centralized configuration, loaded from environment variables (and a local
.env file if present). Nothing else in the app should call os.getenv directly —
import values from here so there is exactly one place that defines defaults.
"""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-5").strip()

_default_origins = "http://localhost:4200,http://127.0.0.1:4200"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
