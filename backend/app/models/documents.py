"""Domain model documents representing database records.

These models map directly to MongoDB documents. They're used internally
by repositories to convert between database records and Python objects.
"""

from datetime import date

from pydantic import BaseModel

from backend.app.models.enums import VehicleStatus


class CarDocument(BaseModel):
    """A car record as stored in MongoDB."""
    id: str
    model: str
    year: int
    status: VehicleStatus


class RentalDocument(BaseModel):
    """A rental record as stored in MongoDB.
    
    A rental is considered 'active' (open) when end_date is None.
    """
    id: str
    car_id: str
    customer_name: str
    start_date: date
    planned_end_date: date | None = None
    end_date: date | None = None
