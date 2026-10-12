from datetime import UTC, date, datetime, time

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, Place, SyncMetadata, Ticket, utcnow
from app.enum import EventStatus


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


class SqlEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: str) -> Event | None:
        result = await self._session.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Event], int]:
        stmt = select(Event)
        count_stmt = select(func.count(Event.id))

        if date_from:
            dt = datetime.combine(date_from, time.min, tzinfo=UTC)
            stmt = stmt.where(Event.event_time >= dt)
            count_stmt = count_stmt.where(Event.event_time >= dt)

        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Event.event_time.asc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return rows, total

    async def upsert(self, data: dict) -> Event:
        place = await self._upsert_place(data.get("place") or {})
        await self._session.flush()

        result = await self._session.execute(select(Event).where(Event.id == data["id"]))
        event = result.scalar_one_or_none()
        if event is None:
            event = Event(id=data["id"], name=data.get("name", ""), changed_at=utcnow())
            self._session.add(event)

        event.name = data.get("name", event.name)
        event.place_id = place.id if place else event.place_id
        event.event_time = _parse_dt(data.get("event_time")) or event.event_time
        event.registration_deadline = _parse_dt(data.get("registration_deadline"))
        event.status = data.get("status", event.status or EventStatus.NEW.value)
        event.number_of_visitors = int(data.get("number_of_visitors") or event.number_of_visitors or 0)
        event.changed_at = _parse_dt(data.get("changed_at")) or utcnow()
        event.created_at = _parse_dt(data.get("created_at"))
        event.status_changed_at = _parse_dt(data.get("status_changed_at"))
        event.updated_at = utcnow()
        return event

    async def _upsert_place(self, data: dict) -> Place | None:
        place_id = data.get("id")
        if not place_id:
            return None
        result = await self._session.execute(select(Place).where(Place.id == place_id))
        place = result.scalar_one_or_none()
        if place is None:
            place = Place(id=place_id, name=data.get("name", ""))
            self._session.add(place)
        place.name = data.get("name", place.name or "")
        place.city = data.get("city", place.city)
        place.address = data.get("address", place.address)
        if data.get("seats_pattern"):
            place.seats_pattern = data["seats_pattern"]
        place.changed_at = _parse_dt(data.get("changed_at")) or place.changed_at
        place.created_at = _parse_dt(data.get("created_at")) or place.created_at
        return place


class SqlTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> None:
        self._session.add(
            Ticket(
                id=ticket_id,
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
        )
        await self._session.commit()

    async def get_event_id(self, ticket_id: str) -> str | None:
        result = await self._session.execute(select(Ticket.event_id).where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()

    async def delete(self, ticket_id: str) -> str | None:
        result = await self._session.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket is None:
            return None
        event_id = ticket.event_id
        await self._session.execute(sa_delete(Ticket).where(Ticket.id == ticket_id))
        await self._session.commit()
        return event_id


class SqlSyncMetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SyncMetadata:
        result = await self._session.execute(select(SyncMetadata).where(SyncMetadata.id == 1))
        meta = result.scalar_one_or_none()
        if meta is None:
            meta = SyncMetadata(id=1)
            self._session.add(meta)
            await self._session.commit()
            await self._session.refresh(meta)
        return meta

    async def save(self, meta: SyncMetadata) -> None:
        await self._session.commit()
