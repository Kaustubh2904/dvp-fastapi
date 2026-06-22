from app.core.database.postgres import async_session_maker
from app.services.subscription_service import subscription_service


async def check_subscription_expiries() -> dict:
    """
    Background task to check and handle subscription expiries.
    Returns summary of actions taken.
    """
    async with async_session_maker() as db:
        notified = await subscription_service.check_expiring_companies(db)
        suspended = await subscription_service.suspend_expired_companies(db)

    return {
        "notified_companies": notified,
        "suspended_companies": suspended,
    }