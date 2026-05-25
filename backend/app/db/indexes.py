"""Database index creation for performance optimization.

Ensures proper indexes exist for common queries.
"""

from typing import Any


async def ensure_database_indexes(database: Any) -> None:
    """Create database indexes for efficient queries.
    
    Indexes:
    - cars.status: Fast filtering by car status
    - rentals.[car_id, end_date]: Fast lookup of active rentals per car
    - fleet_events.event_id: Idempotent event consumption
    - fleet_events.occurred_at: Fast event audit sorting
    """
    await database.cars.create_index("status")
    await database.rentals.create_index([("car_id", 1), ("end_date", 1)])
    await database.fleet_events.create_index("event_id", unique=True)
    await database.fleet_events.create_index("occurred_at")
