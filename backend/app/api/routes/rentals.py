"""Rental management API endpoints.

Handles all rental-related operations:
- Start a new rental (which automatically marks the car as RENTED)
- List rentals (with optional open-only filtering)
- End a rental (which frees up the car for future rentals)
"""

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
    """Start a new rental for a customer.
    
    - Car must exist and be available
    - Car cannot already have an active rental
    - Car status will be changed to RENTED
    """
    return await service.start_rental(data)


@router.get("", response_model=list[RentalRead])
async def list_rentals(
    open_only: bool | None = None,
    service: FleetService = Depends(get_fleet_service),
) -> list[RentalRead]:
    """Get all rentals, optionally filtered by status.
    
    Query params:
    - open_only=true: only rentals without an end_date (active rentals)
    - open_only=false: only rentals with an end_date (completed rentals)
    - omit open_only: all rentals
    """
    return await service.list_rentals(open_only=open_only)


@router.post("/{rental_id}/end", response_model=RentalRead)
async def end_rental(
    rental_id: str,
    end_date: date | None = None,
    service: FleetService = Depends(get_fleet_service),
) -> RentalRead:
    """Mark a rental as ended and free up the car.
    
    If end_date is not provided, defaults to today.
    Car status will be changed back to AVAILABLE.
    """
    return await service.end_rental(rental_id, end_date=end_date)
