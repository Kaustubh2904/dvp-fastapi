import json
import logging
from typing import Any, Optional, Tuple
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database.postgres import async_session_maker
from app.core.security.security import decode_token
from app.models.user import User, UserRole
from app.services.chat_service import chat_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}
        self.connection_details: dict[int, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, role: UserRole, company_id: Optional[int]) -> None:
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.connection_details[user_id] = {
            "role": role,
            "company_id": company_id,
        }
        await chat_service.log_websocket_event(
            event_type="CONNECT",
            user_id=user_id,
            payload={"status": "connected", "role": role.value, "company_id": company_id},
        )

        await self.broadcast_presence(user_id, online=True)

    async def disconnect(self, user_id: int) -> None:
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.connection_details:
            del self.connection_details[user_id]

        await chat_service.log_websocket_event(
            event_type="DISCONNECT",
            user_id=user_id,
            payload={"status": "disconnected"},
        )

        await self.broadcast_presence(user_id, online=False)

    async def send_personal_message(self, message: dict[str, Any], user_id: int) -> None:
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(json.dumps(message))

    async def broadcast_presence(self, user_id: int, online: bool) -> None:
        presence_msg = {
            "event": "presence",
            "user_id": user_id,
            "status": "online" if online else "offline",
        }
        for active_id in self.active_connections:
            if active_id != user_id:
                try:
                    await self.send_personal_message(presence_msg, active_id)
                except Exception:
                    pass

    async def verify_permissions(self, db_session: Any, sender_id: int, receiver_id: int) -> bool:
        sender_query = select(User).where(User.id == sender_id)
        sender_res = await db_session.execute(sender_query)
        sender = sender_res.scalar_one_or_none()

        receiver_query = select(User).where(User.id == receiver_id)
        receiver_res = await db_session.execute(receiver_query)
        receiver = receiver_res.scalar_one_or_none()

        if not sender or not receiver:
            return False

        role_s, company_s = sender.role, sender.company_id
        role_r, company_r = receiver.role, receiver.company_id

        if (role_s == UserRole.EMPLOYEE and role_r == UserRole.SUPERADMIN) or (
            role_s == UserRole.SUPERADMIN and role_r == UserRole.EMPLOYEE
        ):
            return False

        if (role_s == UserRole.ADMIN and role_r == UserRole.EMPLOYEE) or (
            role_s == UserRole.EMPLOYEE and role_r == UserRole.ADMIN
        ):
            if company_s != company_r:
                return False

        if role_s == UserRole.ADMIN and role_r == UserRole.ADMIN:
            if company_s != company_r:
                return False

        return True


connection_manager = ConnectionManager()