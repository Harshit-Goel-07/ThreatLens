"""
Centralised logging configuration.

Supports both human-readable logs (development) and structured JSON logs
(production) so the service plays nicely with log aggregators such as Loki,
ELK or CloudWatch.
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger

from app.config import settings


def configure_logging() -> None:
    """Configure the root logger based on application settings."""
    root = logging.getLogger()
    root.setLevel(settings.log_level)

    # Remove any pre-existing handlers (e.g. from uvicorn) to avoid duplicates.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    if settings.log_json:
        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Align uvicorn/gunicorn loggers with our configuration.
    for noisy in ("uvicorn", "uvicorn.access", "uvicorn.error", "gunicorn.error"):
        logging.getLogger(noisy).handlers = [handler]
        logging.getLogger(noisy).propagate = False
