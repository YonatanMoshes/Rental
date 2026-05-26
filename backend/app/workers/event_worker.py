"""Background worker for asynchronous observability work.

The API publishes fleet events after successful writes. This worker consumes
those messages and handles the slower follow-up tasks: storing the audit event,
writing the log line, and refreshing fleet metrics outside the user request.
"""

import asyncio
import logging
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.core.metrics import refresh_metrics
from backend.app.db.indexes import ensure_database_indexes
from backend.app.db.mongodb import close_mongodb_connection, connect_to_mongodb, get_database
from backend.app.messaging.consumer import RabbitMQEventConsumer
from backend.app.messaging.events import FleetEvent
from backend.app.repositories.cars import MongoCarRepository
from backend.app.repositories.events import MongoEventRepository
from backend.app.repositories.rentals import MongoRentalRepository


async def process_fleet_event(
    event: FleetEvent,
    event_repository: MongoEventRepository,
    car_repository: Any,
    rental_repository: Any,
    logger: logging.Logger,
) -> None:
    """Handle all post-request observability work for one queue event."""
    await event_repository.save(event)
    await refresh_metrics(car_repository, rental_repository)
    logger.info(
        "Processed fleet event type=%s aggregate_type=%s aggregate_id=%s",
        event.event_type,
        event.aggregate_type,
        event.aggregate_id,
    )


async def run_worker() -> None:
    """Start the queue consumer and keep it running until the process stops."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_file, settings.log_timezone)
    logger = logging.getLogger(__name__)

    await connect_to_mongodb(settings)
    await ensure_database_indexes(get_database())
    database = get_database()
    event_repository = MongoEventRepository(database)
    car_repository = MongoCarRepository(database)
    rental_repository = MongoRentalRepository(database)

    async def save_event(event: FleetEvent) -> None:
        """Adapt the queue consumer callback to the worker's full event pipeline."""
        await process_fleet_event(
            event,
            event_repository,
            car_repository,
            rental_repository,
            logger,
        )

    consumer = RabbitMQEventConsumer(settings, handler=save_event)
    await consumer.start()
    logger.info("Fleet event worker started")

    try:
        await asyncio.Future()
    finally:
        await consumer.close()
        await close_mongodb_connection()


def main() -> None:
    """Synchronous entry point used by Docker and local worker commands."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
