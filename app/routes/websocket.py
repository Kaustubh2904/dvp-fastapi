import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy import select

from app.core.database.postgres import async_session_maker
from app.core.security.security import decode_token
from app.models.user import User
from app.services.websocket_service import connection_manager
from app.services.chat_service import chat_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = decode_token(token)
    user_id_str = payload.get("sub")
    token_type = payload.get("type")

    if not user_id_str or token_type != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = int(user_id_str)

    async with async_session_maker() as db:
        query = select(User).where(User.id == user_id)
        res = await db.execute(query)
        user = res.scalar_one_or_none()

        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        role = user.role
        company_id = user.company_id

    await connection_manager.connect(websocket, user_id=user_id, role=role, company_id=company_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
                receiver_id = int(msg_data.get("receiver_id"))
                content = str(msg_data.get("content")).strip()
                attachment_url = msg_data.get("attachment_url")
            except Exception:
                await connection_manager.send_personal_message(
                    {"event": "error", "message": "Invalid message format"}, user_id
                )
                continue

            if not content:
                continue

            async with async_session_maker() as db_session:
                is_allowed = await connection_manager.verify_permissions(
                    db_session, sender_id=user_id, receiver_id=receiver_id
                )

            if not is_allowed:
                await connection_manager.send_personal_message(
                    {"event": "error", "message": "Communication policy restricts this conversation."},
                    user_id,
                )
                continue

            conv_id = await chat_service.get_or_create_conversation([user_id, receiver_id])
            message = await chat_service.save_message(
                conversation_id=conv_id,
                sender_id=user_id,
                receiver_id=receiver_id,
                content=content,
                attachment_url=attachment_url,
            )

            payload = {
                "event": "message",
                "message_id": message["message_id"],
                "conversation_id": conv_id,
                "sender_id": user_id,
                "receiver_id": receiver_id,
                "content": content,
                "attachment_url": attachment_url,
                "timestamp": message["timestamp"].isoformat(),
                "is_read": False,
            }

            if receiver_id in connection_manager.active_connections:
                await connection_manager.send_personal_message(payload, receiver_id)
            else:
                async with async_session_maker() as db_session:
                    await notification_service.create_in_app_notification(
                        db=db_session,
                        user_id=receiver_id,
                        title="New Chat Message",
                        message=f"You received a message: '{content[:50]}...'",
                    )

            await connection_manager.send_personal_message(payload, user_id)

    except WebSocketDisconnect:
        await connection_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(user_id)