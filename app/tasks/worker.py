import asyncio
import logging
from urllib.parse import urlparse

import arq
from arq.connections import RedisSettings

from app.core.config.settings import settings
from app.core.database.postgres import async_session_maker
from app.services.subscription_service import subscription_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------

async def run_subscription_checks(ctx) -> str:
    """
    Background job: check subscription expiries and suspend elapsed accounts.
    Scheduled daily at midnight via ARQ cron.
    """
    logger.info("Starting background subscription validation checks...")
    async with async_session_maker() as db:
        notified = await subscription_service.check_expiring_companies(db)
        suspended = await subscription_service.suspend_expired_companies(db)
    result = f"Subscription checks complete. Notified: {len(notified)}, Suspended: {len(suspended)}"
    logger.info(result)
    return result


async def send_onboarding_email_job(ctx, email: str, first_name: str, temp_pass: str) -> None:
    await notification_service.send_onboarding_email(email, first_name, temp_pass)


async def send_otp_email_job(ctx, email: str, code: str) -> None:
    await notification_service.send_otp_email(email, code)


async def send_reset_password_email_job(ctx, email: str, token: str) -> None:
    await notification_service.send_reset_password_email(email, token)


# ---------------------------------------------------------------------------
# Worker lifecycle hooks
# ---------------------------------------------------------------------------

async def startup(ctx):
    logger.info("ARQ Worker starting up...")


async def shutdown(ctx):
    logger.info("ARQ Worker shutting down...")


# ---------------------------------------------------------------------------
# Worker settings
# ---------------------------------------------------------------------------

url = urlparse(settings.REDIS_URL)


class WorkerSettings:
    redis_settings = RedisSettings(
        host=url.hostname or "localhost",
        port=url.port or 6379,
        database=int((url.path or "/0").strip("/")),
    )
    on_startup = startup
    on_shutdown = shutdown
    functions = [
        run_subscription_checks,
        send_onboarding_email_job,
        send_otp_email_job,
        send_reset_password_email_job,
    ]
    # Run subscription expiry checks every day at midnight UTC
    cron_jobs = [
        arq.cron(run_subscription_checks, hour=0, minute=0),
    ]
