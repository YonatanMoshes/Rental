"""Request/response schemas for rental endpoints.

RentalCreate: start a new rental
RentalRead: rental response from API
"""

from datetime import date

from pydantic import BaseModel, Field


class RentalCreate(BaseModel):
    """Request body for starting a new rental."""
    car_id: str
    customer_name: str = Field(min_length=1, max_length=120)
    start_date: date = Field(default_factory=date.today)
    planned_end_date: date


class RentalUpdate(BaseModel):
    """Request body for editing an open rental."""
    planned_end_date: date


class RentalRead(BaseModel):
    """API response containing a complete rental record."""
    id: str
    car_id: str
    customer_name: str
    start_date: date
    planned_end_date: date | None = None
    end_date: date | None = None
