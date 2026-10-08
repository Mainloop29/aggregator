import math
from datetime import date

from app.errors import EventNotFound
from app.usecases.protocols import EventRepositoryProtocol


class ListEventsUsecase:
    def __init__(self, events: EventRepositoryProtocol, hostname: str) -> None:
        self._events = events
        self._hostname = hostname.rstrip("/")

    async def do(
        self,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> dict:
        events, total = await self._events.list(date_from, page, page_size)
        total_pages = max(1, math.ceil(total / page_size))

        params = [f"page_size={page_size}"]
        if date_from:
            params.append(f"date_from={date_from.isoformat()}")
        query = "&".join(params)

        next_url = f"{self._hostname}/api/events?page={page + 1}&{query}" if page < total_pages else None
        prev_url = f"{self._hostname}/api/events?page={page - 1}&{query}" if page > 1 else None

        return {
            "count": total,
            "next": next_url,
            "previous": prev_url,
            "results": events,
        }


class GetEventUsecase:
    def __init__(self, events: EventRepositoryProtocol) -> None:
        self._events = events

    async def do(self, event_id: str):
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)
        return event
