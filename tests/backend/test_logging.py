"""Tests for backend logging configuration."""

import logging
from datetime import datetime, timezone

from backend.app.core.logging import TimezoneFormatter


def test_timezone_formatter_uses_configured_timezone():
    """Log timestamps should render in the configured app timezone."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.created = datetime(2026, 5, 26, 14, 6, tzinfo=timezone.utc).timestamp()

    formatter = TimezoneFormatter("%(asctime)s | %(message)s", "Asia/Jerusalem")

    assert formatter.format(record).startswith("2026-05-26 17:06:00")
