from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies.dependencies import get_current_user, require_admin, require_ticket_portal_access
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketReplyCreate, TicketResponse
from app.services.ticket_service import ticket_service


router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED, dependencies=[require_admin()])
async def create_ticket(
    obj_in: TicketCreate,
    current_user: User = Depends(get_current_user),
):
    return await ticket_service.create_ticket(current_user, obj_in)


@router.get("", response_model=list[TicketResponse], dependencies=[require_ticket_portal_access()])
async def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    current_user: User = Depends(get_current_user),
):
    return await ticket_service.list_tickets(current_user, skip=skip, limit=limit)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
):
    return await ticket_service.get_ticket(ticket_id, current_user)


@router.post("/{ticket_id}/reply", response_model=TicketResponse, dependencies=[require_ticket_portal_access()])
async def reply_to_ticket(
    ticket_id: str,
    obj_in: TicketReplyCreate,
    current_user: User = Depends(get_current_user),
):
    return await ticket_service.reply_to_ticket(ticket_id, current_user, obj_in)