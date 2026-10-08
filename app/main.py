import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import health
from app.db.engine import engine
from app.db.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")

    # Создаём таблицы, если их нет (для dev; в проде — Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    yield

    # Закрываем пул соединений при остановке
    await engine.dispose()
    logger.info("Application shutting down")


app = FastAPI(
    title="Events Aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api", tags=["health"])
