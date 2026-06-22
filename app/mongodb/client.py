from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config.settings import settings

# Re-export the MongoDB client and db from core
from app.core.database.mongodb import mongo_client, mongo_db, get_mongo_db, check_mongo_connection

__all__ = ["mongo_client", "mongo_db", "get_mongo_db", "check_mongo_connection"]