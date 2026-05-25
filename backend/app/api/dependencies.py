from typing import Any

from fastapi import Depends

from backend.app.db.mongodb import get_database
from backend.app.repositories.cars import MongoCarRepository
from backend.app.repositories.rentals import MongoRentalRepository
from backend.app.services.fleet_service import FleetService


def get_fleet_service(database: Any = Depends(get_database)) -> FleetService:
    return FleetService(
        cars=MongoCarRepository(database),
        rentals=MongoRentalRepository(database),
    )
