"""RabbitMQ publisher for fleet domain events."""

import asyncio
import logging
from typing import Protocol

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from backend.app.core.config import AppSettings
from backend.app.messaging.events import FleetEvent

logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    """Interface used by the service layer to publish business events."""

    async def publish(self, event: FleetEvent) -> None:
        pass


class NoOpEventPublisher:
    """Publisher used by tests and local runs that do not need RabbitMQ."""

    async def publish(self, event: FleetEvent) -> None:
        logger.debug("Skipped event publish event_type=%s", event.event_type)


class RabbitMQEventPublisher:
    """Publishes fleet events to RabbitMQ."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None
        self.exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self, attempts: int = 10, delay_seconds: float = 1.0) -> None:
        """Connect to RabbitMQ with retries for Docker startup ordering."""
        for attempt in range(1, attempts + 1):
            try:
                self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
                self.channel = await self.connection.channel()
                self.exchange = await self.channel.declare_exchange(
                    self.settings.event_exchange_name,
                    ExchangeType.DIRECT,
                    durable=True,
                )
                queue = await self.channel.declare_queue(
                    self.settings.event_queue_name,
                    durable=True,
                )
                await queue.bind(
                    self.exchange,
                    routing_key=self.settings.event_routing_key,
                )
                logger.info("Connected to RabbitMQ queue=%s", self.settings.event_queue_name)
                return
            except Exception as exc:
                logger.warning(
                    "RabbitMQ connection attempt %s/%s failed: %s",
                    attempt,
                    attempts,
                    exc,
                )
                await asyncio.sleep(delay_seconds)

        raise RuntimeError("Could not connect to RabbitMQ.")

    async def publish(self, event: FleetEvent) -> None:
        if self.exchange is None:
            await self.connect()

        message = Message(
            body=event.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self.exchange.publish(message, routing_key=self.settings.event_routing_key)
        logger.info(
            "Published event event_type=%s aggregate_id=%s",
            event.event_type,
            event.aggregate_id,
        )

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
