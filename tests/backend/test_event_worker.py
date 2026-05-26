"""Unit tests for the RabbitMQ worker's post-request responsibilities."""

import asyncio

from backend.app.messaging.events import FleetEvent
from backend.app.workers.event_worker import process_fleet_event


class CapturingEventRepository:
    """Stores the event passed by the worker so the test can inspect it."""

    def __init__(self):
        """Start with no saved events."""
        self.saved_events: list[FleetEvent] = []

    async def save(self, event: FleetEvent) -> None:
        """Capture the event that the worker asks to persist."""
        self.saved_events.append(event)


class CountingCarRepository:
    """Provides car status counts and records that metrics were refreshed."""

    def __init__(self):
        """Start with no metrics refresh calls."""
        self.count_calls = 0

    async def count_by_status(self) -> dict[str, int]:
        """Return fake car status counts and record the call."""
        self.count_calls += 1
        return {"available": 2, "rented": 1, "maintenance": 0}


class CountingRentalRepository:
    """Provides open rental counts and records that metrics were refreshed."""

    def __init__(self):
        """Start with no open-rental count calls."""
        self.count_calls = 0

    async def count_open(self) -> int:
        """Return a fake open-rental count and record the call."""
        self.count_calls += 1
        return 1


class CapturingLogger:
    """Records worker log messages without writing to the real log file."""

    def __init__(self):
        """Start with no captured log messages."""
        self.messages: list[tuple[str, tuple[object, ...]]] = []

    def info(self, message: str, *args: object) -> None:
        """Capture an info-level log call for assertions."""
        self.messages.append((message, args))


def test_worker_processes_event_logging_and_metrics():
    """The worker saves audit events, refreshes metrics, and logs the work."""

    async def scenario():
        """Run one worker event through the full post-request pipeline."""
        event = FleetEvent(
            event_type="car.created",
            aggregate_type="car",
            aggregate_id="car-1",
            payload={"model": "Toyota Corolla"},
        )
        event_repository = CapturingEventRepository()
        car_repository = CountingCarRepository()
        rental_repository = CountingRentalRepository()
        logger = CapturingLogger()

        await process_fleet_event(
            event,
            event_repository,
            car_repository,
            rental_repository,
            logger,
        )

        assert event_repository.saved_events == [event]
        assert car_repository.count_calls == 1
        assert rental_repository.count_calls == 1
        assert logger.messages[0][1] == ("car.created", "car", "car-1")

    asyncio.run(scenario())
