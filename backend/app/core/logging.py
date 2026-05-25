"""Logging configuration.

Sets up both console and file logging with a consistent format.
Log level and file path are configurable via settings.
"""

import logging
from pathlib import Path


def configure_logging(level: str, log_file: str) -> None:
    """Configure application logging with console and file handlers."""
    log_path = Path(log_file)
    if log_path.parent:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
