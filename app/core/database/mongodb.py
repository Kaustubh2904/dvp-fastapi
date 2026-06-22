import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize client lazily or when module is imported
mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
mongo_db = mongo_client[settings.MONGODB_DB]


def get_mongo_db():
    return mongo_db


async def check_mongo_connection() -> bool:
    try:
        # The ismaster command is cheap and does not require auth.
        await mongo_client.admin.command('ismaster')
        return True
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")
        return False
