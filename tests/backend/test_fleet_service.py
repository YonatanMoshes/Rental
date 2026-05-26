from datetime import date, timedelta
import asyncio

import pytest

from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate, RentalUpdate
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
        today = date.today()
        car = await fleet_service.add_car(CarCreate(model="Toyota Corolla", year=2024))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Dana Levi",
                start_date=today,
                planned_end_date=today + timedelta(days=2),
            )
        )

        cars = await fleet_service.list_cars()
        assert rental.end_date is None
        assert cars[0].status == VehicleStatus.RENTED

    asyncio.run(scenario())


def test_future_rentals_keep_car_available_and_reject_only_overlaps(fleet_service):
    async def scenario():
        today = date.today()
        car = await fleet_service.add_car(CarCreate(model="Toyota Corolla", year=2024))
        future_start = today + timedelta(days=30)
        future_end = future_start + timedelta(days=2)
        next_week_start = today + timedelta(days=7)
        next_week_end = next_week_start + timedelta(days=2)

        await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Dana Levi",
                start_date=future_start,
                planned_end_date=future_end,
            )
        )
        await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Noa Amir",
                start_date=next_week_start,
                planned_end_date=next_week_end,
            )
        )

        cars = await fleet_service.list_cars()
        assert cars[0].status == VehicleStatus.AVAILABLE

        with pytest.raises(BusinessRuleError):
            await fleet_service.start_rental(
                RentalCreate(
                    car_id=car.id,
                    customer_name="Avi Cohen",
                    start_date=future_start + timedelta(days=1),
                    planned_end_date=future_end + timedelta(days=1),
                )
            )

    asyncio.run(scenario())


def test_start_rental_keeps_planned_end_date(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Toyota Corolla", year=2024))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Dana Levi",
                start_date=date(2026, 5, 25),
                planned_end_date=date(2026, 5, 28),
            )
        )

        assert rental.planned_end_date == date(2026, 5, 28)
        assert rental.end_date is None

    asyncio.run(scenario())


def test_update_rental_planned_end_date(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Kia Niro", year=2024))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Noa Amir",
                start_date=date(2026, 5, 25),
                planned_end_date=date(2026, 5, 28),
            )
        )

        updated = await fleet_service.update_rental_plan(
            rental.id,
            RentalUpdate(planned_end_date=date(2026, 5, 29)),
        )

        assert updated.planned_end_date == date(2026, 5, 29)

    asyncio.run(scenario())


def test_end_rental_marks_car_available(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(CarCreate(model="Mazda 3", year=2023))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Avi Cohen",
                start_date=date(2026, 5, 25),
                planned_end_date=date(2026, 5, 30),
            )
        )
        closed = await fleet_service.end_rental(rental.id, end_date=date(2026, 5, 26))

        cars = await fleet_service.list_cars()
        assert closed.end_date == date(2026, 5, 26)
        assert closed.planned_end_date == date(2026, 5, 30)
        assert cars[0].status == VehicleStatus.AVAILABLE

    asyncio.run(scenario())


def test_cannot_rent_car_in_maintenance(fleet_service):
    async def scenario():
        car = await fleet_service.add_car(
            CarCreate(model="Tesla Model 3", year=2025, status=VehicleStatus.MAINTENANCE)
        )

        with pytest.raises(BusinessRuleError):
            await fleet_service.start_rental(
                RentalCreate(
                    car_id=car.id,
                    customer_name="Noa Amir",
                    start_date=date.today(),
                    planned_end_date=date.today() + timedelta(days=2),
                )
            )

    asyncio.run(scenario())


def test_missing_car_raises_not_found(fleet_service):
    async def scenario():
        with pytest.raises(NotFoundError):
            await fleet_service.update_car("missing", CarUpdate(status=VehicleStatus.AVAILABLE))

    asyncio.run(scenario())
