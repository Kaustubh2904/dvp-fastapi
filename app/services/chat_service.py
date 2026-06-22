from datetime import datetime, timezone
import secrets
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database.mongodb import get_mongo_db


class ChatService:
    def __init__(self):
        pass

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return get_mongo_db()

    async def get_or_create_conversation(self, participants: list[int]) -> str:
        participants = sorted([int(p) for p in participants])

        existing = await self.db.conversations.find_one({"participants": participants})
        if existing:
            return existing["conversation_id"]

        conv_id = secrets.token_hex(16)
        new_conv = {
            "conversation_id": conv_id,
            "participants": participants,
            "created_at": datetime.now(timezone.utc),
        }
        await self.db.conversations.insert_one(new_conv)
        return conv_id

    async def save_message(
        self,
        conversation_id: str,
        sender_id: int,
        receiver_id: int,
        content: str,
        attachment_url: Optional[str] = None,
    ) -> dict[str, Any]:
        msg_id = secrets.token_hex(12)
        message = {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "sender_id": int(sender_id),
            "receiver_id": int(receiver_id),
            "content": content,
            "attachment_url": attachment_url,
            "timestamp": datetime.now(timezone.utc),
            "is_read": False,
        }
        await self.db.messages.insert_one(message)
        return message

    async def get_conversation_history(
        self, conversation_id: str, skip: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        cursor = (
            self.db.messages.find({"conversation_id": conversation_id})
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        messages = await cursor.to_list(length=limit)

        messages.reverse()
        for msg in messages:
            if "_id" in msg:
                msg["_id"] = str(msg["_id"])
        return messages

    async def get_user_conversations(self, user_id: int) -> list[dict[str, Any]]:
        cursor = self.db.conversations.find({"participants": int(user_id)}).sort("created_at", -1)
        convs = await cursor.to_list(length=100)
        for conv in convs:
            if "_id" in conv:
                conv["_id"] = str(conv["_id"])
        return convs

    async def mark_messages_read(self, conversation_id: str, reader_id: int) -> None:
        await self.db.messages.update_many(
            {"conversation_id": conversation_id, "receiver_id": int(reader_id), "is_read": False},
            {"$set": {"is_read": True}},
        )

    async def log_websocket_event(self, event_type: str, user_id: int, payload: dict[str, Any]) -> None:
        event = {
            "event_id": secrets.token_hex(12),
            "event_type": event_type,
            "user_id": int(user_id),
            "payload": payload,
            "timestamp": datetime.now(timezone.utc),
        }
        await self.db.websocket_event_logs.insert_one(event)


chat_service = ChatService()