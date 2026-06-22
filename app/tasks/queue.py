import logging
import sys
from typing import Callable, Optional
from fastapi import BackgroundTasks
from app.core.database.redis import is_redis_available, redis_client
from app.core.config.settings import settings

logger = logging.getLogger(__name__)

# arq queue client pool
arq_pool = None


async def get_arq_pool():
    global arq_pool
    if not is_redis_available:
        return None
    if arq_pool is None:
        try:
            from arq import create_pool
            from arq.connections import RedisSettings
            # Construct arq redis settings from URL
            # redis://localhost:6379/0 -> host='localhost', port=6379
            from urllib.parse import urlparse
            url = urlparse(settings.REDIS_URL)
            arq_pool = await create_pool(
                RedisSettings(
                    host=url.hostname or "localhost",
                    port=url.port or 6379,
                    database=int((url.path or "/0").strip("/")),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to create arq task pool: {e}")
            arq_pool = None
    return arq_pool


async def enqueue_task(
    background_tasks: BackgroundTasks,
    task_func: Callable,
    *args,
    **kwargs
) -> None:
    """
    Enqueues a background task. 
    If Redis is running, delegates to the arq Redis-backed queue.
    If Redis is down, falls back to FastAPI's in-process BackgroundTasks.
    """
    pool = await get_arq_pool()
    if pool and is_redis_available:
        try:
            # Enqueue task name matching function name
            job_name = task_func.__name__
            await pool.enqueue_job(job_name, *args, **kwargs)
            logger.info(f"Enqueued arq worker task: '{job_name}'")
            return
        except Exception as e:
            logger.error(f"Failed to queue task in arq: {e}. Falling back to inline execution.")
            
    # Fallback to local process background tasks
    print(f"INFO:  Redis offline. Executing task '{task_func.__name__}' inline via FastAPI BackgroundTasks.", file=sys.stderr)
    background_tasks.add_task(task_func, *args, **kwargs)
