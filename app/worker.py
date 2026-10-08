import logging

from app.db.engine import SessionLocal
from app.providers.events_provider import EventsProviderClient
from app.repositories.sqlalchemy import (
    SqlEventRepository,
    SqlSyncMetadataRepository,
)
from app.usecases.sync import SyncEventsUsecase

logger = logging.getLogger(__name__)


async def run_sync_job() -> None:

    async with SessionLocal() as session:
        usecase = SyncEventsUsecase(
            client=EventsProviderClient(),
            events=SqlEventRepository(session),
            metadata=SqlSyncMetadataRepository(session),
        )
        try:
            result = await usecase.do()
            logger.info("Sync job done: %s", result)
        except Exception:  # noqa: BLE001
            logger.exception("Sync job failed")
