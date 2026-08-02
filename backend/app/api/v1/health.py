from fastapi import APIRouter
from pymongo.errors import PyMongoError

from app.db.mongodb import database

router = APIRouter()


@router.get("/health")
async def health():

    backend = "online"

    try:

        await database.command("ping")

        database_status = "connected"

    except PyMongoError:

        database_status = "disconnected"

    return {
        "backend": backend,
        "database": database_status,
        "browser": "ready"
    }