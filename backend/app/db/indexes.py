from typing import Any


async def ensure_database_indexes(database: Any) -> None:
    await database.cars.create_index("status")
    await database.rentals.create_index([("car_id", 1), ("end_date", 1)])
