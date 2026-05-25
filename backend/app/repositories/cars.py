from typing import Any

from backend.app.db.object_ids import parse_object_id
from backend.app.models.documents import CarDocument
from backend.app.models.enums import VehicleStatus
from backend.app.schemas.cars import CarCreate, CarUpdate


class MongoCarRepository:
    def __init__(self, database: Any):
        self.collection = database.cars

    async def create(self, data: CarCreate) -> CarDocument:
        document = data.model_dump(mode="json")
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_document(created)

    async def get(self, car_id: str) -> CarDocument | None:
        object_id = parse_object_id(car_id)
        if object_id is None:
            return None
        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def list(self, status: VehicleStatus | None = None) -> list[CarDocument]:
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status.value

        cars: list[CarDocument] = []
        cursor = self.collection.find(query).sort("model", 1)
        async for document in cursor:
            cars.append(self._to_document(document))
        return cars

    async def update(self, car_id: str, data: CarUpdate) -> CarDocument | None:
        object_id = parse_object_id(car_id)
        if object_id is None:
            return None

        changes = data.model_dump(exclude_none=True, mode="json")
        if changes:
            await self.collection.update_one({"_id": object_id}, {"$set": changes})

        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def delete(self, car_id: str) -> bool:
        object_id = parse_object_id(car_id)
        if object_id is None:
            return False
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1

    async def count_by_status(self) -> dict[str, int]:
        counts = {status.value: 0 for status in VehicleStatus}
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        async for item in self.collection.aggregate(pipeline):
            counts[str(item["_id"])] = int(item["count"])
        return counts

    @staticmethod
    def _to_document(document: dict[str, Any]) -> CarDocument:
        return CarDocument(
            id=str(document["_id"]),
            model=document["model"],
            year=document["year"],
            status=document["status"],
        )
