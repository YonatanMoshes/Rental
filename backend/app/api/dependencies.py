"""Dependency injection providers for FastAPI routes.

Provides instances of services and repositories needed by API routes.
FastAPI automatically resolves these dependencies based on function signatures.
"""

from typing import Any

from fastapi import Depends

from backend.app.db.mongodb import get_database
from backend.app.repositories.cars import MongoCarRepository
from backend.app.repositories.rentals import MongoRentalRepository
from backend.app.services.fleet_service import FleetService


def get_fleet_service(database: Any = Depends(get_database)) -> FleetService:
    """Build and inject FleetService with MongoDB repositories."""
    return FleetService(
        cars=MongoCarRepository(database),
        rentals=MongoRentalRepository(database),
    )
