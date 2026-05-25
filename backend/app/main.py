import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.app.api.routes import cars, rentals, system
from backend.app.core.config import get_settings
from backend.app.core.errors import BusinessRuleError, NotFoundError
from backend.app.core.logging import configure_logging
from backend.app.db.indexes import ensure_database_indexes
from backend.app.db.mongodb import close_mongodb_connection, connect_to_mongodb, get_database

settings = get_settings()
configure_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)


def create_app(connect_database: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        if connect_database:
            await connect_to_mongodb(settings)
            await ensure_database_indexes(get_database())
            logger.info("Connected to MongoDB database=%s", settings.mongodb_database)
        yield
        if connect_database:
            await close_mongodb_connection()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(system.router)
    app.include_router(cars.router)
    app.include_router(rentals.router)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BusinessRuleError)
    async def business_rule_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
