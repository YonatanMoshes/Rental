"""MongoDB connection management.

Handles connection lifecycle, retry logic, and provides the database instance
to the application through dependency injection.
"""

import asyncio
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from backend.app.core.config import AppSettings


class MongoDatabase:
    """Holds MongoDB connection state."""
    client: AsyncMongoClient | None = None
    database: Any | None = None


mongo_database = MongoDatabase()


async def connect_to_mongodb(settings: AppSettings) -> None:
    """Connect to MongoDB with retry logic (up to 10 attempts, 1 second apart)."""
    client = AsyncMongoClient(settings.mongodb_uri)
    for attempt in range(1, 11):
        try:
            await client.admin.command("ping")
            break
        except PyMongoError:
            if attempt == 10:
                raise
            await asyncio.sleep(1)
    mongo_database.client = client
    mongo_database.database = client[settings.mongodb_database]


async def close_mongodb_connection() -> None:
    """Close the MongoDB connection and cleanup resources."""
    if mongo_database.client is not None:
        await mongo_database.client.close()
    mongo_database.client = None
    mongo_database.database = None


def get_database() -> Any:
    """Get the MongoDB database instance (used for dependency injection)."""
    if mongo_database.database is None:
        raise RuntimeError("MongoDB connection has not been initialized.")
    return mongo_database.database
