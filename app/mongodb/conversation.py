from typing import Optional
from app.core.database.mongodb import get_mongo_db


class ConversationRepository:
    """
    MongoDB operations for conversations.
    """

    @property
    def collection(self):
        return get_mongo_db().conversations

    async def find_by_participants(self, participants: list[int]) -> Optional[dict]:
        participants = sorted([int(p) for p in participants])
        return await self.collection.find_one({"participants": participants})

    async def create(self, conversation_id: str, participants: list[int]) -> dict:
        from datetime import datetime, timezone
        participants = sorted([int(p) for p in participants])
        conv = {
            "conversation_id": conversation_id,
            "participants": participants,
            "created_at": datetime.now(timezone.utc),
        }
        await self.collection.insert_one(conv)
        return conv

    async def find_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find({"participants": int(user_id)}).sort("created_at", -1).skip(skip).limit(limit)
        convs = await cursor.to_list(length=limit)
        for conv in convs:
            if "_id" in conv:
                conv["_id"] = str(conv["_id"])
        return convs


conversation_repo = ConversationRepository()