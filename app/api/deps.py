from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import get_session
from app.repositories.sqlalchemy import SqlEventRepository
from app.usecases.events import GetEventUsecase, ListEventsUsecase

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_event_repo(session: SessionDep) -> SqlEventRepository:
    return SqlEventRepository(session)


def get_list_events_usecase(
    repo: Annotated[SqlEventRepository, Depends(get_event_repo)],
) -> ListEventsUsecase:
    return ListEventsUsecase(events=repo, hostname=settings.hostname)


def get_event_usecase(
    repo: Annotated[SqlEventRepository, Depends(get_event_repo)],
) -> GetEventUsecase:
    return GetEventUsecase(events=repo)
