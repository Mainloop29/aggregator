from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_event_usecase, get_list_events_usecase
from app.api.schemas import EventListItem, PaginatedEvents
from app.errors import EventNotFound
from app.usecases.events import GetEventUsecase, ListEventsUsecase

router = APIRouter()


@router.get("/events", response_model=PaginatedEvents, summary="Список событий")
async def list_events(
    usecase: Annotated[ListEventsUsecase, Depends(get_list_events_usecase)],
    date_from: date | None = Query(
        default=None,
        description="Фильтр: события после даты (YYYY-MM-DD)",
    ),
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(default=20, ge=1, le=100, description="Размер страницы"),
) -> PaginatedEvents:
    data = await usecase.do(date_from=date_from, page=page, page_size=page_size)
    return PaginatedEvents(
        count=data["count"],
        next=data["next"],
        previous=data["previous"],
        results=[EventListItem.model_validate(e) for e in data["results"]],
    )


@router.get("/events/{event_id}", response_model=EventListItem, summary="Детали события")
async def get_event(
    event_id: str,
    usecase: Annotated[GetEventUsecase, Depends(get_event_usecase)],
) -> EventListItem:
    try:
        event = await usecase.do(event_id)
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    return EventListItem.model_validate(event)
