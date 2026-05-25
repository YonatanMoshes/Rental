from fastapi import APIRouter, Response

from backend.app.core.metrics import metrics_response

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return metrics_response()
