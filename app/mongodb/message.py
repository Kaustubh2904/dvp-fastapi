from typing import Optional
from app.core.database.mongodb import get_mongo_db


class MessageRepository:
    """
    MongoDB operations for messages.
    """

    @property
    def collection(self):
        return get_mongo_db().messages

    async def create(self, message: dict) -> dict:
        await self.collection.insert_one(message)
        return message

    async def find_by_conversation(self, conversation_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        cursor = (
            self.collection.find({"conversation_id": conversation_id})
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

    async def mark_read(self, conversation_id: str, reader_id: int) -> None:
        await self.collection.update_many(
            {"conversation_id": conversation_id, "receiver_id": int(reader_id), "is_read": False},
            {"$set": {"is_read": True}},
        )


message_repo = MessageRepository()