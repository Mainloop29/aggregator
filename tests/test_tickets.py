from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.errors import (
    EventInPast,
    EventNotFound,
    EventNotPublished,
    InvalidSeat,
    ProviderUnavailable,
    RegistrationClosed,
    SeatNotAvailable,
    TicketNotFound,
)
from app.providers.events_provider import EventsProviderError
from app.usecases.tickets import CancelTicketUsecase, CreateTicketUsecase


class _Cache:
    def __init__(self):
        self._d: dict = {}

    def get(self, key):
        return self._d.get(key)

    def set(self, key, value):
        self._d[key] = value

    def invalidate(self, key):
        self._d.pop(key, None)


def _event(
    *,
    status: str = "published",
    seats_pattern: str = "A1-10",
    event_time: datetime | None = None,
    registration_deadline: datetime | None = None,
):
    now = datetime.now(UTC)
    place = SimpleNamespace(seats_pattern=seats_pattern)
    return SimpleNamespace(
        id="e1",
        status=status,
        place=place,
        event_time=event_time or (now + timedelta(days=1)),
        registration_deadline=registration_deadline or (now + timedelta(hours=1)),
    )


@pytest.mark.asyncio
async def test_create_ticket_raises_when_event_not_found():
    events = AsyncMock()
    events.get.return_value = None
    usecase = CreateTicketUsecase(AsyncMock(), events, AsyncMock(), _Cache())

    with pytest.raises(EventNotFound):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")


@pytest.mark.asyncio
async def test_create_ticket_raises_when_not_published():
    events = AsyncMock()
    events.get.return_value = _event(status="new")
    usecase = CreateTicketUsecase(AsyncMock(), events, AsyncMock(), _Cache())

    with pytest.raises(EventNotPublished):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")


@pytest.mark.asyncio
async def test_create_ticket_raises_when_event_in_past():
    events = AsyncMock()
    events.get.return_value = _event(
        event_time=datetime.now(UTC) - timedelta(days=1),
    )
    usecase = CreateTicketUsecase(AsyncMock(), events, AsyncMock(), _Cache())

    with pytest.raises(EventInPast):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")


@pytest.mark.asyncio
async def test_create_ticket_raises_when_registration_closed():
    events = AsyncMock()
    events.get.return_value = _event(
        registration_deadline=datetime.now(UTC) - timedelta(hours=1),
    )
    usecase = CreateTicketUsecase(AsyncMock(), events, AsyncMock(), _Cache())

    with pytest.raises(RegistrationClosed):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")


@pytest.mark.asyncio
async def test_create_ticket_raises_when_seat_invalid_format():
    events = AsyncMock()
    events.get.return_value = _event(seats_pattern="A1-10")
    usecase = CreateTicketUsecase(AsyncMock(), events, AsyncMock(), _Cache())

    with pytest.raises(InvalidSeat):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "Z99")


@pytest.mark.asyncio
async def test_create_ticket_raises_when_seat_taken():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.seats.return_value = ["A2", "A3"]  # A1 занято
    usecase = CreateTicketUsecase(client, events, AsyncMock(), _Cache())

    with pytest.raises(SeatNotAvailable):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")


@pytest.mark.asyncio
async def test_create_ticket_happy_path():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.seats.return_value = ["A1", "A2"]
    client.register.return_value = "t-1"
    tickets = AsyncMock()
    cache = _Cache()
    usecase = CreateTicketUsecase(client, events, tickets, cache)

    ticket_id = await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")

    assert ticket_id == "t-1"
    client.register.assert_awaited_once_with(
        event_id="e1",
        first_name="Ivan",
        last_name="Ivanov",
        email="i@x.com",
        seat="A1",
    )
    tickets.create.assert_awaited_once()
    assert cache.get("seats:e1") is None  # инвалидировали


@pytest.mark.asyncio
async def test_create_ticket_maps_provider_400_to_seat_not_available():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.seats.return_value = ["A1"]
    client.register.side_effect = EventsProviderError("seat sold", status_code=400, payload=["already sold"])
    tickets = AsyncMock()
    cache = _Cache()
    usecase = CreateTicketUsecase(client, events, tickets, cache)

    with pytest.raises(SeatNotAvailable):
        await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")

    tickets.create.assert_not_awaited()
    assert cache.get("seats:e1") is None


@pytest.mark.asyncio
async def test_create_ticket_uses_cache_for_seats():
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.register.return_value = "t-1"
    tickets = AsyncMock()
    cache = _Cache()
    cache.set("seats:e1", ["A1", "A2"])
    usecase = CreateTicketUsecase(client, events, tickets, cache)

    await usecase.do("e1", "Ivan", "Ivanov", "i@x.com", "A1")

    client.seats.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_ticket_raises_when_ticket_unknown():
    tickets = AsyncMock()
    tickets.get_event_id.return_value = None
    usecase = CancelTicketUsecase(AsyncMock(), AsyncMock(), tickets, _Cache())

    with pytest.raises(TicketNotFound):
        await usecase.do("t-1")


@pytest.mark.asyncio
async def test_cancel_ticket_raises_when_event_in_past():
    tickets = AsyncMock()
    tickets.get_event_id.return_value = "e1"
    events = AsyncMock()
    events.get.return_value = _event(
        event_time=datetime.now(UTC) - timedelta(days=1),
    )
    usecase = CancelTicketUsecase(AsyncMock(), events, tickets, _Cache())

    with pytest.raises(EventInPast):
        await usecase.do("t-1")


@pytest.mark.asyncio
async def test_cancel_ticket_happy_path():
    tickets = AsyncMock()
    tickets.get_event_id.return_value = "e1"
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    cache = _Cache()
    usecase = CancelTicketUsecase(client, events, tickets, cache)

    result = await usecase.do("t-1")

    assert result is True
    client.cancel.assert_awaited_once_with(event_id="e1", ticket_id="t-1")
    tickets.delete.assert_awaited_once_with("t-1")


@pytest.mark.asyncio
async def test_cancel_ticket_wraps_provider_error():
    tickets = AsyncMock()
    tickets.get_event_id.return_value = "e1"
    events = AsyncMock()
    events.get.return_value = _event()
    client = AsyncMock()
    client.cancel.side_effect = EventsProviderError("boom")
    usecase = CancelTicketUsecase(client, events, tickets, _Cache())

    with pytest.raises(ProviderUnavailable):
        await usecase.do("t-1")
