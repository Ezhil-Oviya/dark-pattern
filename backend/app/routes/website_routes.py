import logging
from fastapi import APIRouter, HTTPException, status
from pymongo.errors import PyMongoError

from app.models.website import Website
from app.services.website_service import (
    create_website,
    get_all_websites,
    get_website,
    update_website,
    delete_website,
)
from app.config.database import check_mongo_connection, get_mongo_diagnostics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health():
    """
    Health check endpoint reporting backend status, MongoDB connectivity, and diagnostics.
    """
    conn_result = check_mongo_connection()
    is_connected, msg = conn_result
    diagnostics = get_mongo_diagnostics(connection_check=conn_result)

    return {
        "backend": "online",
        "database": "connected" if is_connected else "disconnected",
        "database_details": diagnostics,
        "browser": "ready",
    }



# ---------------- WEBSITE CRUD ---------------- #

@router.post("/websites", status_code=status.HTTP_201_CREATED)
def add_website(website: Website):
    try:
        return create_website(website.dict())
    except PyMongoError as e:
        logger.error(f"Error creating website: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating website: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create website: {str(e)}"
        )


@router.get("/websites")
def read_websites():
    try:
        return get_all_websites()
    except PyMongoError as e:
        logger.error(f"Error fetching websites: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching websites: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch websites: {str(e)}"
        )


@router.get("/websites/{id}")
def read_website(id: str):
    try:
        website = get_website(id)
        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website with id '{id}' not found"
            )
        return website
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Error fetching website '{id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching website '{id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch website: {str(e)}"
        )


@router.put("/websites/{id}")
def edit_website(id: str, website: Website):
    try:
        existing = get_website(id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website with id '{id}' not found"
            )
        return update_website(id, website.dict())
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Error updating website '{id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating website '{id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update website: {str(e)}"
        )


@router.delete("/websites/{id}")
def remove_website(id: str):
    try:
        existing = get_website(id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website with id '{id}' not found"
            )
        return delete_website(id)
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Error deleting website '{id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting website '{id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete website: {str(e)}"
        )