"""Repository for consumed fleet event messages."""

from typing import Any

from backend.app.messaging.events import FleetEvent


class MongoEventRepository:
    """Stores consumed RabbitMQ events in MongoDB for audit and demos."""

    def __init__(self, database: Any):
        self.collection = database.fleet_events

    async def save(self, event: FleetEvent) -> None:
        document = event.model_dump(mode="json")
        await self.collection.update_one(
            {"event_id": event.event_id},
            {"$setOnInsert": document},
            upsert=True,
        )

    async def list(self, limit: int = 50) -> list[FleetEvent]:
        events: list[FleetEvent] = []
        cursor = self.collection.find({}).sort("occurred_at", -1).limit(limit)
        async for document in cursor:
            document.pop("_id", None)
            events.append(FleetEvent.model_validate(document))
        return events
