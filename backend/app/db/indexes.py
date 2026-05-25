"""Database index creation for performance optimization.

Ensures proper indexes exist for common queries.
"""

from typing import Any


async def ensure_database_indexes(database: Any) -> None:
    """Create database indexes for efficient queries.
    
    Indexes:
    - cars.status: Fast filtering by car status
    - rentals.[car_id, end_date]: Fast lookup of active rentals per car
    """
    await database.cars.create_index("status")
    await database.rentals.create_index([("car_id", 1), ("end_date", 1)])
