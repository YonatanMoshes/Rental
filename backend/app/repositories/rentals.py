from datetime import date
from typing import Any

from backend.app.db.object_ids import parse_object_id
from backend.app.models.documents import RentalDocument
from backend.app.schemas.rentals import RentalCreate


class MongoRentalRepository:
    def __init__(self, database: Any):
        self.collection = database.rentals

    async def create(self, data: RentalCreate) -> RentalDocument:
        document = data.model_dump(mode="json")
        document["end_date"] = None
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_document(created)

    async def get(self, rental_id: str) -> RentalDocument | None:
        object_id = parse_object_id(rental_id)
        if object_id is None:
            return None
        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def list(self, open_only: bool | None = None) -> list[RentalDocument]:
        query: dict[str, Any] = {}
        if open_only is True:
            query["end_date"] = None
        elif open_only is False:
            query["end_date"] = {"$ne": None}

        rentals: list[RentalDocument] = []
        cursor = self.collection.find(query).sort("start_date", -1)
        async for document in cursor:
            rentals.append(self._to_document(document))
        return rentals

    async def active_for_car(self, car_id: str) -> RentalDocument | None:
        document = await self.collection.find_one({"car_id": car_id, "end_date": None})
        return self._to_document(document) if document else None

    async def end(self, rental_id: str, end_date: date) -> RentalDocument | None:
        object_id = parse_object_id(rental_id)
        if object_id is None:
            return None
        await self.collection.update_one(
            {"_id": object_id},
            {"$set": {"end_date": end_date.isoformat()}},
        )
        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def count_open(self) -> int:
        return int(await self.collection.count_documents({"end_date": None}))

    @staticmethod
    def _to_document(document: dict[str, Any]) -> RentalDocument:
        return RentalDocument(
            id=str(document["_id"]),
            car_id=document["car_id"],
            customer_name=document["customer_name"],
            start_date=document["start_date"],
            end_date=document.get("end_date"),
        )
