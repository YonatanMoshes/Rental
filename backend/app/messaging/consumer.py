"""RabbitMQ consumer for fleet domain events."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika import ExchangeType, IncomingMessage

from backend.app.core.config import AppSettings
from backend.app.messaging.events import FleetEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[FleetEvent], Awaitable[None]]


class RabbitMQEventConsumer:
    """Consumes fleet events from RabbitMQ and passes them to a handler."""

    def __init__(self, settings: AppSettings, handler: EventHandler):
        self.settings = settings
        self.handler = handler
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None

    async def start(self, attempts: int = 10, delay_seconds: float = 1.0) -> None:
        for attempt in range(1, attempts + 1):
            try:
                self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
                break
            except Exception as exc:
                logger.warning(
                    "RabbitMQ consumer connection attempt %s/%s failed: %s",
                    attempt,
                    attempts,
                    exc,
                )
                await asyncio.sleep(delay_seconds)

        if self.connection is None:
            raise RuntimeError("Could not connect RabbitMQ consumer.")

        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)

        exchange = await self.channel.declare_exchange(
            self.settings.event_exchange_name,
            ExchangeType.DIRECT,
            durable=True,
        )
        queue = await self.channel.declare_queue(
            self.settings.event_queue_name,
            durable=True,
        )
        await queue.bind(exchange, routing_key=self.settings.event_routing_key)
        await queue.consume(self._handle_message)
        logger.info("Consuming RabbitMQ queue=%s", self.settings.event_queue_name)

    async def _handle_message(self, message: IncomingMessage) -> None:
        async with message.process(requeue=True):
            event = FleetEvent.model_validate_json(message.body)
            await self.handler(event)
            logger.info(
                "Consumed event event_type=%s aggregate_id=%s",
                event.event_type,
                event.aggregate_id,
            )

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
