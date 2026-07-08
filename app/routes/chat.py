from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.postgres import get_db
from app.core.dependencies.dependencies import get_current_user, require_employee
from app.models.user import User
from app.services.chat_service import chat_service
from app.services.subscription_service import subscription_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/conversations", dependencies=[require_employee()])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await subscription_service.ensure_feature_available(db, current_user.company_id, "chat")
    return await chat_service.get_user_conversations(current_user.id)


@router.get("/conversations/{conversation_id}/messages", dependencies=[require_employee()])
async def get_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await subscription_service.ensure_feature_available(db, current_user.company_id, "chat")
    conv = await chat_service.db.conversations.find_one({"conversation_id": conversation_id})
    if not conv or current_user.id not in conv["participants"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation.",
        )

    return await chat_service.get_conversation_history(conversation_id, skip=skip, limit=limit)


@router.put("/conversations/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT, dependencies=[require_employee()])
async def mark_read(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await subscription_service.ensure_feature_available(db, current_user.company_id, "chat")
    await chat_service.mark_messages_read(conversation_id, reader_id=current_user.id)
    return None