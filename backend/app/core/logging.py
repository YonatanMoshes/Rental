"""Logging configuration.

Sets up both console and file logging with a consistent format.
Log level and file path are configurable via settings.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _load_log_timezone(timezone_name: str):
    """Return the requested timezone, with a safe Israel-time fallback."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name == "Asia/Jerusalem":
            return timezone(timedelta(hours=3), name="Asia/Jerusalem")
        return datetime.now().astimezone().tzinfo or timezone.utc


class TimezoneFormatter(logging.Formatter):
    """Logging formatter that prints timestamps in the configured timezone."""

    def __init__(self, fmt: str, timezone_name: str):
        """Create a formatter that renders asctime in timezone_name."""
        super().__init__(fmt)
        self.timezone = _load_log_timezone(timezone_name)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Format the log record timestamp using the configured timezone."""
        logged_at = datetime.fromtimestamp(record.created, tz=self.timezone)
        if datefmt is not None:
            return logged_at.strftime(datefmt)
        return logged_at.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


def configure_logging(level: str, log_file: str, timezone_name: str = "Asia/Jerusalem") -> None:
    """Configure application logging with console and file handlers."""
    log_path = Path(log_file)
    if log_path.parent:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = TimezoneFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        timezone_name,
    )
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True,
    )
