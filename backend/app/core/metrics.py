from collections.abc import Awaitable, Callable
from functools import wraps
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


def track_operation(operation: str) -> Callable[[F], F]:
    def decorator(function: F) -> F:
        @wraps(function)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            start = perf_counter()
            try:
                return await function(*args, **kwargs)
            finally:
                OPERATIONS_TOTAL.labels(operation=operation).inc()
                OPERATION_DURATION_SECONDS.labels(operation=operation).observe(
                    perf_counter() - start
                )

        return wrapped  # type: ignore[return-value]

    return decorator


async def refresh_metrics(car_repository: Any, rental_repository: Any) -> None:
    counts = await car_repository.count_by_status()
    AVAILABLE_CARS.set(counts.get("available", 0))
    RENTED_CARS.set(counts.get("rented", 0))
    OPEN_RENTALS.set(await rental_repository.count_open())


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
