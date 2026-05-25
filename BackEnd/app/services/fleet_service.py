import logging
from datetime import date
from typing import Protocol

from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.core.metrics import refresh_metrics, track_operation
from backend.app.models.documents import CarDocument, RentalDocument
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate
from backend.app.schemas.rentals import RentalCreate

logger = logging.getLogger(__name__)


class CarRepository(Protocol):
    async def create(self, data: CarCreate) -> CarDocument:
        pass

    async def get(self, car_id: str) -> CarDocument | None:
        pass

    async def list(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        pass

    async def update(self, car_id: str, data: CarUpdate) -> CarDocument | None:
        pass

    async def delete(self, car_id: str) -> bool:
        pass

    async def count_by_status(self) -> dict[str, int]:
        pass


class RentalRepository(Protocol):
    async def create(self, data: RentalCreate) -> RentalDocument:
        pass

    async def get(self, rental_id: str) -> RentalDocument | None:
        pass

    async def list(self, open_only: bool | None = None) -> list[RentalDocument]:
        pass

    async def active_for_car(self, car_id: str) -> RentalDocument | None:
        pass

    async def end(self, rental_id: str, end_date: date) -> RentalDocument | None:
        pass

    async def count_open(self) -> int:
        pass


class FleetService:
    def __init__(self, cars: CarRepository, rentals: RentalRepository):
        self.cars = cars
        self.rentals = rentals

    @track_operation("add_car")
    async def add_car(self, data: CarCreate) -> CarDocument:
        car = await self.cars.create(data)
        logger.info("Added car id=%s model=%s year=%s", car.id, car.model, car.year)
        await refresh_metrics(self.cars, self.rentals)
        return car

    @track_operation("list_cars")
    async def list_cars(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        cars = await self.cars.list(status=status)
        logger.info("Listed cars count=%s status=%s", len(cars), status)
        return cars

    @track_operation("update_car")
    async def update_car(self, car_id: str, data: CarUpdate) -> CarDocument:
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

        logger.info("Updated car id=%s status=%s", updated.id, updated.status)
        await refresh_metrics(self.cars, self.rentals)
        return updated

    @track_operation("delete_car")
    async def delete_car(self, car_id: str) -> None:
        car = await self._require_car(car_id)
        if await self.rentals.active_for_car(car.id):
            raise BusinessRuleError("Cannot delete a car with an active rental.")

        deleted = await self.cars.delete(car.id)
        if not deleted:
            raise NotFoundError(f"Car {car_id} was not found.")

        logger.info("Deleted car id=%s", car.id)
        await refresh_metrics(self.cars, self.rentals)

    @track_operation("start_rental")
    async def start_rental(self, data: RentalCreate) -> RentalDocument:
        car = await self._require_car(data.car_id)
        if car.status != VehicleStatus.AVAILABLE:
            raise BusinessRuleError("Only available cars can be rented.")
        if await self.rentals.active_for_car(car.id):
            raise BusinessRuleError("This car already has an active rental.")

        rental = await self.rentals.create(data)
        await self.cars.update(car.id, CarUpdate(status=VehicleStatus.RENTED))

        logger.info(
            "Started rental id=%s car_id=%s customer=%s",
            rental.id,
            rental.car_id,
            rental.customer_name,
        )
        await refresh_metrics(self.cars, self.rentals)
        return rental

    @track_operation("list_rentals")
    async def list_rentals(self, open_only: bool | None = None) -> list[RentalDocument]:
        rentals = await self.rentals.list(open_only=open_only)
        logger.info("Listed rentals count=%s open_only=%s", len(rentals), open_only)
        return rentals

    @track_operation("end_rental")
    async def end_rental(self, rental_id: str, end_date: date | None = None) -> RentalDocument:
        rental = await self.rentals.get(rental_id)
        if rental is None:
            raise NotFoundError(f"Rental {rental_id} was not found.")
        if rental.end_date is not None:
            raise BusinessRuleError("Rental is already closed.")

        closed_on = end_date or date.today()
        if closed_on < rental.start_date:
            raise BusinessRuleError("End date cannot be before the rental start date.")

        closed_rental = await self.rentals.end(rental.id, closed_on)
        if closed_rental is None:
            raise NotFoundError(f"Rental {rental_id} was not found.")

        await self.cars.update(rental.car_id, CarUpdate(status=VehicleStatus.AVAILABLE))
        logger.info("Ended rental id=%s car_id=%s", rental.id, rental.car_id)
        await refresh_metrics(self.cars, self.rentals)
        return closed_rental

    async def _require_car(self, car_id: str) -> CarDocument:
        car = await self.cars.get(car_id)
        if car is None:
            raise NotFoundError(f"Car {car_id} was not found.")
        return car
