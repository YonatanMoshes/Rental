"""API endpoint for inspecting events consumed from the message queue."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.app.db.mongodb import get_database
from backend.app.repositories.events import MongoEventRepository
from backend.app.schemas.events import FleetEventRead

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[FleetEventRead])
async def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    database: Any = Depends(get_database),
) -> list[FleetEventRead]:
    """List recently consumed queue events."""
    return await MongoEventRepository(database).list(limit=limit)
