import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import arq
from arq.connections import RedisSettings

from app.core.config.settings import settings
from app.core.database.postgres import async_session_maker
from app.services.subscription_service import subscription_service
from app.services.notification_service import notification_service
from app.services.email_service import email_service
from app.repositories.email_log_repository import email_log_repository
from app.models.email_log import EmailStatus

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


async def run_monthly_reset_job(ctx) -> str:
    logger.info("Starting monthly subscription usage reset...")
    async with async_session_maker() as db:
        reset = await subscription_service.reset_monthly_usage(db)
    result = f"Monthly usage reset complete for {len(reset)} companies"
    logger.info(result)
    return result


async def run_scheduled_changes_job(ctx) -> str:
    logger.info("Applying scheduled subscription changes...")
    async with async_session_maker() as db:
        processed = await subscription_service.process_scheduled_changes(db)
    result = f"Scheduled changes processed for {len(processed)} companies"
    logger.info(result)
    return result


async def send_onboarding_email_job(ctx, email: str, first_name: str, temp_pass: str) -> None:
    await notification_service.send_onboarding_email(email, first_name, temp_pass)


async def send_otp_email_job(ctx, email: str, code: str) -> None:
    await notification_service.send_otp_email(email, code)


async def send_reset_password_email_job(ctx, email: str, token: str) -> None:
    await notification_service.send_reset_password_email(email, token)


async def send_email_job(ctx, email_log_id: int) -> None:
    async with async_session_maker() as db:
        log = await email_log_repository.get(db, email_log_id)
        if not log:
            return
        try:
            log.attempts += 1
            log.status = EmailStatus.RETRYING
            db.add(log)
            await db.commit()
            await email_service.send_email_by_log_id(db, email_log_id)
            log = await email_log_repository.get(db, email_log_id)
            if log:
                log.status = EmailStatus.SENT
                log.sent_at = datetime.now(timezone.utc)
                db.add(log)
                await db.commit()
        except Exception as exc:
            log = await email_log_repository.get(db, email_log_id)
            if log:
                log.status = EmailStatus.FAILED if log.attempts >= settings.EMAIL_QUEUE_RETRY_LIMIT else EmailStatus.RETRYING
                log.last_error = str(exc)
                db.add(log)
                await db.commit()
            logger.exception("Failed to send email log %s", email_log_id)
            raise


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
        run_monthly_reset_job,
        run_scheduled_changes_job,
        send_onboarding_email_job,
        send_otp_email_job,
        send_reset_password_email_job,
        send_email_job,
    ]
    # Run subscription expiry checks every day at midnight UTC
    cron_jobs = [
        arq.cron(run_subscription_checks, hour=0, minute=0),
        arq.cron(run_monthly_reset_job, day=1, hour=0, minute=0),
        arq.cron(run_scheduled_changes_job, hour=0, minute=15),
    ]
