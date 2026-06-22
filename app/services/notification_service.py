import logging
import sys
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notification_repository import notification_repository
from app.schemas.notification import NotificationCreate
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def create_in_app_notification(
        db: AsyncSession, user_id: int, title: str, message: str
    ) -> Notification:
        obj_in = NotificationCreate(user_id=user_id, title=title, message=message)
        notification = await notification_repository.create(db, obj_in=obj_in)

        try:
            from app.services.websocket_service import connection_manager
            await connection_manager.send_personal_message(
                message={
                    "event": "in_app_notification",
                    "id": notification.id,
                    "title": title,
                    "message": message,
                    "created_at": notification.created_at.isoformat(),
                },
                user_id=user_id,
            )
        except Exception as e:
            logger.debug(f"Failed to dispatch notification via websocket: {e}")

        return notification

    @staticmethod
    async def send_otp_email(email: str, code: str) -> None:
        message = f"""
        ==================================================
        EMAIL DISPATCH (SIMULATED):
        To: {email}
        Subject: DVP Portal - OTP Verification Code
        Body: Your verification OTP is {code}.
        It will expire in 5 minutes.
        ==================================================
        """
        print(message, file=sys.stderr)

    @staticmethod
    async def send_reset_password_email(email: str, token: str) -> None:
        message = f"""
        ==================================================
        EMAIL DISPATCH (SIMULATED):
        To: {email}
        Subject: DVP Portal - Password Reset Link
        Body: Use the token below to reset your password.
        Token: {token}
        Expires in 15 minutes.
        ==================================================
        """
        print(message, file=sys.stderr)

    @staticmethod
    async def send_onboarding_email(email: str, first_name: str, temp_pass: str) -> None:
        message = f"""
        ==================================================
        EMAIL DISPATCH (SIMULATED):
        To: {email}
        Subject: Welcome to DVP Portal! Onboarding Credentials
        Body: Hello {first_name},
        An account has been set up for you.
        Temporary Password: {temp_pass}
        Please log in and update your profile and credentials.
        ==================================================
        """
        print(message, file=sys.stderr)


notification_service = NotificationService()