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
    return await service.add_car(data)


@router.get("", response_model=list[CarRead])
async def list_cars(
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    service: FleetService = Depends(get_fleet_service),
) -> list[CarRead]:
    return await service.list_cars(status=status_filter)


@router.patch("/{car_id}", response_model=CarRead)
async def update_car(
    car_id: str,
    data: CarUpdate,
    service: FleetService = Depends(get_fleet_service),
) -> CarRead:
    return await service.update_car(car_id, data)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: str,
    service: FleetService = Depends(get_fleet_service),
) -> Response:
    await service.delete_car(car_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
