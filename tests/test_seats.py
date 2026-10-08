from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.errors import EventNotFound, EventNotPublished, ProviderUnavailable
from app.providers.events_provider import EventsProviderError
from app.usecases.seats import GetSeatsUsecase
from app.utils.seats import InvalidSeatsPattern, is_valid_seat, parse_seats_pattern


class _Cache:
    def __init__(self):
        self._d: dict = {}

    def get(self, key):
        return self._d.get(key)

    def set(self, key, value):
        self._d[key] = value

    def invalidate(self, key):
        self._d.pop(key, None)


def _event(status: str = "published"):
    return SimpleNamespace(id="e1", status=status, place=None)


def test_parse_single_section():
    assert parse_seats_pattern("A1-3") == {"A1", "A2", "A3"}


def test_parse_multiple_sections():
    assert parse_seats_pattern("A1-2,B1-2") == {"A1", "A2", "B1", "B2"}


def test_parse_empty_returns_empty_set():
    assert parse_seats_pattern(None) == set()
    assert parse_seats_pattern("") == set()


def test_parse_invalid_raises():
    with pytest.raises(InvalidSeatsPattern):
        parse_seats_pattern("nonsense")
    with pytest.raises(InvalidSeatsPattern):
        parse_seats_pattern("A5-1")


def test_is_valid_seat():
    assert is_valid_seat("A1-100,B1-200", "A15") is True
    assert is_valid_seat("A1-100,B1-200", "a15") is True
    assert is_valid_seat("A1-100,B1-200", "C1") is False
    assert is_valid_seat(None, "A1") is False


@pytest.mark.asyncio
async def test_get_seats_raises_when_event_not_found():
    events = AsyncMock()
    events.get.return_value = None
    usecase = GetSeatsUsecase(AsyncMock(), events, _Cache())

    with pytest.raises(EventNotFound):
        await usecase.do("e1")


@pytest.mark.asyncio
async def test_get_seats_raises_when_event_not_published():
    events = AsyncMock()
    events.get.return_value = _event(status="new")
    client = AsyncMock()
    usecase = GetSeatsUsecase(client, events, _Cache())

    with pytest.raises(EventNotPublished):
        await usecase.do("e1")

    client.seats.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_seats_returns_provider_list_and_caches_it():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.seats.return_value = ["A1", "A3"]
    cache = _Cache()
    usecase = GetSeatsUsecase(client, events, cache)

    seats = await usecase.do("e1")
    assert seats == ["A1", "A3"]

    seats_again = await usecase.do("e1")
    assert seats_again == ["A1", "A3"]
    assert client.seats.await_count == 1


@pytest.mark.asyncio
async def test_get_seats_wraps_provider_error():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.seats.side_effect = EventsProviderError("boom")
    usecase = GetSeatsUsecase(client, events, _Cache())

    with pytest.raises(ProviderUnavailable):
        await usecase.do("e1")


@pytest.mark.asyncio
async def test_get_seats_no_status_check_for_published():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.seats.return_value = []
    usecase = GetSeatsUsecase(client, events, _Cache())

    await usecase.do("e1")
    client.seats.assert_awaited_once_with("e1")
