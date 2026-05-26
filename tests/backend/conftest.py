"""Shared pytest fixtures and in-memory test doubles for backend tests."""

from collections.abc import Generator
from datetime import date
from itertools import count

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_fleet_service
from backend.app.db.mongodb import get_database
from backend.app.main import create_app
from backend.app.models.documents import CarDocument, RentalDocument
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate, RentalUpdate
from backend.app.services.fleet_service import FleetService


class InMemoryCarRepository:
    """Fast fake car repository that follows the same interface as MongoCarRepository."""

    def __init__(self):
        """Prepare an empty in-memory car table and predictable ids."""
        self._ids = count(1)
        self._cars: dict[str, CarDocument] = {}

    async def create(self, data: CarCreate) -> CarDocument:
        """Store one car in memory and return the created document."""
        car_id = str(next(self._ids))
        car = CarDocument(id=car_id, **data.model_dump())
        self._cars[car_id] = car
        return car

    async def get(self, car_id: str) -> CarDocument | None:
        """Return one stored car by id."""
        return self._cars.get(car_id)

    async def list(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        """Return all cars, or only cars with the requested status."""
        cars = list(self._cars.values())
        if status is not None:
            cars = [car for car in cars if car.status == status]
        return cars

    async def update(self, car_id: str, data: CarUpdate) -> CarDocument | None:
        """Apply partial updates in the same style as the Mongo repository."""
        car = self._cars.get(car_id)
        if car is None:
            return None
        updated = car.model_copy(update=data.model_dump(exclude_none=True))
        self._cars[car_id] = updated
        return updated

    async def delete(self, car_id: str) -> bool:
        """Delete a car from memory and report whether it existed."""
        return self._cars.pop(car_id, None) is not None

    async def count_by_status(self) -> dict[str, int]:
        """Count cars by status for metrics-related tests."""
        counts = {status.value: 0 for status in VehicleStatus}
        for car in self._cars.values():
            counts[car.status.value] += 1
        return counts


class InMemoryRentalRepository:
    """Fast fake rental repository used by service and API tests."""

    def __init__(self):
        """Prepare an empty in-memory rental table and predictable ids."""
        self._ids = count(1)
        self._rentals: dict[str, RentalDocument] = {}

    async def create(self, data: RentalCreate) -> RentalDocument:
        """Store a new open rental in memory."""
        rental_id = str(next(self._ids))
        rental = RentalDocument(id=rental_id, **data.model_dump(), end_date=None)
        self._rentals[rental_id] = rental
        return rental

    async def get(self, rental_id: str) -> RentalDocument | None:
        """Return one stored rental by id."""
        return self._rentals.get(rental_id)

    async def list(self, open_only: bool | None = None) -> list[RentalDocument]:
        """Return rentals, optionally filtering to open or closed records."""
        rentals = list(self._rentals.values())
        if open_only is True:
            rentals = [rental for rental in rentals if rental.end_date is None]
        elif open_only is False:
            rentals = [rental for rental in rentals if rental.end_date is not None]
        return rentals

    async def active_for_car(self, car_id: str) -> RentalDocument | None:
        """Return the open rental that covers today for this car."""
        today = date.today()
        for rental in self._rentals.values():
            planned_end_date = rental.planned_end_date or rental.start_date
            if (
                rental.car_id == car_id
                and rental.end_date is None
                and rental.start_date <= today <= planned_end_date
            ):
                return rental
        return None

    async def open_for_car(self, car_id: str) -> RentalDocument | None:
        """Return any open rental for this car, including future reservations."""
        for rental in self._rentals.values():
            if rental.car_id == car_id and rental.end_date is None:
                return rental
        return None

    async def overlapping_for_car(
        self,
        car_id: str,
        start_date: date,
        planned_end_date: date,
        exclude_rental_id: str | None = None,
    ) -> RentalDocument | None:
        """Find an open rental whose date range conflicts with a new plan."""
        for rental in self._rentals.values():
            existing_end_date = rental.planned_end_date or rental.start_date
            if (
                rental.id != exclude_rental_id
                and rental.car_id == car_id
                and rental.end_date is None
                and rental.start_date <= planned_end_date
                and existing_end_date >= start_date
            ):
                return rental
        return None

    async def end(self, rental_id: str, end_date) -> RentalDocument | None:
        """Close an open rental by setting its actual end date."""
        rental = self._rentals.get(rental_id)
        if rental is None:
            return None
        closed = rental.model_copy(update={"end_date": end_date})
        self._rentals[rental_id] = closed
        return closed

    async def update(self, rental_id: str, data: RentalUpdate) -> RentalDocument | None:
        """Update editable rental planning fields."""
        rental = self._rentals.get(rental_id)
        if rental is None:
            return None
        updated = rental.model_copy(update=data.model_dump(exclude_unset=True))
        self._rentals[rental_id] = updated
        return updated

    async def count_open(self) -> int:
        """Count rentals that do not have an actual end date."""
        return len([rental for rental in self._rentals.values() if rental.end_date is None])


class AsyncMetricsCursor:
    """Small async cursor used by the metrics endpoint test database."""

    def __init__(self, items):
        """Wrap the given items in an async-iterator interface."""
        self._items = iter(items)

    def __aiter__(self):
        """Return this cursor as its own async iterator."""
        return self

    async def __anext__(self):
        """Return the next item or stop the async iteration."""
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class InMemoryMetricsCarsCollection:
    """Mongo-like collection that supports the car status aggregation query."""

    async def aggregate(self, pipeline):
        """Return fake status aggregation rows for Prometheus gauge refreshes."""
        return AsyncMetricsCursor([{"_id": "available", "count": 0}])


class InMemoryMetricsRentalsCollection:
    """Mongo-like collection that supports counting open rentals."""

    async def count_documents(self, query):
        """Return a fake count of open rentals for Prometheus gauge refreshes."""
        return 0


class InMemoryMetricsDatabase:
    """Minimal database object needed by /metrics in route tests."""

    def __init__(self):
        """Expose fake cars and rentals collections through Mongo-like attributes."""
        self.cars = InMemoryMetricsCarsCollection()
        self.rentals = InMemoryMetricsRentalsCollection()


@pytest.fixture()
def fleet_service() -> FleetService:
    """Provide a FleetService backed by in-memory repositories."""
    return FleetService(InMemoryCarRepository(), InMemoryRentalRepository())


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient wired to in-memory dependencies."""
    app = create_app(connect_database=False)
    service = FleetService(InMemoryCarRepository(), InMemoryRentalRepository())
    app.dependency_overrides[get_fleet_service] = lambda: service
    app.dependency_overrides[get_database] = lambda: InMemoryMetricsDatabase()

    with TestClient(app) as test_client:
        yield test_client
