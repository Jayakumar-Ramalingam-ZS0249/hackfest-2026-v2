"""
Structured logging setup.

Deliberately logs processing metadata (claim id, stage, duration,
match score) and never raw document text or extracted patient/claim
field values, per the "no sensitive data in logs" requirement.
"""

import logging
import sys


def configure_logging(app_env: str) -> None:
    level = logging.DEBUG if app_env == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root = logging.getLogger("app")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False
