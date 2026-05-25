"""Domain events sent through the message queue."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.app.models.documents import CarDocument, RentalDocument


class FleetEvent(BaseModel):
    """A business event published after an important fleet change."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]


def car_event(event_type: str, car: CarDocument) -> FleetEvent:
    """Create a queue message for a car change."""
    return FleetEvent(
        event_type=event_type,
        aggregate_type="car",
        aggregate_id=car.id,
        payload=car.model_dump(mode="json"),
    )


def rental_event(event_type: str, rental: RentalDocument) -> FleetEvent:
    """Create a queue message for a rental change."""
    return FleetEvent(
        event_type=event_type,
        aggregate_type="rental",
        aggregate_id=rental.id,
        payload=rental.model_dump(mode="json"),
    )
