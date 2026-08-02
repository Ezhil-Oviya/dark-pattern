from fastapi import APIRouter

from app.models.website import Website
from app.services.website_service import *
from app.config.database import client


router = APIRouter()


@router.get("/health")
def health():

    try:

        client.admin.command("ping")

        database_status = "connected"

    except Exception:

        database_status = "disconnected"

    return {
        "backend": "online",
        "database": database_status,
        "browser": "ready"
    }

# ---------------- WEBSITE CRUD ---------------- #

@router.post("/websites")
def add_website(website: Website):

    return create_website(
        website.dict()
    )


@router.get("/websites")
def read_websites():

    return get_all_websites()


@router.get("/websites/{id}")
def read_website(id: str):

    return get_website(id)


@router.put("/websites/{id}")
def edit_website(
    id: str,
    website: Website
):

    return update_website(
        id,
        website.dict()
    )


@router.delete("/websites/{id}")
def remove_website(id: str):

    return delete_website(id)