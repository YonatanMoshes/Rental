"""System health and observability endpoints.

Provides:
- /health: Basic health check
- /metrics: Prometheus-compatible metrics
"""

from fastapi import APIRouter, Response

from backend.app.core.metrics import metrics_response

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint. Returns 200 OK if service is running."""
    return {"status": "ok"}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics endpoint. Not included in OpenAPI schema."""
    return metrics_response()
