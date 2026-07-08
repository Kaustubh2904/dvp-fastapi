from datetime import datetime, timezone
import secrets
from typing import Any

from fastapi import HTTPException, status

from app.core.database.mongodb import get_mongo_db
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketReply, TicketReplyCreate, TicketResponse, TicketStatus


class TicketService:
    @property
    def db(self):
        return get_mongo_db()

    def _serialize_ticket(self, ticket: dict[str, Any]) -> TicketResponse:
        return TicketResponse(
            ticket_id=ticket["ticket_id"],
            subject=ticket["subject"],
            description=ticket["description"],
            priority=ticket["priority"],
            status=ticket["status"],
            raised_by_id=ticket["raised_by_id"],
            raised_by_email=ticket["raised_by_email"],
            assigned_to_id=ticket.get("assigned_to_id"),
            replies=[TicketReply(**reply) for reply in ticket.get("replies", [])],
            created_at=ticket["created_at"],
            updated_at=ticket["updated_at"],
        )

    async def create_ticket(self, current_user: User, obj_in: TicketCreate) -> TicketResponse:
        now = datetime.now(timezone.utc)
        ticket = {
            "ticket_id": secrets.token_hex(12),
            "subject": obj_in.subject,
            "description": obj_in.description,
            "priority": obj_in.priority.value,
            "status": TicketStatus.OPEN.value,
            "raised_by_id": current_user.id,
            "raised_by_email": current_user.email,
            "assigned_to_id": None,
            "replies": [],
            "created_at": now,
            "updated_at": now,
        }
        await self.db.tickets.insert_one(ticket)
        return self._serialize_ticket(ticket)

    async def list_tickets(self, current_user: User, skip: int = 0, limit: int = 100) -> list[TicketResponse]:
        query: dict[str, Any] = {}
        if current_user.role not in {UserRole.SUPERADMIN, UserRole.TECHNICAL_TEAM}:
            query["raised_by_id"] = current_user.id

        cursor = self.db.tickets.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        tickets = await cursor.to_list(length=limit)
        return [self._serialize_ticket(ticket) for ticket in tickets]

    async def get_ticket(self, ticket_id: str, current_user: User) -> TicketResponse:
        ticket = await self.db.tickets.find_one({"ticket_id": ticket_id})
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        if current_user.role not in {UserRole.SUPERADMIN, UserRole.TECHNICAL_TEAM} and ticket["raised_by_id"] != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this ticket")

        return self._serialize_ticket(ticket)

    async def reply_to_ticket(self, ticket_id: str, current_user: User, obj_in: TicketReplyCreate) -> TicketResponse:
        ticket = await self.db.tickets.find_one({"ticket_id": ticket_id})
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        if current_user.role not in {UserRole.SUPERADMIN, UserRole.TECHNICAL_TEAM}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to reply to this ticket")

        reply = {
            "responder_id": current_user.id,
            "responder_email": current_user.email,
            "responder_role": current_user.role.value,
            "message": obj_in.message,
            "created_at": datetime.now(timezone.utc),
        }

        new_status = TicketStatus.IN_PROGRESS.value if ticket.get("status") == TicketStatus.OPEN.value else ticket.get("status", TicketStatus.OPEN.value)
        await self.db.tickets.update_one(
            {"ticket_id": ticket_id},
            {
                "$push": {"replies": reply},
                "$set": {
                    "status": new_status,
                    "assigned_to_id": current_user.id,
                    "updated_at": datetime.now(timezone.utc),
                },
            },
        )
        ticket = await self.db.tickets.find_one({"ticket_id": ticket_id})
        return self._serialize_ticket(ticket)


ticket_service = TicketService()