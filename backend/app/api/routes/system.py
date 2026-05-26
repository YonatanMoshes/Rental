"""System health and observability endpoints.

Provides:
- /health: Basic health check
- /metrics: Prometheus-compatible metrics
- /api/operation-statistics: Friendly operation timing statistics for the UI
- /api/logs: Current application log file
"""

from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from backend.app.core.config import get_settings
from backend.app.core.metrics import metrics_response, operation_statistics_snapshot

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint. Returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics endpoint. Not included in OpenAPI schema."""
    return metrics_response()


@router.get("/api/operation-statistics")
async def operation_statistics() -> dict:
    """Return average operation times in a UI-friendly JSON shape."""
    return operation_statistics_snapshot()


@router.get("/api/logs", response_class=PlainTextResponse)
async def logs() -> PlainTextResponse:
    """Return the current application log file as plain text."""
    log_path = Path(get_settings().log_file)
    if not log_path.exists():
        return PlainTextResponse("The log file does not exist yet.")

    return PlainTextResponse(log_path.read_text(encoding="utf-8", errors="replace"))
