"""MongoDB-backed repository for rental persistence.

Handles all database operations for rentals including CRUD operations,
filtering by open/closed status, and querying active rentals per car.
"""

from datetime import date
from typing import Any

from backend.app.db.object_ids import parse_object_id
from backend.app.models.documents import RentalDocument
from backend.app.schemas.rentals import RentalCreate, RentalUpdate


class MongoRentalRepository:
    """MongoDB repository for rental documents."""
    def __init__(self, database: Any):
        """Initialize with MongoDB database instance."""
        self.collection = database.rentals

    async def create(self, data: RentalCreate) -> RentalDocument:
        """Create a new rental with end_date initially set to None (active)."""
        document = data.model_dump(mode="json")
        document["end_date"] = None
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_document(created)

    async def get(self, rental_id: str) -> RentalDocument | None:
        """Retrieve a single rental by ID."""
        object_id = parse_object_id(rental_id)
        if object_id is None:
            return None
        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def list(self, open_only: bool | None = None) -> list[RentalDocument]:
        """List rentals, optionally filtered by status (open_only=True means end_date is None)."""
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
        """Get the open rental that covers today for a specific car."""
        today = date.today().isoformat()
        document = await self.collection.find_one(
            {
                "car_id": car_id,
                "end_date": None,
                "start_date": {"$lte": today},
                "$or": [{"planned_end_date": {"$gte": today}}, {"planned_end_date": None}],
            }
        )
        return self._to_document(document) if document else None

    async def open_for_car(self, car_id: str) -> RentalDocument | None:
        """Get any open current or future rental for a specific car."""
        document = await self.collection.find_one({"car_id": car_id, "end_date": None})
        return self._to_document(document) if document else None

    async def overlapping_for_car(
        self,
        car_id: str,
        start_date: date,
        planned_end_date: date,
        exclude_rental_id: str | None = None,
    ) -> RentalDocument | None:
        """Find an open rental whose planned date range overlaps the requested range."""
        query: dict[str, Any] = {
            "car_id": car_id,
            "end_date": None,
            "start_date": {"$lte": planned_end_date.isoformat()},
        }
        if exclude_rental_id is not None:
            object_id = parse_object_id(exclude_rental_id)
            if object_id is not None:
                query["_id"] = {"$ne": object_id}

        cursor = self.collection.find(query)
        async for document in cursor:
            rental = self._to_document(document)
            existing_end_date = rental.planned_end_date or rental.start_date
            if rental.start_date <= planned_end_date and existing_end_date >= start_date:
                return rental
        return None

    async def end(self, rental_id: str, end_date: date) -> RentalDocument | None:
        """Mark a rental as ended by setting the end_date."""
        object_id = parse_object_id(rental_id)
        if object_id is None:
            return None
        await self.collection.update_one(
            {"_id": object_id},
            {"$set": {"end_date": end_date.isoformat()}},
        )
        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def update(self, rental_id: str, data: RentalUpdate) -> RentalDocument | None:
        """Update editable rental fields for an open rental."""
        object_id = parse_object_id(rental_id)
        if object_id is None:
            return None

        changes = data.model_dump(exclude_unset=True, mode="json")
        if changes:
            await self.collection.update_one({"_id": object_id}, {"$set": changes})

        document = await self.collection.find_one({"_id": object_id})
        return self._to_document(document) if document else None

    async def count_open(self) -> int:
        """Get count of active (open) rentals (used for dashboard metrics)."""
        return int(await self.collection.count_documents({"end_date": None}))

    @staticmethod
    def _to_document(document: dict[str, Any]) -> RentalDocument:
        """Convert a raw MongoDB document into the clean API/domain model."""
        return RentalDocument(
            id=str(document["_id"]),
            car_id=document["car_id"],
            customer_name=document["customer_name"],
            start_date=document["start_date"],
            planned_end_date=document.get("planned_end_date"),
            end_date=document.get("end_date"),
        )
