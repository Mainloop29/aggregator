import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from app.api.routers import events, health, sync
from app.config import settings
from app.db.engine import engine
from app.db.models import Base
from app.worker import run_sync_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")

    # Создаём таблицы (для dev; в проде — Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    # Планировщик: синхронизация раз в N часов
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_sync_job,
        trigger=IntervalTrigger(hours=settings.sync_interval_hours),
        id="event_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started: interval=%sh", settings.sync_interval_hours)

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await engine.dispose()
        logger.info("Application shutting down")


app = FastAPI(
    title="Events Aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(sync.router, prefix="/api", tags=["sync"])
app.include_router(events.router, prefix="/api", tags=["events"])
