#!/usr/bin/env python3
"""
Intelligent Automated Compliance Auditing Framework
AI-Assisted Dark Pattern Detectors Evaluation Script (Final Review)

Evaluates:
1. Pretrained Transformer Semantic Similarity Layer (sentence-transformers/all-MiniLM-L6-v2)
2. End-to-End Hybrid Detector Layer (Semantic Layer + Deterministic DOM/Context Validation)
on the project-specific curated benchmark dataset.

Outputs:
- Number of test cases
- Actual vs Predicted labels
- Accuracy, Precision, Recall, F1-Score
- Confusion Matrix (TP, FP, TN, FN)
- Explicit statistical limitations and methodology notes
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Reconfigure stdout to UTF-8 for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend modules are on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.dark_patterns.ai_classifier import get_ai_classifier
from app.services.dark_patterns.basket_sneaking_detector import BasketSneakingDetector
from app.services.dark_patterns.forced_action_detector import ForcedActionDetector


def load_dataset() -> Dict[str, Any]:
    dataset_path = PROJECT_ROOT / "ai" / "datasets" / "dark_patterns_benchmark.json"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    """Computes binary classification metrics and confusion matrix."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    total = len(y_true)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total_samples": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    }


def evaluate_forced_action(dataset: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    classifier = get_ai_classifier()
    detector = ForcedActionDetector()

    # 1. AI Model Semantic Classification Layer
    y_true_ai = []
    y_pred_ai = []

    # 2. End-to-End Hybrid Detector Layer
    y_true_e2e = []
    y_pred_e2e = []

    print("\n" + "=" * 86)
    print("EVALUATION 1: FORCED ACTION DETECTION (Pretrained Transformer + DOM Validation)")
    print("=" * 86)
    print(f"{'ID':<12} | {'True Label':<20} | {'AI Score':<10} | {'AI Pred':<10} | {'E2E Status':<14} | {'E2E Pred':<10}")
    print("-" * 86)

    for item in dataset:
        text = item["text"]
        is_positive = 1 if item["label"] == "FORCED_ACTION" else 0
        context = {
            "has_alternative": item.get("has_alternative", False),
            "guest_option_present": item.get("has_alternative", False),
        }

        # 1. Semantic Model Prediction
        ai_score, ai_meta = classifier.classify_forced_action(text, context)
        ai_pred = 1 if ai_score >= 0.70 else 0

        y_true_ai.append(is_positive)
        y_pred_ai.append(ai_pred)

        # 2. End-to-End Hybrid Detector (Simulate DOM environment)
        mock_extracted = {
            "url": "https://example.com/test",
            "forms": [],
            "checkboxes": [],
            "modals": [],
            "buttons": [],
            "links": []
        }

        if item.get("context") == "modal_overlay" or "modal" in item.get("context", ""):
            mock_extracted["modals"].append({"text": text, "selector": "#gating-modal"})
        elif item.get("context") == "required_checkbox":
            mock_extracted["checkboxes"].append({"label": text, "required": True, "selector": "#req-cb"})
        else:
            mock_extracted["buttons"].append({"text": text, "selector": "#btn-action"})

        if item.get("has_alternative"):
            mock_extracted["buttons"].append({"text": "Continue as guest", "selector": "#btn-guest"})

        e2e_finding = detector.detect(mock_extracted, {})
        e2e_pred = 1 if e2e_finding.detected else 0

        y_true_e2e.append(is_positive)
        y_pred_e2e.append(e2e_pred)

        print(
            f"{item['id']:<12} | {item['label']:<20} | {ai_score:<10.2f} | "
            f"{'POSITIVE' if ai_pred else 'NEGATIVE':<10} | {e2e_finding.status:<14} | "
            f"{'POSITIVE' if e2e_pred else 'NEGATIVE':<10}"
        )

    ai_metrics = compute_metrics(y_true_ai, y_pred_ai)
    e2e_metrics = compute_metrics(y_true_e2e, y_pred_e2e)
    return ai_metrics, e2e_metrics


def evaluate_basket_sneaking(dataset: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    classifier = get_ai_classifier()
    detector = BasketSneakingDetector()

    y_true_ai = []
    y_pred_ai = []

    y_true_e2e = []
    y_pred_e2e = []

    print("\n" + "=" * 86)
    print("EVALUATION 2: BASKET SNEAKING DETECTION (Pretrained Transformer + DOM Validation)")
    print("=" * 86)
    print(f"{'ID':<12} | {'True Label':<20} | {'AI Score':<10} | {'AI Pred':<10} | {'E2E Status':<14} | {'E2E Pred':<10}")
    print("-" * 86)

    for item in dataset:
        text = item["text"]
        is_positive = 1 if item["label"] == "BASKET_SNEAKING" else 0
        context = {
            "has_price": item.get("has_price", False),
            "is_checked": item.get("is_checked"),
        }

        # 1. Semantic Model Prediction
        ai_score, ai_meta = classifier.classify_basket_sneaking(text, context)
        ai_pred = 1 if ai_score >= 0.70 else 0

        y_true_ai.append(is_positive)
        y_pred_ai.append(ai_pred)

        # 2. End-to-End Hybrid Detector (Simulate DOM environment)
        mock_extracted = {
            "url": "https://example.com/checkout",
            "forms": [],
            "checkboxes": [],
            "cart_items": [{"name": "Main Product", "price": "₹1,000"}],
        }

        if item.get("context") == "cart_item":
            mock_extracted["cart_items"].append({
                "name": text,
                "is_addon": True,
                "is_checked": item.get("is_checked", True),
                "selector": "#cart-addon"
            })
        elif item.get("context") in ("checkbox", "toggle"):
            mock_extracted["checkboxes"].append({
                "label": text,
                "checked": item.get("is_checked"),
                "default_checked": item.get("is_checked"),
                "selector": "#chk-addon"
            })
        else:
            mock_extracted["checkboxes"].append({
                "label": text,
                "checked": item.get("is_checked"),
                "selector": "#chk-gen"
            })

        e2e_finding = detector.detect(mock_extracted, {})
        e2e_pred = 1 if e2e_finding.detected else 0

        y_true_e2e.append(is_positive)
        y_pred_e2e.append(e2e_pred)

        print(
            f"{item['id']:<12} | {item['label']:<20} | {ai_score:<10.2f} | "
            f"{'POSITIVE' if ai_pred else 'NEGATIVE':<10} | {e2e_finding.status:<14} | "
            f"{'POSITIVE' if e2e_pred else 'NEGATIVE':<10}"
        )

    ai_metrics = compute_metrics(y_true_ai, y_pred_ai)
    e2e_metrics = compute_metrics(y_true_e2e, y_pred_e2e)
    return ai_metrics, e2e_metrics


def print_summary_table(title: str, ai_m: Dict[str, Any], e2e_m: Dict[str, Any]):
    print("\n" + "=" * 86)
    print(f"METRIC SUMMARY: {title.upper()}")
    print("=" * 86)
    print(f"{'Metric':<28} | {'Semantic Model Layer':<24} | {'End-to-End Detector':<24}")
    print("-" * 86)
    print(f"{'Total Evaluation Samples':<28} | {ai_m['total_samples']:<24} | {e2e_m['total_samples']:<24}")
    print(f"{'True Positives (TP)':<28} | {ai_m['tp']:<24} | {e2e_m['tp']:<24}")
    print(f"{'False Positives (FP)':<28} | {ai_m['fp']:<24} | {e2e_m['fp']:<24}")
    print(f"{'True Negatives (TN)':<28} | {ai_m['tn']:<24} | {e2e_m['tn']:<24}")
    print(f"{'False Negatives (FN)':<28} | {ai_m['fn']:<24} | {e2e_m['fn']:<24}")
    print(f"{'Accuracy':<28} | {ai_m['accuracy'] * 100:<23.1f}% | {e2e_m['accuracy'] * 100:<23.1f}%")
    print(f"{'Precision':<28} | {ai_m['precision'] * 100:<23.1f}% | {e2e_m['precision'] * 100:<23.1f}%")
    print(f"{'Recall':<28} | {ai_m['recall'] * 100:<23.1f}% | {e2e_m['recall'] * 100:<23.1f}%")
    print(f"{'F1-Score':<28} | {ai_m['f1_score'] * 100:<23.1f}% | {e2e_m['f1_score'] * 100:<23.1f}%")
    print("=" * 86)


def main():
    print("==============================================================================")
    print("Intelligent Automated Compliance Auditing Framework")
    print("Research Evaluation: AI-Assisted Dark Pattern Detection (Review III / Final)")
    print("Model: sentence-transformers/all-MiniLM-L6-v2 (Pretrained Sentence Transformer)")
    print("==============================================================================")

    data = load_dataset()
    meta = data.get("metadata", {})
    print(f"Dataset Version   : {meta.get('version')}")
    print(f"Semester Review   : {meta.get('semester_review')}")
    print(f"Pretrained Model  : {meta.get('nlp_model')}")
    print(f"Total Samples     : {len(data.get('forced_action_dataset', [])) + len(data.get('basket_sneaking_dataset', []))} (20 Forced Action, 18 Basket Sneaking)")

    fa_ai_m, fa_e2e_m = evaluate_forced_action(data.get("forced_action_dataset", []))
    bs_ai_m, bs_e2e_m = evaluate_basket_sneaking(data.get("basket_sneaking_dataset", []))

    print_summary_table("Forced Action Detection", fa_ai_m, fa_e2e_m)
    print_summary_table("Basket Sneaking Detection", bs_ai_m, bs_e2e_m)

    print("\n" + "=" * 86)
    print("EXPLICIT EVALUATION METHODOLOGY & STATISTICAL LIMITATIONS:")
    print("=" * 86)
    print("1. Model Attribution: The dense sentence embedding model (all-MiniLM-L6-v2) is")
    print("   pretrained. The project does not claim to train the base language model.")
    print("2. Score Interpretation: model_score represents dense semantic cosine similarity")
    print("   and contrast margin relative to prototype concepts; it is NOT a population-calibrated")
    print("   statistical probability.")
    print("3. Evaluation Limitation: The evaluation dataset is project-specific and relatively")
    print("   small (38 samples: 20 Forced Action, 18 Basket Sneaking); results demonstrate functional")
    print("   validation on curated compliance test scenarios rather than broad statistical generalization.")
    print("=" * 86)


if __name__ == "__main__":
    main()
