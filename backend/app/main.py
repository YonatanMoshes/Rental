"""FastAPI application factory and lifecycle management.

Handles app initialization, database connection, route registration, and error handling.
The lifespan context manager ensures MongoDB connection is established on startup
and properly closed on shutdown.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.app.api.routes import cars, events, rentals, system
from backend.app.core.config import get_settings
from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.core.logging import configure_logging
from backend.app.db.indexes import ensure_database_indexes
from backend.app.db.mongodb import close_mongodb_connection, connect_to_mongodb, get_database
from backend.app.messaging.publisher import RabbitMQEventPublisher

settings = get_settings()
configure_logging(settings.log_level, settings.log_file, settings.log_timezone)
logger = logging.getLogger(__name__)


def create_app(connect_database: bool = True) -> FastAPI:
    """Create and configure FastAPI application.
    
    Args:
        connect_database: If True, connects to MongoDB on startup.
                         Set to False for testing without a database.
    
    Returns:
        Configured FastAPI instance with all routes and error handlers.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage app startup and shutdown events."""
        publisher: RabbitMQEventPublisher | None = None
        if connect_database:
            await connect_to_mongodb(settings)
            await ensure_database_indexes(get_database())
            publisher = RabbitMQEventPublisher(settings)
            await publisher.connect()
            app.state.event_publisher = publisher
            logger.info("Connected to MongoDB database=%s", settings.mongodb_database)
        try:
            yield
        finally:
            if publisher is not None:
                await publisher.close()
            if connect_database:
                await close_mongodb_connection()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(system.router)
    app.include_router(cars.router)
    app.include_router(rentals.router)
    app.include_router(events.router)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        """Handle 404 errors for missing resources."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BusinessRuleError)
    async def business_rule_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
        """Handle business logic violations (e.g., cannot delete car with active rental)."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
