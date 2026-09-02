import logging
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from app.config.database import website_collection
from app.schemas.website_schema import website_serializer, websites_serializer

logger = logging.getLogger(__name__)


def _make_id_query(id_str: str):
    """
    Constructs an ID query supporting both BSON ObjectId and string matching.
    """
    try:
        return {"_id": ObjectId(id_str)}
    except (InvalidId, TypeError):
        return {"_id": id_str}


def create_website(data: dict):
    """
    Inserts a new website configuration into MongoDB and returns the serialized document.
    """
    try:
        clean_data = {k: v for k, v in data.items() if k != "_id"}
        result = website_collection.insert_one(clean_data)
        doc = website_collection.find_one({"_id": result.inserted_id})
        return website_serializer(doc)
    except PyMongoError as e:
        logger.error(f"Failed to create website in MongoDB: {e}")
        raise


def get_all_websites():
    """
    Retrieves all configured websites from MongoDB.
    """
    try:
        cursor = website_collection.find()
        return websites_serializer(cursor)
    except PyMongoError as e:
        logger.error(f"Failed to retrieve websites from MongoDB: {e}")
        raise


def get_website(id: str):
    """
    Retrieves a single website configuration by ID.
    """
    try:
        query = _make_id_query(id)
        doc = website_collection.find_one(query)
        if not doc:
            # Fallback check for string id field
            doc = website_collection.find_one({"id": id})
        return website_serializer(doc) if doc else None
    except PyMongoError as e:
        logger.error(f"Failed to retrieve website '{id}' from MongoDB: {e}")
        raise


def delete_website(id: str):
    """
    Deletes a website configuration by ID.
    """
    try:
        query = _make_id_query(id)
        result = website_collection.delete_one(query)
        if result.deleted_count == 0:
            # Fallback for string id field
            website_collection.delete_one({"id": id})
        return {"message": "Deleted Successfully"}
    except PyMongoError as e:
        logger.error(f"Failed to delete website '{id}' from MongoDB: {e}")
        raise


def update_website(id: str, data: dict):
    """
    Updates an existing website configuration by ID.
    """
    try:
        query = _make_id_query(id)
        clean_data = {k: v for k, v in data.items() if k not in ("_id", "id")}
        website_collection.update_one(query, {"$set": clean_data})
        doc = website_collection.find_one(query)
        return website_serializer(doc)
    except PyMongoError as e:
        logger.error(f"Failed to update website '{id}' in MongoDB: {e}")
        raise