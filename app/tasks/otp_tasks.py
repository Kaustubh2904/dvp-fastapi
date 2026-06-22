from app.services.notification_service import notification_service


async def send_otp_notification(email: str, code: str) -> None:
    """Send OTP code to user's email."""
    await notification_service.send_otp_email(email=email, code=code)