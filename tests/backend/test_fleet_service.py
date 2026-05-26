"""Unit tests for FleetService app logic.

These tests call the service directly with in-memory repositories. They are
fast unit tests because they do not require MongoDB, RabbitMQ, or Docker.
"""

from datetime import date, timedelta
import asyncio

import pytest

from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate, RentalUpdate
from backend.app.services.fleet_service import FleetService


class CapturingEventPublisher:
    """Fake event publisher used to prove service methods publish events."""

    def __init__(self):
        """Start with no captured queue events."""
        self.events = []

    async def publish(self, event):
        """Capture the event that the service tried to publish."""
        self.events.append(event)


def test_add_and_list_cars(fleet_service):
    """Adding a car should store it and listing cars should return it."""
    async def scenario():
        """Run the async add/list service flow."""
        car = await fleet_service.add_car(CarCreate(model="Hyundai i20", year=2022))
        cars = await fleet_service.list_cars()

        assert car.id == "1"
        assert cars == [car]

    asyncio.run(scenario())


def test_add_car_publishes_queue_event(fleet_service):
    """Adding a car should publish a car.created message for RabbitMQ."""
    async def scenario():
        """Run the async create flow with a capturing publisher."""
        publisher = CapturingEventPublisher()
        service = FleetService(fleet_service.cars, fleet_service.rentals, publisher)

        car = await service.add_car(CarCreate(model="Hyundai i20", year=2022))

        assert publisher.events[0].event_type == "car.created"
        assert publisher.events[0].aggregate_type == "car"
        assert publisher.events[0].aggregate_id == car.id

    asyncio.run(scenario())


def test_update_car_status_to_maintenance(fleet_service):
    """A car can be moved from available to maintenance."""
    async def scenario():
        """Run the async car status update flow."""
        car = await fleet_service.add_car(CarCreate(model="Kia Niro", year=2024))
        updated = await fleet_service.update_car(
            car.id,
            CarUpdate(status=VehicleStatus.MAINTENANCE),
        )

        assert updated.status == VehicleStatus.MAINTENANCE

    asyncio.run(scenario())


def test_start_rental_marks_car_as_rented(fleet_service):
    """A rental that starts today should make the car rented now."""
    async def scenario():
        """Run the async same-day rental creation flow."""
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
    """Future reservations keep the car available today and reject overlaps."""
    async def scenario():
        """Run the async future-reservation conflict rules."""
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


def test_rented_filter_returns_only_cars_rented_today(fleet_service):
    """The rented filter should ignore future reservations and closed rentals."""
    async def scenario():
        """Create current, future, and closed rentals, then filter rented cars."""
        today = date.today()
        current_car = await fleet_service.add_car(CarCreate(model="Current Rental", year=2024))
        future_car = await fleet_service.add_car(CarCreate(model="Future Rental", year=2024))
        closed_car = await fleet_service.add_car(CarCreate(model="Closed Rental", year=2024))

        current_rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=current_car.id,
                customer_name="Current Customer",
                start_date=today,
                planned_end_date=today + timedelta(days=2),
            )
        )
        await fleet_service.start_rental(
            RentalCreate(
                car_id=future_car.id,
                customer_name="Future Customer",
                start_date=today + timedelta(days=7),
                planned_end_date=today + timedelta(days=9),
            )
        )
        closed_rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=closed_car.id,
                customer_name="Closed Customer",
                start_date=today,
                planned_end_date=today + timedelta(days=1),
            )
        )
        await fleet_service.end_rental(closed_rental.id, end_date=today)

        rented_cars = await fleet_service.list_cars(status=VehicleStatus.RENTED)

        assert [car.id for car in rented_cars] == [current_car.id]
        assert current_rental.car_id == current_car.id

    asyncio.run(scenario())


def test_start_rental_keeps_planned_end_date(fleet_service):
    """Scheduling a rental should preserve its planned return date."""
    async def scenario():
        """Run the async rental creation flow and inspect planned dates."""
        today = date.today()
        planned_end = today + timedelta(days=3)
        car = await fleet_service.add_car(CarCreate(model="Toyota Corolla", year=2024))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Dana Levi",
                start_date=today,
                planned_end_date=planned_end,
            )
        )

        assert rental.planned_end_date == planned_end
        assert rental.end_date is None

    asyncio.run(scenario())


def test_update_rental_planned_end_date(fleet_service):
    """An open rental can update its planned return date when legal."""
    async def scenario():
        """Run the async planned return update flow."""
        today = date.today()
        planned_end = today + timedelta(days=3)
        extended_end = today + timedelta(days=4)
        car = await fleet_service.add_car(CarCreate(model="Kia Niro", year=2024))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Noa Amir",
                start_date=today,
                planned_end_date=planned_end,
            )
        )

        updated = await fleet_service.update_rental_plan(
            rental.id,
            RentalUpdate(planned_end_date=extended_end),
        )

        assert updated.planned_end_date == extended_end

    asyncio.run(scenario())


def test_rejects_past_rental_dates(fleet_service):
    """The service rejects past planned start and return dates."""
    async def scenario():
        """Run the async invalid-date cases."""
        today = date.today()
        car = await fleet_service.add_car(CarCreate(model="Hyundai i20", year=2022))

        with pytest.raises(BusinessRuleError):
            await fleet_service.start_rental(
                RentalCreate(
                    car_id=car.id,
                    customer_name="Past Start",
                    start_date=today - timedelta(days=1),
                    planned_end_date=today + timedelta(days=1),
                )
            )

        with pytest.raises(BusinessRuleError):
            await fleet_service.start_rental(
                RentalCreate(
                    car_id=car.id,
                    customer_name="Past Return",
                    start_date=today,
                    planned_end_date=today - timedelta(days=1),
                )
            )

    asyncio.run(scenario())


def test_rejects_past_rental_plan_update(fleet_service):
    """The service rejects updating a rental plan to a past return date."""
    async def scenario():
        """Run the async invalid rental-plan update case."""
        today = date.today()
        car = await fleet_service.add_car(CarCreate(model="Mazda 2", year=2023))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Dana Levi",
                start_date=today,
                planned_end_date=today + timedelta(days=2),
            )
        )

        with pytest.raises(BusinessRuleError):
            await fleet_service.update_rental_plan(
                rental.id,
                RentalUpdate(planned_end_date=today - timedelta(days=1)),
            )

    asyncio.run(scenario())


def test_end_rental_marks_car_available(fleet_service):
    """Ending the current rental should make the car available again."""
    async def scenario():
        """Run the async end-rental flow."""
        today = date.today()
        planned_end = today + timedelta(days=5)
        car = await fleet_service.add_car(CarCreate(model="Mazda 3", year=2023))
        rental = await fleet_service.start_rental(
            RentalCreate(
                car_id=car.id,
                customer_name="Avi Cohen",
                start_date=today,
                planned_end_date=planned_end,
            )
        )
        closed = await fleet_service.end_rental(rental.id, end_date=today)

        cars = await fleet_service.list_cars()
        assert closed.end_date == today
        assert closed.planned_end_date == planned_end
        assert cars[0].status == VehicleStatus.AVAILABLE

    asyncio.run(scenario())


def test_cannot_rent_car_in_maintenance(fleet_service):
    """Cars in maintenance cannot be reserved or rented."""
    async def scenario():
        """Run the async maintenance-car rejection case."""
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
    """Updating an unknown car id should raise NotFoundError."""
    async def scenario():
        """Run the async missing-car update case."""
        with pytest.raises(NotFoundError):
            await fleet_service.update_car("missing", CarUpdate(status=VehicleStatus.AVAILABLE))

    asyncio.run(scenario())
