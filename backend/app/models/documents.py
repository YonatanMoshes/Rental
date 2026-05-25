from datetime import date

from pydantic import BaseModel

from backend.app.models.enums import VehicleStatus


class CarDocument(BaseModel):
    id: str
    model: str
    year: int
    status: VehicleStatus


class RentalDocument(BaseModel):
    id: str
    car_id: str
    customer_name: str
    start_date: date
    end_date: date | None = None
