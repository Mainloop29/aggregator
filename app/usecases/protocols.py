from datetime import date, datetime
from typing import Any, Protocol

from app.db.models import Event


class EventsProviderProtocol(Protocol):
    async def events(
        self,
        changed_at: date | datetime,
        next_url: str | None = None,
    ) -> dict[str, Any]: ...

    async def event(self, event_id: str) -> dict[str, Any]: ...

    async def seats(self, event_id: str) -> list[str]: ...

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str: ...

    async def cancel(self, event_id: str, ticket_id: str) -> None: ...


class EventRepositoryProtocol(Protocol):
    async def get(self, event_id: str) -> Event | None: ...

    async def list(
        self,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Event], int]: ...

    async def upsert(self, data: dict) -> Event: ...


class TicketRepositoryProtocol(Protocol):
    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> None: ...

    async def get_event_id(self, ticket_id: str) -> str | None: ...

    async def delete(self, ticket_id: str) -> str | None: ...


class SyncMetadataRepositoryProtocol(Protocol):
    async def get(self): ...

    async def save(self, meta) -> None: ...


class SeatsCacheProtocol(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...
    def invalidate(self, key: str) -> None: ...
