import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from pymongo.errors import PyMongoError
import gridfs

from app.config.database import client, EVIDENCE_DB_NAME

logger = logging.getLogger(__name__)

evidence_db = client[EVIDENCE_DB_NAME]

audits_collection = evidence_db["audits"]
pages_collection = evidence_db["pages"]
evidence_items_collection = evidence_db["evidence_items"]
fs = gridfs.GridFS(evidence_db)


def store_artifact_in_gridfs(
    content: bytes,
    filename: str,
    content_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Uploads a binary artifact (screenshot, DOM HTML, extracted JSON, evidence JSON)
    to GridFS and returns the generated ObjectId as a string.
    """
    try:
        meta = metadata.copy() if metadata else {}
        meta["content_type"] = content_type

        file_id = fs.put(
            content,
            filename=filename,
            metadata=meta
        )
        return str(file_id)
    except PyMongoError as e:
        logger.error(f"Failed to store GridFS artifact '{filename}': {e}")
        raise


def get_gridfs_artifact(file_id_str: str) -> Optional[Tuple[bytes, str, str]]:
    """
    Retrieves a file from GridFS by its ObjectId string.
    Returns (bytes_content, filename, content_type) or None if not found.
    """
    try:
        obj_id = ObjectId(file_id_str)
        if not fs.exists(obj_id):
            return None
        grid_out = fs.get(obj_id)
        content = grid_out.read()
        filename = grid_out.filename or "artifact"
        meta = grid_out.metadata or {}
        content_type = meta.get("content_type")

        if not content_type or content_type == "application/octet-stream":
            if filename.endswith(".png"):
                content_type = "image/png"
            elif filename.endswith(".html"):
                content_type = "text/html"
            elif filename.endswith(".json"):
                content_type = "application/json"
            else:
                content_type = "application/octet-stream"

        return content, filename, content_type
    except Exception as e:
        logger.error(f"Error retrieving GridFS artifact '{file_id_str}': {e}")
        return None


def save_audit_to_mongodb(
    audit_summary: Dict[str, Any],
    pages_data: List[Dict[str, Any]],
    evidence_items_list: List[Dict[str, Any]]
) -> str:
    """
    Persists an entire audit session into the dedicated MongoDB evidence database:
    - 'audits' collection: high-level audit summary and aggregated dark-pattern findings
    - 'pages' collection: per-page records with GridFS artifact references
    - 'evidence_items' collection: granular evidence elements with provenance
    """
    audit_id = audit_summary.get("audit_id")
    if not audit_id:
        raise ValueError("audit_summary must contain 'audit_id'")

    try:
        # Clone items to avoid in-place mutation with ObjectId by PyMongo
        clean_audit_summary = {k: (v if k != "pages" else [{pk: pv for pk, pv in p.items() if pk != "_id"} for p in v]) for k, v in audit_summary.items() if k != "_id"}
        pages_to_insert = [{k: v for k, v in p.items() if k != "_id"} for p in pages_data]
        evidence_to_insert = [{k: v for k, v in ev.items() if k != "_id"} for ev in evidence_items_list]

        # 1. Upsert into audits collection
        audits_collection.update_one(
            {"audit_id": audit_id},
            {"$set": clean_audit_summary},
            upsert=True
        )

        # 2. Insert/replace pages
        pages_collection.delete_many({"audit_id": audit_id})
        if pages_to_insert:
            pages_collection.insert_many(pages_to_insert)

        # 3. Insert/replace evidence items
        evidence_items_collection.delete_many({"audit_id": audit_id})
        if evidence_to_insert:
            evidence_items_collection.insert_many(evidence_to_insert)

        logger.info(
            f"Saved audit '{audit_id}' to MongoDB: {len(pages_to_insert)} pages, "
            f"{len(evidence_to_insert)} evidence items."
        )
        return audit_id
    except PyMongoError as e:
        logger.error(f"Failed to save audit '{audit_id}' to MongoDB: {e}")
        raise


def get_all_audits_from_mongodb() -> List[Dict[str, Any]]:
    """
    Returns all completed audits from MongoDB sorted by start_time descending.
    """
    try:
        cursor = audits_collection.find({}, {"_id": 0}).sort("start_time", -1)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"Failed to get audits from MongoDB: {e}")
        raise


def get_audit_details_from_mongodb(audit_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns full audit details including all crawled pages and detections from MongoDB.
    """
    try:
        audit = audits_collection.find_one({"audit_id": audit_id}, {"_id": 0})
        if not audit:
            return None

        # Load pages from pages collection to ensure freshness
        pages_cursor = pages_collection.find({"audit_id": audit_id}, {"_id": 0}).sort("page_index", 1)
        pages = list(pages_cursor)
        if pages:
            audit["pages"] = pages

        return audit
    except PyMongoError as e:
        logger.error(f"Failed to get audit details for '{audit_id}' from MongoDB: {e}")
        raise


def get_evidence_items_from_mongodb(audit_id: str, page_index: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves granular evidence items for a given audit and optional page index.
    """
    try:
        query: Dict[str, Any] = {"audit_id": audit_id}
        if page_index is not None:
            query["page_index"] = page_index

        cursor = evidence_items_collection.find(query, {"_id": 0}).sort("page_index", 1)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"Failed to get evidence items for audit '{audit_id}' from MongoDB: {e}")
        raise
