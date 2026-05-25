"""Car management API endpoints.

Handles all car-related operations:
- Create new cars in the fleet
- List cars (with optional status filtering)
- Update car details or status
- Delete cars from the system
"""

from fastapi import APIRouter, Depends, Query, Response, status

from backend.app.api.dependencies import get_fleet_service
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarRead, CarUpdate
from backend.app.services.fleet_service import FleetService

router = APIRouter(prefix="/api/cars", tags=["cars"])


@router.post("", response_model=CarRead, status_code=status.HTTP_201_CREATED)
async def add_car(
    data: CarCreate,
    service: FleetService = Depends(get_fleet_service),
) -> CarRead:
    """Create a new car and add it to the fleet."""
    return await service.add_car(data)


@router.get("", response_model=list[CarRead])
async def list_cars(
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    service: FleetService = Depends(get_fleet_service),
) -> list[CarRead]:
    """Get all cars, optionally filtered by status (available, rented, maintenance)."""
    return await service.list_cars(status=status_filter)


@router.patch("/{car_id}", response_model=CarRead)
async def update_car(
    car_id: str,
    data: CarUpdate,
    service: FleetService = Depends(get_fleet_service),
) -> CarRead:
    """Update car details (model, year, status).
    
    Note: Cannot change status to 'rented' directly - use the rental API.
    Cannot change status away from 'rented' while a rental is active.
    """
    return await service.update_car(car_id, data)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: str,
    service: FleetService = Depends(get_fleet_service),
) -> Response:
    """Delete a car from the fleet.
    
    Cannot delete a car with an active rental.
    """
    await service.delete_car(car_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
