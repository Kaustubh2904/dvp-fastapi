from app.services.notification_service import notification_service


async def send_bulk_notification(user_ids: list[int], title: str, message: str) -> None:
    """Send in-app notification to multiple users."""
    from app.core.database.postgres import async_session_maker

    async with async_session_maker() as db:
        for user_id in user_ids:
            await notification_service.create_in_app_notification(
                db=db, user_id=user_id, title=title, message=message
            )