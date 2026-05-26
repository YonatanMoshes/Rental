"""Prometheus metrics collection and observability.

Tracks operation counts, durations, and fleet statistics.
Metrics are exposed at /metrics endpoint in Prometheus format.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from time import perf_counter
from typing import Any, TypeVar

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

OPERATIONS_TOTAL = Counter(
    "rental_fleet_operations_total",
    "Total number of backend operations.",
    ["operation"],
)

OPERATION_DURATION_SECONDS = Histogram(
    "rental_fleet_operation_duration_seconds",
    "Backend operation duration in seconds.",
    ["operation"],
)

AVAILABLE_CARS = Gauge("rental_fleet_available_cars", "Cars currently available for rent.")
RENTED_CARS = Gauge("rental_fleet_rented_cars", "Cars currently rented.")
OPEN_RENTALS = Gauge("rental_fleet_open_rentals", "Rentals without an end date.")


@dataclass
class OperationTiming:
    """In-memory timing totals used by the dashboard statistics panel."""

    count: int = 0
    total_seconds: float = 0.0
    last_seconds: float = 0.0
    min_seconds: float | None = None
    max_seconds: float | None = None


_operation_timings: dict[str, OperationTiming] = {}
_operation_timings_lock = Lock()


def _record_operation_timing(operation: str, duration_seconds: float) -> None:
    """Store one measured operation duration for the UI statistics endpoint."""
    with _operation_timings_lock:
        timing = _operation_timings.setdefault(operation, OperationTiming())
        timing.count += 1
        timing.total_seconds += duration_seconds
        timing.last_seconds = duration_seconds
        timing.min_seconds = (
            duration_seconds
            if timing.min_seconds is None
            else min(timing.min_seconds, duration_seconds)
        )
        timing.max_seconds = (
            duration_seconds
            if timing.max_seconds is None
            else max(timing.max_seconds, duration_seconds)
        )


def track_operation(operation: str) -> Callable[[F], F]:
    """Decorator to track operation count and duration metrics."""
    def decorator(function: F) -> F:
        """Wrap one async service function with timing and count collection."""

        @wraps(function)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            """Execute the service function and record its elapsed time."""
            start = perf_counter()
            try:
                return await function(*args, **kwargs)
            finally:
                duration_seconds = perf_counter() - start
                OPERATIONS_TOTAL.labels(operation=operation).inc()
                OPERATION_DURATION_SECONDS.labels(operation=operation).observe(
                    duration_seconds
                )
                _record_operation_timing(operation, duration_seconds)

        return wrapped  # type: ignore[return-value]

    return decorator


async def refresh_metrics(car_repository: Any, rental_repository: Any) -> None:
    """Update gauge metrics based on current database state."""
    counts = await car_repository.count_by_status()
    AVAILABLE_CARS.set(counts.get("available", 0))
    RENTED_CARS.set(counts.get("rented", 0))
    OPEN_RENTALS.set(await rental_repository.count_open())


def metrics_response() -> Response:
    """Generate Prometheus-format metrics response."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def operation_statistics_snapshot() -> dict[str, Any]:
    """Return friendly operation timing statistics for the dashboard UI."""
    with _operation_timings_lock:
        operation_rows: list[dict[str, Any]] = []
        total_count = 0
        total_seconds = 0.0

        for operation, timing in sorted(_operation_timings.items()):
            average_seconds = timing.total_seconds / timing.count if timing.count else 0.0
            total_count += timing.count
            total_seconds += timing.total_seconds
            operation_rows.append(
                {
                    "operation": operation,
                    "count": timing.count,
                    "total_seconds": timing.total_seconds,
                    "average_seconds": average_seconds,
                    "average_ms": average_seconds * 1000,
                    "last_ms": timing.last_seconds * 1000,
                    "min_ms": (timing.min_seconds or 0.0) * 1000,
                    "max_ms": (timing.max_seconds or 0.0) * 1000,
                }
            )

    overall_average_seconds = total_seconds / total_count if total_count else 0.0
    return {
        "operations": operation_rows,
        "total_count": total_count,
        "total_seconds": total_seconds,
        "average_seconds": overall_average_seconds,
        "average_ms": overall_average_seconds * 1000,
    }
