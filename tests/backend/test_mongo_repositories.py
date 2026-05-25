import asyncio

from backend.app.repositories.cars import MongoCarRepository


class AsyncListCursor:
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeCarsCollection:
    def __init__(self):
        self.aggregate_was_awaited = False

    async def aggregate(self, pipeline):
        self.aggregate_was_awaited = True
        return AsyncListCursor(
            [
                {"_id": "available", "count": 2},
                {"_id": "maintenance", "count": 1},
            ]
        )


class FakeDatabase:
    def __init__(self):
        self.cars = FakeCarsCollection()


def test_count_by_status_awaits_async_mongo_aggregate():
    async def scenario():
        database = FakeDatabase()
        repository = MongoCarRepository(database)

        counts = await repository.count_by_status()

        assert database.cars.aggregate_was_awaited is True
        assert counts["available"] == 2
        assert counts["maintenance"] == 1
        assert counts["rented"] == 0

    asyncio.run(scenario())
