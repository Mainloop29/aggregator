import logging
from datetime import UTC, date, datetime

from app.providers.paginator import EventsPaginator
from app.usecases.protocols import (
    EventRepositoryProtocol,
    EventsProviderProtocol,
    SyncMetadataRepositoryProtocol,
)

logger = logging.getLogger(__name__)

FIRST_SYNC_DATE = date(2000, 1, 1)


class SyncEventsUsecase:
    def __init__(
        self,
        client: EventsProviderProtocol,
        events: EventRepositoryProtocol,
        metadata: SyncMetadataRepositoryProtocol,
    ) -> None:
        self._client = client
        self._events = events
        self._metadata = metadata

    async def do(self) -> dict:
        meta = await self._metadata.get()
        meta.sync_status = "running"
        await self._metadata.save(meta)

        changed_at: date | datetime = meta.last_changed_at or FIRST_SYNC_DATE
        logger.info("Sync started: changed_at=%s", changed_at)

        count = 0
        max_changed = meta.last_changed_at

        try:
            async for raw in EventsPaginator(self._client, changed_at):
                await self._events.upsert(raw)
                raw_changed = _parse_dt(raw.get("changed_at"))
                if raw_changed and (max_changed is None or raw_changed > max_changed):
                    max_changed = raw_changed
                count += 1

            meta.last_sync_time = datetime.now(UTC)
            meta.last_changed_at = max_changed or datetime.now(UTC)
            meta.sync_status = "success"
            await self._metadata.save(meta)

            logger.info("Sync completed: %s events", count)
            return {
                "synced": count,
                "last_changed_at": meta.last_changed_at.isoformat(),
            }

        except Exception as exc:  # noqa: BLE001
            logger.exception("Sync failed")
            meta.sync_status = f"error: {str(exc)[:200]}"
            await self._metadata.save(meta)
            raise


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
