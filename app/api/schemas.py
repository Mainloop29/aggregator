from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
