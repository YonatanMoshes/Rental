"""Request/response schemas for car endpoints.

These Pydantic models validate input data and document API contracts.
CarCreate: new car payload
CarUpdate: partial car update payload
CarRead: car response from API
"""

from pydantic import BaseModel, Field

from backend.app.models.enums import VehicleStatus

MIN_CAR_YEAR = 1950
MAX_CAR_YEAR = 2026


class CarCreate(BaseModel):
    """Request body for creating a new car."""
    model: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=MIN_CAR_YEAR, le=MAX_CAR_YEAR)
    status: VehicleStatus = VehicleStatus.AVAILABLE


class CarUpdate(BaseModel):
    """Request body for updating a car. All fields are optional."""
    model: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=MIN_CAR_YEAR, le=MAX_CAR_YEAR)
    status: VehicleStatus | None = None


class CarRead(BaseModel):
    """API response containing a complete car record."""
    id: str
    model: str
    year: int
    status: VehicleStatus
