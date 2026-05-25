import asyncio
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from backend.app.core.config import AppSettings


class MongoDatabase:
    client: AsyncMongoClient | None = None
    database: Any | None = None


mongo_database = MongoDatabase()


async def connect_to_mongodb(settings: AppSettings) -> None:
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
    if mongo_database.client is not None:
        await mongo_database.client.close()
    mongo_database.client = None
    mongo_database.database = None


def get_database() -> Any:
    if mongo_database.database is None:
        raise RuntimeError("MongoDB connection has not been initialized.")
    return mongo_database.database
