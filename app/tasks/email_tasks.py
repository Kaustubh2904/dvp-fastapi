from app.services.notification_service import notification_service


async def send_welcome_email(email: str, first_name: str) -> None:
    """Send welcome email to new users."""
    subject = "Welcome to DVP Portal"
    body = f"Hello {first_name},\n\nWelcome to the Digital Verification Portal!"
    await notification_service.send_onboarding_email(email, first_name, "")


async def send_generic_email(to: str, subject: str, body: str) -> None:
    """Send a generic email notification."""
    from app.services.email_service import email_service
    await email_service.send_email(to=to, subject=subject, body=body)