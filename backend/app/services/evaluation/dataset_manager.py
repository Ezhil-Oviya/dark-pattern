import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sklearn.model_selection import StratifiedKFold, train_test_split

logger = logging.getLogger(__name__)

DATASET_CANDIDATES = [
    Path(__file__).resolve().parents[5] / "ai" / "datasets" / "dark_patterns_multi_category_benchmark.json",
    Path("..") / "ai" / "datasets" / "dark_patterns_multi_category_benchmark.json",
    Path("ai") / "datasets" / "dark_patterns_multi_category_benchmark.json",
    Path("c:/1.Fumar plans/Final year project/Dark Pattern/dark-pattern/ai/datasets/dark_patterns_multi_category_benchmark.json"),
    Path(__file__).resolve().parents[5] / "ai" / "datasets" / "dark_patterns_benchmark.json",
]


class BenchmarkDatasetManager:
    """
    Manages verified ground-truth benchmark datasets for dark pattern algorithms.
    Guarantees train/test leakage prevention, deterministic splitting, and dataset provenance.
    """

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path or self._resolve_dataset_path()
        self._raw_data: Dict[str, Any] = {}
        self._samples: List[Dict[str, Any]] = []
        self._dataset_hash: str = ""
        self._load_dataset()

    def _resolve_dataset_path(self) -> Path:
        for p in DATASET_CANDIDATES:
            if p.exists():
                return p
        return DATASET_CANDIDATES[0]

    def _load_dataset(self) -> None:
        if self.dataset_path and self.dataset_path.exists():
            try:
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self._dataset_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    self._raw_data = json.loads(content)
                    self._samples = self._raw_data.get("samples", [])
                    logger.info(
                        f"Loaded benchmark dataset from {self.dataset_path} "
                        f"({len(self._samples)} samples, SHA256: {self._dataset_hash[:12]}...)"
                    )
                    return
            except Exception as e:
                logger.error(f"Failed to read dataset from {self.dataset_path}: {e}")

        logger.warning("Benchmark dataset file not found. Initializing empty dataset manager.")
        self._raw_data = {"metadata": {"version": "0.0.0", "description": "Empty"}, "samples": []}
        self._samples = []
        self._dataset_hash = ""

    @property
    def dataset_hash(self) -> str:
        return self._dataset_hash

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._raw_data.get("metadata", {})

    @property
    def all_samples(self) -> List[Dict[str, Any]]:
        return list(self._samples)

    def get_decisive_samples(self) -> List[Dict[str, Any]]:
        """
        Returns samples with definitive ground-truth labels (DARK_PATTERN or BENIGN),
        excluding ambiguous / INSUFFICIENT_EVIDENCE cases for standard evaluation.
        """
        return [
            s for s in self._samples
            if s.get("label") in ("DARK_PATTERN", "BENIGN", "FORCED_ACTION", "BASKET_SNEAKING")
        ]

    def get_insufficient_evidence_samples(self) -> List[Dict[str, Any]]:
        """
        Returns samples specifically annotated as ambiguous or INSUFFICIENT_EVIDENCE
        for testing abstention policies.
        """
        return [
            s for s in self._samples
            if s.get("label") in ("INSUFFICIENT_EVIDENCE", "INSUFFICIENT_CONTEXT")
        ]

    def get_train_test_split(
        self,
        test_size: float = 0.30,
        random_state: int = 42
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Splits decisive samples into deterministic Stratified Train and Held-Out Test partitions.
        Stratification is performed on composite key (category + binary label) to ensure
        balanced representation across all 8 dark-pattern categories.
        """
        decisive = self.get_decisive_samples()
        if not decisive:
            logger.warning("No decisive samples available for train/test split.")
            return [], []

        strat_keys = []
        for s in decisive:
            cat = s.get("category") or s.get("pattern", "Unknown")
            is_pos = 1 if s.get("label") in ("DARK_PATTERN", "FORCED_ACTION", "BASKET_SNEAKING") else 0
            strat_keys.append(f"{cat}_{is_pos}")

        try:
            train_samples, test_samples = train_test_split(
                decisive,
                test_size=test_size,
                random_state=random_state,
                stratify=strat_keys
            )
        except ValueError as ve:
            logger.warning(f"Stratified split failed (sparse classes: {ve}). Falling back to unstratified split.")
            train_samples, test_samples = train_test_split(
                decisive,
                test_size=test_size,
                random_state=random_state
            )

        logger.info(
            f"Dataset Split (test_size={test_size}, seed={random_state}): "
            f"Train={len(train_samples)}, Test={len(test_samples)}"
        )
        return train_samples, test_samples

    def get_k_fold_splits(
        self,
        n_splits: int = 5,
        random_state: int = 42
    ) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
        """
        Generates K-Fold Stratified train/test splits for cross-validation stability analysis.
        """
        decisive = self.get_decisive_samples()
        if len(decisive) < n_splits * 2:
            return []

        strat_keys = []
        for s in decisive:
            is_pos = 1 if s.get("label") in ("DARK_PATTERN", "FORCED_ACTION", "BASKET_SNEAKING") else 0
            strat_keys.append(is_pos)

        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        folds = []
        for train_idx, test_idx in skf.split(decisive, strat_keys):
            folds.append(([decisive[i] for i in train_idx], [decisive[i] for i in test_idx]))
        return folds


_dataset_manager_instance: Optional[BenchmarkDatasetManager] = None


def get_dataset_manager() -> BenchmarkDatasetManager:
    global _dataset_manager_instance
    if _dataset_manager_instance is None:
        _dataset_manager_instance = BenchmarkDatasetManager()
    return _dataset_manager_instance
