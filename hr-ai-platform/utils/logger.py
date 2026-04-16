"""Centralized logging configuration for the HR AI Platform."""

import logging
import sys

from app.config import settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    return logger
