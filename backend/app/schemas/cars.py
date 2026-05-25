from pydantic import BaseModel, Field

from backend.app.models.enums import VehicleStatus


class CarCreate(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1886, le=2100)
    status: VehicleStatus = VehicleStatus.AVAILABLE


class CarUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=1886, le=2100)
    status: VehicleStatus | None = None


class CarRead(BaseModel):
    id: str
    model: str
    year: int
    status: VehicleStatus
