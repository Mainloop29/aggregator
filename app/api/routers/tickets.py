from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_cancel_ticket_usecase, get_create_ticket_usecase
from app.api.schemas import TicketCancelResponse, TicketCreate, TicketResponse
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
from app.usecases.tickets import CancelTicketUsecase, CreateTicketUsecase

router = APIRouter()


@router.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=201,
    summary="Зарегистрироваться на событие",
)
async def create_ticket(
    payload: TicketCreate,
    usecase: Annotated[CreateTicketUsecase, Depends(get_create_ticket_usecase)],
) -> TicketResponse:
    try:
        ticket_id = await usecase.do(
            event_id=payload.event_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            seat=payload.seat,
        )
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        EventNotPublished,
        EventInPast,
        RegistrationClosed,
        SeatNotAvailable,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidSeat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TicketResponse(ticket_id=ticket_id)


@router.delete(
    "/tickets/{ticket_id}",
    response_model=TicketCancelResponse,
    summary="Отменить регистрацию",
)
async def cancel_ticket(
    ticket_id: str,
    usecase: Annotated[CancelTicketUsecase, Depends(get_cancel_ticket_usecase)],
) -> TicketCancelResponse:
    try:
        await usecase.do(ticket_id)
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Ticket not found") from exc
    except EventNotFound as exc:
        raise HTTPException(status_code=404, detail="Event not found") from exc
    except EventInPast as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TicketCancelResponse(success=True)
