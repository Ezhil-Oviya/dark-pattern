import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Fallback in-memory dataset if filesystem path cannot be resolved
BENCHMARK_PATH = Path("..") / "ai" / "datasets" / "dark_patterns_benchmark.json"
LOCAL_BENCHMARK_PATH = Path("c:/dark-pattern/ai/datasets/dark_patterns_benchmark.json")


def load_benchmark_dataset() -> Dict[str, Any]:
    """
    Loads the curated benchmark dataset for Forced Action and Basket Sneaking.
    """
    candidates = [
        LOCAL_BENCHMARK_PATH,
        BENCHMARK_PATH,
        Path(__file__).resolve().parents[4] / "ai" / "datasets" / "dark_patterns_benchmark.json",
    ]

    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load benchmark dataset from {p}: {e}")

    logger.warning("Using built-in fallback benchmark dataset records.")
    return {
        "metadata": {"version": "1.0", "description": "Fallback dataset"},
        "forced_action_dataset": [],
        "basket_sneaking_dataset": []
    }
