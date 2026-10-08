from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class SyncTriggerResponse(BaseModel):
    status: str


class PlaceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    city: str | None = None
    address: str | None = None


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    place: PlaceSchema | None = None
    event_time: datetime
    registration_deadline: datetime | None = None
    status: str
    number_of_visitors: int


class PaginatedEvents(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[EventListItem]


class SeatsResponse(BaseModel):
    event_id: str
    available_seats: list[str]


class TicketCreate(BaseModel):
    """Запрос POST /api/tickets."""

    event_id: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    seat: str = Field(min_length=1, max_length=50)


class TicketResponse(BaseModel):
    """Ответ POST /api/tickets (201)."""

    ticket_id: str


class TicketCancelResponse(BaseModel):
    """Ответ DELETE /api/tickets/{id}."""

    success: bool
