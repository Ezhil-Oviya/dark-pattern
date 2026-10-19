import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pymongo.collection import Collection

from app.config.database import db, check_mongo_connection

logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage") / "evaluations"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class EvaluationRepository:
    """
    Manages persistence of algorithm evaluation runs and experiment provenance.
    Uses MongoDB collection 'algorithm_evaluations' as primary store,
    with automatic JSON file storage fallback to guarantee zero data loss.
    """

    def __init__(self):
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._load_local_files()

    def _get_collection(self) -> Optional[Collection]:
        try:
            is_conn, _ = check_mongo_connection(timeout_ms=1000)
            if is_conn and db is not None:
                return db["algorithm_evaluations"]
        except Exception as e:
            logger.debug(f"MongoDB not available for evaluation repository: {e}")
        return None

    def _load_local_files(self) -> None:
        try:
            for p in STORAGE_DIR.glob("eval_*.json"):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    eid = data.get("evaluation_id")
                    if eid:
                        self._memory_cache[eid] = data
        except Exception as e:
            logger.debug(f"Error loading local evaluation files: {e}")

    def save_evaluation(self, eval_data: Dict[str, Any]) -> str:
        eval_id = eval_data.get("evaluation_id")
        if not eval_id:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            eval_id = f"eval_{ts}"
            eval_data["evaluation_id"] = eval_id

        # Always save to memory cache
        self._memory_cache[eval_id] = eval_data

        # Save to local file
        try:
            local_path = STORAGE_DIR / f"{eval_id}.json"
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(eval_data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not persist evaluation to local file: {e}")

        # Attempt to save to MongoDB
        coll = self._get_collection()
        if coll is not None:
            try:
                # Sanitize document for Mongo
                doc = dict(eval_data)
                doc["_id"] = eval_id
                coll.replace_one({"_id": eval_id}, doc, upsert=True)
                logger.info(f"Persisted evaluation {eval_id} to MongoDB Atlas.")
            except Exception as me:
                logger.warning(f"Could not persist evaluation {eval_id} to MongoDB: {me}")

        return eval_id

    def get_evaluation_by_id(self, eval_id: str) -> Optional[Dict[str, Any]]:
        # Check Mongo first
        coll = self._get_collection()
        if coll is not None:
            try:
                doc = coll.find_one({"_id": eval_id})
                if doc:
                    doc.pop("_id", None)
                    return doc
            except Exception as e:
                logger.debug(f"Error fetching evaluation from Mongo: {e}")

        # Check memory cache / local file
        if eval_id in self._memory_cache:
            return self._memory_cache[eval_id]

        local_path = STORAGE_DIR / f"{eval_id}.json"
        if local_path.exists():
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Could not read local evaluation file: {e}")

        return None

    def list_evaluations(self) -> List[Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = dict(self._memory_cache)

        coll = self._get_collection()
        if coll is not None:
            try:
                for doc in coll.find().sort("created_at", -1):
                    doc.pop("_id", None)
                    eid = doc.get("evaluation_id")
                    if eid:
                        results[eid] = doc
            except Exception as e:
                logger.debug(f"Error listing evaluations from Mongo: {e}")

        # Return sorted by timestamp descending
        sorted_list = sorted(
            results.values(),
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        return sorted_list

    def get_latest_evaluation(self) -> Optional[Dict[str, Any]]:
        evals = self.list_evaluations()
        return evals[0] if evals else None


_eval_repo_instance: Optional[EvaluationRepository] = None


def get_evaluation_repository() -> EvaluationRepository:
    global _eval_repo_instance
    if _eval_repo_instance is None:
        _eval_repo_instance = EvaluationRepository()
    return _eval_repo_instance
