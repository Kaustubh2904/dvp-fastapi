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


async def run_monthly_usage_reset() -> dict:
    async with async_session_maker() as db:
        reset = await subscription_service.reset_monthly_usage(db)
    return {"reset_companies": reset}


async def run_scheduled_subscription_changes() -> dict:
    async with async_session_maker() as db:
        processed = await subscription_service.process_scheduled_changes(db)
    return {"processed_companies": processed}