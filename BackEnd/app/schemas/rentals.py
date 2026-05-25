from datetime import date

from pydantic import BaseModel, Field


class RentalCreate(BaseModel):
    car_id: str
    customer_name: str = Field(min_length=1, max_length=120)
    start_date: date = Field(default_factory=date.today)


class RentalRead(BaseModel):
    id: str
    car_id: str
    customer_name: str
    start_date: date
    end_date: date | None = None
