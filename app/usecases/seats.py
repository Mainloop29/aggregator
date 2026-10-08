from app.errors import EventNotFound, EventNotPublished, ProviderUnavailable
from app.providers.events_provider import EventsProviderError
from app.usecases.protocols import (
    EventRepositoryProtocol,
    EventsProviderProtocol,
    SeatsCacheProtocol,
)

PUBLISHED_STATUS = "published"


class GetSeatsUsecase:
    def __init__(
        self,
        client: EventsProviderProtocol,
        events: EventRepositoryProtocol,
        cache: SeatsCacheProtocol,
    ) -> None:
        self._client = client
        self._events = events
        self._cache = cache

    async def do(self, event_id: str) -> list[str]:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)

        if event.status != PUBLISHED_STATUS:
            raise EventNotPublished(f"event status={event.status}")

        key = f"seats:{event_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        try:
            seats = await self._client.seats(event_id)
        except EventsProviderError as exc:
            raise ProviderUnavailable(str(exc)) from exc

        self._cache.set(key, seats)
        return seats
