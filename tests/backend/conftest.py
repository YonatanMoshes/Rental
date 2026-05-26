from collections.abc import Generator
from itertools import count

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_fleet_service
from backend.app.main import create_app
from backend.app.models.documents import CarDocument, RentalDocument
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate, RentalUpdate
from backend.app.services.fleet_service import FleetService


class InMemoryCarRepository:
    def __init__(self):
        self._ids = count(1)
        self._cars: dict[str, CarDocument] = {}

    async def create(self, data: CarCreate) -> CarDocument:
        car_id = str(next(self._ids))
        car = CarDocument(id=car_id, **data.model_dump())
        self._cars[car_id] = car
        return car

    async def get(self, car_id: str) -> CarDocument | None:
        return self._cars.get(car_id)

    async def list(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        cars = list(self._cars.values())
        if status is not None:
            cars = [car for car in cars if car.status == status]
        return cars

    async def update(self, car_id: str, data: CarUpdate) -> CarDocument | None:
        car = self._cars.get(car_id)
        if car is None:
            return None
        updated = car.model_copy(update=data.model_dump(exclude_none=True))
        self._cars[car_id] = updated
        return updated

    async def delete(self, car_id: str) -> bool:
        return self._cars.pop(car_id, None) is not None

    async def count_by_status(self) -> dict[str, int]:
        counts = {status.value: 0 for status in VehicleStatus}
        for car in self._cars.values():
            counts[car.status.value] += 1
        return counts


class InMemoryRentalRepository:
    def __init__(self):
        self._ids = count(1)
        self._rentals: dict[str, RentalDocument] = {}

    async def create(self, data: RentalCreate) -> RentalDocument:
        rental_id = str(next(self._ids))
        rental = RentalDocument(id=rental_id, **data.model_dump(), end_date=None)
        self._rentals[rental_id] = rental
        return rental

    async def get(self, rental_id: str) -> RentalDocument | None:
        return self._rentals.get(rental_id)

    async def list(self, open_only: bool | None = None) -> list[RentalDocument]:
        rentals = list(self._rentals.values())
        if open_only is True:
            rentals = [rental for rental in rentals if rental.end_date is None]
        elif open_only is False:
            rentals = [rental for rental in rentals if rental.end_date is not None]
        return rentals

    async def active_for_car(self, car_id: str) -> RentalDocument | None:
        for rental in self._rentals.values():
            if rental.car_id == car_id and rental.end_date is None:
                return rental
        return None

    async def end(self, rental_id: str, end_date) -> RentalDocument | None:
        rental = self._rentals.get(rental_id)
        if rental is None:
            return None
        closed = rental.model_copy(update={"end_date": end_date})
        self._rentals[rental_id] = closed
        return closed

    async def update(self, rental_id: str, data: RentalUpdate) -> RentalDocument | None:
        rental = self._rentals.get(rental_id)
        if rental is None:
            return None
        updated = rental.model_copy(update=data.model_dump(exclude_unset=True))
        self._rentals[rental_id] = updated
        return updated

    async def count_open(self) -> int:
        return len([rental for rental in self._rentals.values() if rental.end_date is None])


@pytest.fixture()
def fleet_service() -> FleetService:
    return FleetService(InMemoryCarRepository(), InMemoryRentalRepository())


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = create_app(connect_database=False)
    service = FleetService(InMemoryCarRepository(), InMemoryRentalRepository())
    app.dependency_overrides[get_fleet_service] = lambda: service

    with TestClient(app) as test_client:
        yield test_client
