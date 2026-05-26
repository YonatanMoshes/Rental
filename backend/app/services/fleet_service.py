"""Business logic for fleet management.

Handles car and rental operations with business rule validation.
Protocols define interfaces for repository dependencies.
"""

import logging
from datetime import date
from typing import Protocol

from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.core.metrics import track_operation
from backend.app.messaging.events import FleetEvent, car_event, rental_event
from backend.app.messaging.publisher import EventPublisher, NoOpEventPublisher
from backend.app.models.documents import CarDocument, RentalDocument
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate, RentalUpdate

logger = logging.getLogger(__name__)


class CarRepository(Protocol):
    """Operations the service needs from any car storage implementation."""

    async def create(self, data: CarCreate) -> CarDocument:
        """Persist a new car and return the stored document."""
        pass

    async def get(self, car_id: str) -> CarDocument | None:
        """Return one car by id, or None when it does not exist."""
        pass

    async def list(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        """Return cars from storage, optionally filtered by stored status."""
        pass

    async def update(self, car_id: str, data: CarUpdate) -> CarDocument | None:
        """Apply allowed car field changes and return the updated car."""
        pass

    async def delete(self, car_id: str) -> bool:
        """Delete one car and return whether anything was removed."""
        pass

    async def count_by_status(self) -> dict[str, int]:
        """Return counts grouped by status for metrics refreshes."""
        pass


class RentalRepository(Protocol):
    """Operations the service needs from any rental storage implementation."""

    async def create(self, data: RentalCreate) -> RentalDocument:
        """Persist a new rental schedule and return the stored document."""
        pass

    async def get(self, rental_id: str) -> RentalDocument | None:
        """Return one rental by id, or None when it does not exist."""
        pass

    async def list(self, open_only: bool | None = None) -> list[RentalDocument]:
        """Return rentals, optionally limiting the result to open or closed rows."""
        pass

    async def active_for_car(self, car_id: str) -> RentalDocument | None:
        """Return the rental that makes this car rented today, if one exists."""
        pass

    async def open_for_car(self, car_id: str) -> RentalDocument | None:
        """Return any not-yet-ended rental for this car, including future plans."""
        pass

    async def overlapping_for_car(
        self,
        car_id: str,
        start_date: date,
        planned_end_date: date,
        exclude_rental_id: str | None = None,
    ) -> RentalDocument | None:
        """Find a rental that already reserves any part of the requested dates."""
        pass

    async def end(self, rental_id: str, end_date: date) -> RentalDocument | None:
        """Close an open rental with the actual end date."""
        pass

    async def update(self, rental_id: str, data: RentalUpdate) -> RentalDocument | None:
        """Update editable rental planning fields and return the updated rental."""
        pass

    async def count_open(self) -> int:
        """Return how many rentals have not been ended yet."""
        pass


class FleetService:
    """Core business logic service for managing the rental fleet."""
    def __init__(
        self,
        cars: CarRepository,
        rentals: RentalRepository,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize with injected repository dependencies."""
        self.cars = cars
        self.rentals = rentals
        self.event_publisher = event_publisher or NoOpEventPublisher()

    @track_operation("add_car")
    async def add_car(self, data: CarCreate) -> CarDocument:
        """Create a car, then publish an event for async logging and metrics."""
        car = await self.cars.create(data)
        await self._publish_event(car_event("car.created", car))
        return car

    @track_operation("list_cars")
    async def list_cars(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        """List cars, optionally filtered by status."""
        cars = [await self._with_current_schedule_status(car) for car in await self.cars.list()]
        if status is not None:
            cars = [car for car in cars if car.status == status]
        return cars

    @track_operation("update_car")
    async def update_car(self, car_id: str, data: CarUpdate) -> CarDocument:
        """Update car details with business rule validation.
        
        Business rules:
        - Cannot change status away from RENTED if an active rental exists
        - Cannot mark car as RENTED directly; must use rental flow
        """
        car = await self._require_car(car_id)

        if data.status is not None:
            active_rental = await self.rentals.active_for_car(car.id)
            if active_rental and data.status != VehicleStatus.RENTED:
                raise BusinessRuleError("End the active rental before changing this car status.")
            if data.status == VehicleStatus.RENTED and active_rental is None:
                raise BusinessRuleError("Use the rental flow to mark a car as rented.")

        updated = await self.cars.update(car.id, data)
        if updated is None:
            raise NotFoundError(f"Car {car_id} was not found.")

        await self._publish_event(car_event("car.updated", updated))
        return updated

    @track_operation("delete_car")
    async def delete_car(self, car_id: str) -> None:
        """Delete a car with business rule validation.
        
        Cannot delete a car that has an active rental.
        """
        car = await self._require_car(car_id)
        if await self.rentals.open_for_car(car.id):
            raise BusinessRuleError("Cannot delete a car with an open or scheduled rental.")

        deleted = await self.cars.delete(car.id)
        if not deleted:
            raise NotFoundError(f"Car {car_id} was not found.")

        await self._publish_event(car_event("car.deleted", car))

    @track_operation("start_rental")
    async def start_rental(self, data: RentalCreate) -> RentalDocument:
        """Create a legal rental plan and mark the car rented only if it starts now."""
        today = date.today()
        car = await self._require_car(data.car_id)
        if car.status == VehicleStatus.MAINTENANCE:
            raise BusinessRuleError("Cars in maintenance cannot be reserved.")
        if data.start_date < today:
            raise BusinessRuleError("Planned start date cannot be in the past.")
        if data.planned_end_date < data.start_date:
            raise BusinessRuleError("Planned end date cannot be before the rental start date.")
        if data.planned_end_date < today:
            raise BusinessRuleError("Planned return date cannot be in the past.")
        if await self.rentals.overlapping_for_car(car.id, data.start_date, data.planned_end_date):
            raise BusinessRuleError("This car already has a rental during this date range.")

        rental = await self.rentals.create(data)
        if self._rental_covers_date(rental, today):
            await self.cars.update(car.id, CarUpdate(status=VehicleStatus.RENTED))

        await self._publish_event(rental_event("rental.started", rental))
        return rental

    @track_operation("list_rentals")
    async def list_rentals(self, open_only: bool | None = None) -> list[RentalDocument]:
        """Return rentals for the dashboard table, optionally filtered by open state."""
        rentals = await self.rentals.list(open_only=open_only)
        return rentals

    @track_operation("update_rental_plan")
    async def update_rental_plan(self, rental_id: str, data: RentalUpdate) -> RentalDocument:
        """Change the planned return date when the new date range is still legal."""
        rental = await self.rentals.get(rental_id)
        if rental is None:
            raise NotFoundError(f"Rental {rental_id} was not found.")
        if rental.end_date is not None:
            raise BusinessRuleError("Cannot edit the planned end date of a closed rental.")
        if data.planned_end_date < rental.start_date:
            raise BusinessRuleError("Planned end date cannot be before the rental start date.")
        if data.planned_end_date < date.today():
            raise BusinessRuleError("Planned return date cannot be in the past.")
        if await self.rentals.overlapping_for_car(
            rental.car_id,
            rental.start_date,
            data.planned_end_date,
            exclude_rental_id=rental.id,
        ):
            raise BusinessRuleError("This car already has a rental during this date range.")

        updated = await self.rentals.update(rental.id, data)
        if updated is None:
            raise NotFoundError(f"Rental {rental_id} was not found.")

        await self._publish_event(rental_event("rental.plan_updated", updated))
        return updated

    @track_operation("end_rental")
    async def end_rental(self, rental_id: str, end_date: date | None = None) -> RentalDocument:
        """Close a rental immediately or on a selected legal end date."""
        rental = await self.rentals.get(rental_id)
        if rental is None:
            raise NotFoundError(f"Rental {rental_id} was not found.")
        if rental.end_date is not None:
            raise BusinessRuleError("Rental is already closed.")

        closed_on = end_date or date.today()
        if closed_on < date.today():
            raise BusinessRuleError("End date cannot be in the past.")
        if closed_on < rental.start_date:
            raise BusinessRuleError("End date cannot be before the rental start date.")

        closed_rental = await self.rentals.end(rental.id, closed_on)
        if closed_rental is None:
            raise NotFoundError(f"Rental {rental_id} was not found.")

        active_rental = await self.rentals.active_for_car(rental.car_id)
        if active_rental is None:
            await self.cars.update(rental.car_id, CarUpdate(status=VehicleStatus.AVAILABLE))
        await self._publish_event(rental_event("rental.ended", closed_rental))
        return closed_rental

    async def _require_car(self, car_id: str) -> CarDocument:
        """Load a car or raise the API-friendly not-found error."""
        car = await self.cars.get(car_id)
        if car is None:
            raise NotFoundError(f"Car {car_id} was not found.")
        return car

    async def _with_current_schedule_status(self, car: CarDocument) -> CarDocument:
        """Overlay today's real availability on top of the stored car status."""
        if car.status == VehicleStatus.MAINTENANCE:
            return car
        if await self.rentals.active_for_car(car.id):
            return car.model_copy(update={"status": VehicleStatus.RENTED})
        return car.model_copy(update={"status": VehicleStatus.AVAILABLE})

    @staticmethod
    def _rental_covers_date(rental: RentalDocument, check_date: date) -> bool:
        """Return whether an open rental covers the requested calendar day."""
        planned_end_date = rental.planned_end_date or rental.start_date
        return rental.end_date is None and rental.start_date <= check_date <= planned_end_date

    async def _publish_event(self, event: FleetEvent) -> None:
        """Send a queue event so logging and metrics can happen after the response."""
        try:
            await self.event_publisher.publish(event)
        except Exception:
            logger.exception("Failed to publish fleet event event_type=%s", event.event_type)
