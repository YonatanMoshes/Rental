"""API schemas for queued fleet events."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FleetEventRead(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: dict[str, Any]
