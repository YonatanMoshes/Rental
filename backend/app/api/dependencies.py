"""Dependency injection providers for FastAPI routes.

Provides instances of services and repositories needed by API routes.
FastAPI automatically resolves these dependencies based on function signatures.
"""

from typing import Any

from fastapi import Depends, Request

from backend.app.db.mongodb import get_database
from backend.app.messaging.publisher import EventPublisher, NoOpEventPublisher
from backend.app.repositories.cars import MongoCarRepository
from backend.app.repositories.rentals import MongoRentalRepository
from backend.app.services.fleet_service import FleetService


def get_event_publisher(request: Request) -> EventPublisher:
    """Read the RabbitMQ publisher created during app startup."""
    return getattr(request.app.state, "event_publisher", NoOpEventPublisher())


def get_fleet_service(
    database: Any = Depends(get_database),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> FleetService:
    """Build and inject FleetService with MongoDB repositories."""
    return FleetService(
        cars=MongoCarRepository(database),
        rentals=MongoRentalRepository(database),
        event_publisher=event_publisher,
    )
