"""Background worker that consumes RabbitMQ events and stores them in MongoDB."""

import asyncio
import logging

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.db.indexes import ensure_database_indexes
from backend.app.db.mongodb import close_mongodb_connection, connect_to_mongodb, get_database
from backend.app.messaging.consumer import RabbitMQEventConsumer
from backend.app.messaging.events import FleetEvent
from backend.app.repositories.events import MongoEventRepository


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_file)
    logger = logging.getLogger(__name__)

    await connect_to_mongodb(settings)
    await ensure_database_indexes(get_database())
    repository = MongoEventRepository(get_database())

    async def save_event(event: FleetEvent) -> None:
        await repository.save(event)

    consumer = RabbitMQEventConsumer(settings, handler=save_event)
    await consumer.start()
    logger.info("Fleet event worker started")

    try:
        await asyncio.Future()
    finally:
        await consumer.close()
        await close_mongodb_connection()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
