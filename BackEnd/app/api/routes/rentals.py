from datetime import date

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_fleet_service
from backend.app.schemas.rentals import RentalCreate, RentalRead
from backend.app.services.fleet_service import FleetService

router = APIRouter(prefix="/api/rentals", tags=["rentals"])


@router.post("", response_model=RentalRead, status_code=201)
async def start_rental(
    data: RentalCreate,
    service: FleetService = Depends(get_fleet_service),
) -> RentalRead:
    return await service.start_rental(data)


@router.get("", response_model=list[RentalRead])
async def list_rentals(
    open_only: bool | None = None,
    service: FleetService = Depends(get_fleet_service),
) -> list[RentalRead]:
    return await service.list_rentals(open_only=open_only)


@router.post("/{rental_id}/end", response_model=RentalRead)
async def end_rental(
    rental_id: str,
    end_date: date | None = None,
    service: FleetService = Depends(get_fleet_service),
) -> RentalRead:
    return await service.end_rental(rental_id, end_date=end_date)
