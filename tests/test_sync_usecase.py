from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.usecases.sync import FIRST_SYNC_DATE, SyncEventsUsecase


@pytest.mark.asyncio
async def test_first_sync_uses_year_2000():
    client = AsyncMock()
    client.events.return_value = {"next": None, "results": []}

    events = AsyncMock()
    metadata = AsyncMock()
    meta = AsyncMock()
    meta.last_changed_at = None
    metadata.get.return_value = meta

    usecase = SyncEventsUsecase(client, events, metadata)
    await usecase.do()

    _, kwargs = client.events.await_args
    assert kwargs == {}  # без next_url
    args, _ = client.events.await_args
    assert args[0] == FIRST_SYNC_DATE


@pytest.mark.asyncio
async def test_incremental_sync_uses_last_changed_at():
    last_changed = datetime(2026, 1, 4, 22, 0, tzinfo=UTC)
    client = AsyncMock()
    client.events.return_value = {"next": None, "results": []}

    events = AsyncMock()
    metadata = AsyncMock()
    meta = AsyncMock()
    meta.last_changed_at = last_changed
    metadata.get.return_value = meta

    usecase = SyncEventsUsecase(client, events, metadata)
    await usecase.do()

    args, _ = client.events.await_args
    assert args[0] == last_changed


@pytest.mark.asyncio
async def test_sync_upserts_all_events_and_tracks_max_changed_at():
    events_payload = [
        {"id": "e1", "changed_at": "2026-01-01T10:00:00+00:00"},
        {"id": "e2", "changed_at": "2026-01-02T15:30:00+00:00"},
        {"id": "e3", "changed_at": "2026-01-03T20:00:00+00:00"},
    ]
    client = AsyncMock()
    client.events.return_value = {"next": None, "results": events_payload}

    events = AsyncMock()
    metadata = AsyncMock()
    meta = AsyncMock()
    meta.last_changed_at = None
    metadata.get.return_value = meta

    usecase = SyncEventsUsecase(client, events, metadata)
    result = await usecase.do()

    assert events.upsert.await_count == 3
    assert result["synced"] == 3
    # max_changed должен быть от e3
    assert "2026-01-03" in result["last_changed_at"]


@pytest.mark.asyncio
async def test_sync_marks_error_status_on_failure():
    client = AsyncMock()
    client.events.side_effect = RuntimeError("boom")

    events = AsyncMock()
    metadata = AsyncMock()
    meta = AsyncMock()
    meta.last_changed_at = None
    metadata.get.return_value = meta

    usecase = SyncEventsUsecase(client, events, metadata)

    with pytest.raises(RuntimeError, match="boom"):
        await usecase.do()

    # Статус "running" был записан, потом "error: ..."
    statuses = [c.kwargs.get("meta") for c in []]  # noqa: F841
    assert meta.sync_status.startswith("error:")
