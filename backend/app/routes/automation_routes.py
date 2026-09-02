import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Response, status
from pymongo.errors import PyMongoError

from app.services.automation.playwright_service import run_browser_audit
from app.services.evidence.mongodb_evidence_service import (
    get_all_audits_from_mongodb,
    get_audit_details_from_mongodb,
    get_gridfs_artifact,
)
from app.services.website_service import get_website

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/automation/start/{website_id}")
def start_automation(website_id: str):
    """
    Triggers an automated multi-page crawl audit for the configured website
    and saves all audit metadata, pages, evidence items, and GridFS artifacts to MongoDB.
    """
    try:
        website = get_website(website_id)
    except PyMongoError as e:
        logger.error(f"Database error checking website '{website_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    try:
        result = run_browser_audit(website)
        return result
    except Exception as e:
        logger.error(f"Error during browser automation audit: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit execution failed: {str(e)}"
        )


@router.get("/automation/audits")
def list_audits() -> List[Dict[str, Any]]:
    """
    Returns a list of all completed audit sessions loaded dynamically from MongoDB.
    Used for the Dashboard Audits count and the Evidence Collection audit selector.
    """
    try:
        audits = get_all_audits_from_mongodb()
        return audits
    except PyMongoError as e:
        logger.error(f"Database error retrieving audits from MongoDB: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving audits from MongoDB: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list audits from MongoDB: {str(e)}"
        )


@router.get("/automation/audit/{audit_id}")
def get_audit_details(audit_id: str) -> Dict[str, Any]:
    """
    Returns full audit details including all crawled pages, GridFS artifact references,
    and aggregated dark pattern findings for a specific audit ID from MongoDB.
    """
    try:
        audit = get_audit_details_from_mongodb(audit_id)
        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit with ID '{audit_id}' not found in MongoDB"
            )
        return audit
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Database error retrieving audit '{audit_id}' from MongoDB: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving audit '{audit_id}' from MongoDB: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit from MongoDB: {str(e)}"
        )


@router.get("/automation/artifact/{file_id}")
def get_artifact(file_id: str):
    """
    Streams an individual artifact (screenshot, DOM HTML, extracted JSON, evidence JSON)
    directly from MongoDB GridFS with the appropriate HTTP Content-Type header.
    """
    try:
        artifact_tuple = get_gridfs_artifact(file_id)
    except PyMongoError as e:
        logger.error(f"Database error retrieving GridFS artifact '{file_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )

    if not artifact_tuple:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID '{file_id}' not found in GridFS storage"
        )

    content_bytes, filename, content_type = artifact_tuple
    return Response(
        content=content_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )