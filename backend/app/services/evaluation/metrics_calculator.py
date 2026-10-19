import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)

ALL_EIGHT_CATEGORIES = [
    "False Urgency",
    "Drip Pricing",
    "Bait and Switch",
    "Confirmshaming",
    "SaaS Billing",
    "Interface Interference",
    "Forced Action",
    "Basket Sneaking",
]


class EvaluationMetricsCalculator:
    """
    Standardized, authoritative metrics calculator based on scikit-learn.
    Handles binary classification, multi-category decomposition, macro/weighted averaging,
    and abstention / insufficient-evidence coverage tracking.
    """

    @staticmethod
    def calculate_binary_metrics(
        y_true: List[int],
        y_pred: List[int],
        y_score: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculates standard classification metrics for binary dark-pattern detection.
        Positive class (1) represents a Dark Pattern.
        Negative class (0) represents Benign / Clean UI element.
        """
        total = len(y_true)
        if total == 0:
            return {
                "accuracy": None,
                "precision": None,
                "recall": None,
                "f1_score": None,
                "specificity": None,
                "false_positive_rate": None,
                "predicted_detection_rate": None,
                "support": 0,
                "positive_ground_truth": 0,
                "negative_ground_truth": 0,
                "confusion_matrix": {
                    "true_positive": 0,
                    "false_positive": 0,
                    "true_negative": 0,
                    "false_negative": 0,
                },
                "status": "No samples evaluated"
            }

        # Convert to numpy arrays
        y_t = np.array(y_true)
        y_p = np.array(y_pred)

        # Scikit-learn confusion matrix [[TN, FP], [FN, TP]]
        cm = confusion_matrix(y_t, y_p, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        pos_count = int(np.sum(y_t == 1))
        neg_count = int(np.sum(y_t == 0))
        pred_pos_count = int(np.sum(y_p == 1))

        # Precision, Recall, F1
        prec = float(precision_score(y_t, y_p, zero_division=0.0))
        rec = float(recall_score(y_t, y_p, zero_division=0.0))
        f1 = float(f1_score(y_t, y_p, zero_division=0.0))
        acc = float(accuracy_score(y_t, y_p))

        # Specificity: TN / (TN + FP)
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        # False Positive Rate: FP / (FP + TN)
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

        # Predicted Detection Rate: (TP + FP) / Total
        pred_rate = float(pred_pos_count / total) if total > 0 else 0.0

        return {
            "accuracy": round(acc * 100, 2),
            "precision": round(prec * 100, 2),
            "recall": round(rec * 100, 2),  # Also known as Positive-Class Recall / Actual Cases Detected
            "f1_score": round(f1 * 100, 2),
            "specificity": round(specificity * 100, 2),
            "false_positive_rate": round(fpr * 100, 2),
            "predicted_detection_rate": round(pred_rate * 100, 2),
            "support": total,
            "positive_ground_truth": pos_count,
            "negative_ground_truth": neg_count,
            "predicted_positives": pred_pos_count,
            "confusion_matrix": {
                "true_positive": tp,
                "false_positive": fp,
                "true_negative": tn,
                "false_negative": fn,
            },
            "confusion_matrix_percentages": {
                "true_positive_rate": round((tp / pos_count * 100), 2) if pos_count > 0 else 0.0,
                "false_negative_rate": round((fn / pos_count * 100), 2) if pos_count > 0 else 0.0,
                "true_negative_rate": round((tn / neg_count * 100), 2) if neg_count > 0 else 0.0,
                "false_positive_rate": round((fp / neg_count * 100), 2) if neg_count > 0 else 0.0,
            },
            "status": "Evaluated"
        }

    @staticmethod
    def calculate_category_breakdown(
        test_samples: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Computes per-category evaluation metrics for all 8 categories.
        Ensures categories with insufficient data are honestly flagged.
        """
        breakdown: Dict[str, Dict[str, Any]] = {}

        # Index predictions by sample ID
        pred_map = {p.get("id"): p for p in predictions}

        for cat in ALL_EIGHT_CATEGORIES:
            cat_samples = [s for s in test_samples if s.get("category") == cat or s.get("pattern") == cat]
            if not cat_samples:
                breakdown[cat] = {
                    "category": cat,
                    "status": "Insufficient labeled data",
                    "support": 0,
                    "positive_ground_truth": 0,
                    "negative_ground_truth": 0,
                    "accuracy": None,
                    "precision": None,
                    "recall": None,
                    "f1_score": None,
                    "false_positive_rate": None,
                    "confusion_matrix": {
                        "true_positive": 0,
                        "false_positive": 0,
                        "true_negative": 0,
                        "false_negative": 0,
                    }
                }
                continue

            y_true = []
            y_pred = []
            for s in cat_samples:
                sid = s.get("id")
                # Positive label check
                is_pos = 1 if s.get("label") in ("DARK_PATTERN", "FORCED_ACTION", "BASKET_SNEAKING") else 0
                y_true.append(is_pos)

                pred_entry = pred_map.get(sid, {})
                p_is_detected = 1 if pred_entry.get("detected") is True else 0
                y_pred.append(p_is_detected)

            metrics = EvaluationMetricsCalculator.calculate_binary_metrics(y_true, y_pred)
            metrics["category"] = cat
            breakdown[cat] = metrics

        return breakdown

    @staticmethod
    def calculate_macro_and_weighted_averages(
        category_breakdown: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes Macro (unweighted) and Weighted averages across evaluated categories.
        """
        evaluated_cats = [
            m for m in category_breakdown.values()
            if m.get("status") == "Evaluated" and m.get("support", 0) > 0
        ]

        if not evaluated_cats:
            return {
                "macro_accuracy": None,
                "macro_precision": None,
                "macro_recall": None,
                "macro_f1": None,
                "weighted_f1": None,
                "categories_evaluated_count": 0,
                "averaging_method": "Unweighted Macro Mean across all evaluated categories"
            }

        macro_acc = float(np.mean([m["accuracy"] for m in evaluated_cats if m["accuracy"] is not None]))
        macro_prec = float(np.mean([m["precision"] for m in evaluated_cats if m["precision"] is not None]))
        macro_rec = float(np.mean([m["recall"] for m in evaluated_cats if m["recall"] is not None]))
        macro_f1 = float(np.mean([m["f1_score"] for m in evaluated_cats if m["f1_score"] is not None]))

        total_weight = sum(m["support"] for m in evaluated_cats)
        if total_weight > 0:
            weighted_f1 = sum(m["f1_score"] * m["support"] for m in evaluated_cats if m["f1_score"] is not None) / total_weight
        else:
            weighted_f1 = macro_f1

        return {
            "macro_accuracy": round(macro_acc, 2),
            "macro_precision": round(macro_prec, 2),
            "macro_recall": round(macro_rec, 2),
            "macro_f1": round(macro_f1, 2),
            "weighted_f1": round(weighted_f1, 2),
            "categories_evaluated_count": len(evaluated_cats),
            "total_categories_count": len(ALL_EIGHT_CATEGORIES),
            "averaging_method": "Macro average treats each dark-pattern category equally; weighted average scales by test-set support."
        }
