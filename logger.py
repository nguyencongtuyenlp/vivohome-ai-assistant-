"""
VIVOHOME AI - Logging Configuration
Centralized logging with rotating file handler.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

_LOG_FORMAT = "%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s"
_LOG_FILE = os.path.join(LOG_DIR, "vivohome.log")


def _setup_root_logger() -> None:
    """Configure root logger once at import time."""
    root = logging.getLogger()
    if root.handlers:
        return  # Already configured

    root.setLevel(logging.INFO)

    # File handler with rotation (max 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(console_handler)


_setup_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for a module."""
    return logging.getLogger(name)


# Pre-created loggers for convenience
app_logger = get_logger("app")
db_logger = get_logger("database")
rag_logger = get_logger("rag")
