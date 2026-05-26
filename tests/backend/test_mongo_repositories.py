"""Repository unit tests for MongoDB adapters.

The tests use small fake MongoDB collections so repository behavior can be
checked without starting a real MongoDB server.
"""

import asyncio

from backend.app.repositories.cars import MongoCarRepository


class AsyncListCursor:
    """Async iterator that behaves like a small MongoDB cursor."""

    def __init__(self, items):
        """Wrap plain Python items so async-for can read them."""
        self._items = iter(items)

    def __aiter__(self):
        """Return this cursor as its own async iterator."""
        return self

    async def __anext__(self):
        """Return the next fake Mongo row or stop the iteration."""
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeCarsCollection:
    """Fake MongoDB cars collection that records aggregate usage."""

    def __init__(self):
        """Start with aggregation marked as not yet awaited."""
        self.aggregate_was_awaited = False

    async def aggregate(self, pipeline):
        """Return fake aggregation rows and prove the repository awaited us."""
        self.aggregate_was_awaited = True
        return AsyncListCursor(
            [
                {"_id": "available", "count": 2},
                {"_id": "maintenance", "count": 1},
            ]
        )


class FakeDatabase:
    """Fake database object with only the collection needed by this test."""

    def __init__(self):
        """Expose the fake cars collection under the expected attribute name."""
        self.cars = FakeCarsCollection()


def test_count_by_status_awaits_async_mongo_aggregate():
    """The repository should await Mongo aggregation before reading counts."""
    async def scenario():
        """Run the repository method and assert it consumed the fake cursor."""
        database = FakeDatabase()
        repository = MongoCarRepository(database)

        counts = await repository.count_by_status()

        assert database.cars.aggregate_was_awaited is True
        assert counts["available"] == 2
        assert counts["maintenance"] == 1
        assert counts["rented"] == 0

    asyncio.run(scenario())
