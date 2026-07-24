from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config.settings import settings

mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
database = mongodb_client[settings.mongodb_database]
