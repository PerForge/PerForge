"""Centralised logging configuration for the whole application.

Call setup_logging() once at startup (e.g. in app/__init__.py) before other
application modules are imported so that every logger in the project inherits
this configuration.
"""
from __future__ import annotations

import logging
import logging.config
import os
from logging.handlers import RotatingFileHandler


class IgnoreStaticRequests(logging.Filter):
    """Filter out Flask static file requests from werkzeug logger."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        return "GET /static/" not in record.getMessage()


def _build_log_config(log_directory: str) -> dict:
    """Construct dictConfig compatible logging configuration."""
    log_path = os.path.join(log_directory, "info.log")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "%(asctime)s %(levelname)s %(name)s | %(message)s",
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_path,
                "maxBytes": 50 * 1024 * 1024,  # 50 MiB
                "backupCount": 1,
                "formatter": "verbose",
                "level": "INFO",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "level": "DEBUG",
            },
        },
        "root": {
            "handlers": ["file", "console"],
            "level": "INFO",
        },
    }


def setup_logging() -> None:
    """Initialise logging across the project.

    Creates the log directory if needed, applies dictConfig, and adds the
    IgnoreStaticRequests filter to werkzeug logger.
    """
    base_dir = os.path.abspath(os.path.dirname(__file__))
    log_directory = os.path.join(base_dir, "logs")
    os.makedirs(log_directory, exist_ok=True)

    logging_config = _build_log_config(log_directory)
    logging.config.dictConfig(logging_config)

    # Suppress super-verbose access logs for static files
    logging.getLogger("werkzeug").addFilter(IgnoreStaticRequests())
