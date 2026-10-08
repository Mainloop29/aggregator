from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.errors import EventNotFound
from app.usecases.events import GetEventUsecase, ListEventsUsecase


def _event(event_id: str = "e1") -> SimpleNamespace:
    return SimpleNamespace(
        id=event_id,
        name="Test Event",
        place=None,
        event_time=datetime(2026, 1, 1, tzinfo=UTC),
        registration_deadline=None,
        status="published",
        number_of_visitors=0,
    )


@pytest.mark.asyncio
async def test_list_events_builds_next_url_on_first_page():
    repo = AsyncMock()
    repo.list.return_value = ([_event("e1")], 50)

    usecase = ListEventsUsecase(events=repo, hostname="http://localhost:8000")
    result = await usecase.do(date_from=None, page=1, page_size=20)

    assert result["count"] == 50
    assert result["previous"] is None
    assert result["next"] == "http://localhost:8000/api/events?page=2&page_size=20"
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_list_events_builds_prev_url_on_last_page():
    repo = AsyncMock()
    repo.list.return_value = ([_event("e1")], 50)

    usecase = ListEventsUsecase(events=repo, hostname="http://localhost:8000")
    result = await usecase.do(date_from=None, page=3, page_size=20)

    assert result["next"] is None
    assert result["previous"] == "http://localhost:8000/api/events?page=2&page_size=20"


@pytest.mark.asyncio
async def test_list_events_includes_date_from_in_nav_urls():
    repo = AsyncMock()
    repo.list.return_value = ([], 100)

    usecase = ListEventsUsecase(events=repo, hostname="http://localhost:8000")
    result = await usecase.do(date_from=date(2026, 1, 1), page=1, page_size=20)

    assert "date_from=2026-01-01" in result["next"]
    assert "page=2" in result["next"]


@pytest.mark.asyncio
async def test_get_event_raises_when_not_found():
    repo = AsyncMock()
    repo.get.return_value = None

    usecase = GetEventUsecase(events=repo)

    with pytest.raises(EventNotFound):
        await usecase.do("e-missing")


@pytest.mark.asyncio
async def test_get_event_returns_event():
    repo = AsyncMock()
    event = _event("e1")
    repo.get.return_value = event

    usecase = GetEventUsecase(events=repo)
    result = await usecase.do("e1")

    assert result is event
