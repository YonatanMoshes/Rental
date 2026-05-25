"""Request/response schemas for car endpoints.

These Pydantic models validate input data and document API contracts.
CarCreate: new car payload
CarUpdate: partial car update payload
CarRead: car response from API
"""

from pydantic import BaseModel, Field

from backend.app.models.enums import VehicleStatus


class CarCreate(BaseModel):
    """Request body for creating a new car."""
    model: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1886, le=2100)
    status: VehicleStatus = VehicleStatus.AVAILABLE


class CarUpdate(BaseModel):
    """Request body for updating a car. All fields are optional."""
    model: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=1886, le=2100)
    status: VehicleStatus | None = None


class CarRead(BaseModel):
    """API response containing a complete car record."""
    id: str
    model: str
    year: int
    status: VehicleStatus
