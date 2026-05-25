from datetime import date
import asyncio

import pytest

from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate
from backend.app.services.fleet_service import FleetService


class CapturingEventPublisher:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


def test_add_and_list_cars(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Hyundai i20", year=2022))
        cars = await fleet_service.list_cars()

        assert car.id == "1"
        assert cars == [car]

    asyncio.run(scenario())


def test_add_car_publishes_queue_event(fleet_service):
    async def scenario():
        publisher = CapturingEventPublisher()
        service = FleetService(fleet_service.cars, fleet_service.rentals, publisher)

        car = await service.add_car(CarCreate(model="Hyundai i20", year=2022))

        assert publisher.events[0].event_type == "car.created"
        assert publisher.events[0].aggregate_type == "car"
        assert publisher.events[0].aggregate_id == car.id

    asyncio.run(scenario())


def test_update_car_status_to_maintenance(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Kia Niro", year=2024))
        updated = await fleet_service.update_car(
            car.id,
            CarUpdate(status=VehicleStatus.MAINTENANCE),
        )

        assert updated.status == VehicleStatus.MAINTENANCE

    asyncio.run(scenario())


def test_start_rental_marks_car_as_rented(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Toyota Corolla", year=2024))
        rental = await fleet_service.start_rental(
            RentalCreate(car_id=car.id, customer_name="Dana Levi", start_date=date(2026, 5, 25))
        )

        cars = await fleet_service.list_cars()
        assert rental.end_date is None
        assert cars[0].status == VehicleStatus.RENTED

    asyncio.run(scenario())


def test_end_rental_marks_car_available(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Mazda 3", year=2023))
        rental = await fleet_service.start_rental(
            RentalCreate(car_id=car.id, customer_name="Avi Cohen", start_date=date(2026, 5, 25))
        )
        closed = await fleet_service.end_rental(rental.id, end_date=date(2026, 5, 26))

        cars = await fleet_service.list_cars()
        assert closed.end_date == date(2026, 5, 26)
        assert cars[0].status == VehicleStatus.AVAILABLE

    asyncio.run(scenario())


def test_cannot_rent_car_in_maintenance(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(
            CarCreate(model="Tesla Model 3", year=2025, status=VehicleStatus.MAINTENANCE)
        )

        with pytest.raises(BusinessRuleError):
            await fleet_service.start_rental(RentalCreate(car_id=car.id, customer_name="Noa Amir"))

    asyncio.run(scenario())


def test_missing_car_raises_not_found(fleet_service):
    async def scenario():
        with pytest.raises(NotFoundError):
            await fleet_service.update_car("missing", CarUpdate(status=VehicleStatus.AVAILABLE))

    asyncio.run(scenario())
