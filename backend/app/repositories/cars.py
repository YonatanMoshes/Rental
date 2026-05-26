"""MongoDB-backed repository for car persistence.

Handles all database operations for cars including CRUD operations,
filtering by status, and aggregation for metrics.
"""

from typing import Any

from backend.app.db.object_ids import parse_object_id
from backend.app.models.documents import CarDocument
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate


class MongoCarRepository:
    """MongoDB repository for car documents."""
    def __init__(self, database: Any):
        """Initialize with MongoDB database instance."""
        self.collection = database.cars

    async def create(self, data: CarCreate) -> CarDocument:
        """Create and store a new car document."""
        document = data.model_dump(mode="json")
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_document(created)

    async def get(self, car_id: str) -> CarDocument | None:
        """Retrieve a single car by ID."""
        object_id = parse_object_id(car_id)
        if object_id is None:
            return None
        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def list(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        """List all cars, optionally filtered by status, sorted by model name."""
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status.value

        cars: list[CarDocument] = []
        cursor = self.collection.find(query).sort("model", 1)
        async for document in cursor:
            cars.append(self._to_document(document))
        return cars

    async def update(self, car_id: str, data: CarUpdate) -> CarDocument | None:
        """Update car fields (only non-None fields are updated)."""
        object_id = parse_object_id(car_id)
        if object_id is None:
            return None

        changes = data.model_dump(exclude_none=True, mode="json")
        if changes:
            await self.collection.update_one({"_id": object_id}, {"$set": changes})

        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def delete(self, car_id: str) -> bool:
        """Delete a car document. Returns True if a document was deleted."""
        object_id = parse_object_id(car_id)
        if object_id is None:
            return False
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1

    async def count_by_status(self) -> dict[str, int]:
        """Get count of cars in each status (used for dashboard metrics)."""
        counts = {status.value: 0 for status in VehicleStatus}
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        cursor = await self.collection.aggregate(pipeline)
        async for item in cursor:
            counts[str(item["_id"])] = int(item["count"])
        return counts

    @staticmethod
    def _to_document(document: dict[str, Any]) -> CarDocument:
        """Convert a raw MongoDB document into the clean API/domain model."""
        return CarDocument(
            id=str(document["_id"]),
            model=document["model"],
            year=document["year"],
            status=document["status"],
        )
