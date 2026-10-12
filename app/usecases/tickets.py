import logging
from datetime import UTC, datetime

from app.enum import EventStatus
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
from app.usecases.protocols import (
    EventRepositoryProtocol,
    EventsProviderProtocol,
    SeatsCacheProtocol,
    TicketRepositoryProtocol,
)
from app.utils.seats import is_valid_seat

logger = logging.getLogger(__name__)


class CreateTicketUsecase:
    def __init__(
        self,
        client: EventsProviderProtocol,
        events: EventRepositoryProtocol,
        tickets: TicketRepositoryProtocol,
        cache: SeatsCacheProtocol,
    ) -> None:
        self._client = client
        self._events = events
        self._tickets = tickets
        self._cache = cache

    async def do(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)

        if event.status != EventStatus.PUBLISHED:
            raise EventNotPublished(f"event status={event.status}")

        now = datetime.now(UTC)
        if event.event_time and event.event_time < now:
            raise EventInPast(f"event_time={event.event_time.isoformat()}")

        if event.registration_deadline and event.registration_deadline < now:
            raise RegistrationClosed(f"registration_deadline={event.registration_deadline.isoformat()}")

        pattern = event.place.seats_pattern if event.place else None
        if not is_valid_seat(pattern, seat):
            raise InvalidSeat(f"seat={seat!r} does not match seats_pattern={pattern!r}")

        cache_key = f"seats:{event.id}"
        available = self._cache.get(cache_key)
        if available is None:
            try:
                available = await self._client.seats(event.id)
            except EventsProviderError as exc:
                raise ProviderUnavailable(str(exc)) from exc
            self._cache.set(cache_key, available)

        if seat.upper() not in available:
            raise SeatNotAvailable(f"seat={seat!r} is already taken")

        try:
            ticket_id = await self._client.register(
                event_id=event.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
        except EventsProviderError as exc:
            if exc.status_code == 400:
                self._cache.invalidate(cache_key)
                raise SeatNotAvailable(str(exc)) from exc
            raise ProviderUnavailable(str(exc)) from exc

        await self._tickets.create(
            ticket_id=ticket_id,
            event_id=event.id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        self._cache.invalidate(cache_key)
        return ticket_id


class CancelTicketUsecase:
    def __init__(
        self,
        client: EventsProviderProtocol,
        events: EventRepositoryProtocol,
        tickets: TicketRepositoryProtocol,
        cache: SeatsCacheProtocol,
    ) -> None:
        self._client = client
        self._events = events
        self._tickets = tickets
        self._cache = cache

    async def do(self, ticket_id: str) -> bool:
        event_id = await self._tickets.get_event_id(ticket_id)
        if event_id is None:
            raise TicketNotFound(ticket_id)

        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)

        now = datetime.now(UTC)
        if event.event_time and event.event_time < now:
            raise EventInPast(f"event_time={event.event_time.isoformat()}")

        try:
            await self._client.cancel(event_id=event_id, ticket_id=ticket_id)
        except EventsProviderError as exc:
            raise ProviderUnavailable(str(exc)) from exc

        await self._tickets.delete(ticket_id)
        self._cache.invalidate(f"seats:{event_id}")
        return True
