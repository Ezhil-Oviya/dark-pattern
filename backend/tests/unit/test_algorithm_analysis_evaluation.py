import pytest
from app.services.evaluation.dataset_manager import BenchmarkDatasetManager, get_dataset_manager
from app.services.evaluation.metrics_calculator import (
    ALL_EIGHT_CATEGORIES,
    EvaluationMetricsCalculator,
)
from app.services.evaluation.baseline_models import (
    DeterministicRegexBaseline,
    TextOnlyTransformerBaseline,
    TfidfLinearSvmBaseline,
    TfidfLogisticRegressionBaseline,
)
from app.services.evaluation.literature_repository import PublishedLiteratureRepository
from app.services.evaluation.report_generator import EvaluationReportGenerator
from app.services.evaluation.evaluation_service import get_evaluation_service


def test_metric_calculations_basic():
    """Verify precision, recall, accuracy, and F1-score on known binary targets."""
    # 4 True Positives, 1 False Positive, 4 True Negatives, 1 False Negative
    y_true = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    y_pred = [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]

    metrics = EvaluationMetricsCalculator.calculate_binary_metrics(y_true, y_pred)
    assert metrics["support"] == 10
    assert metrics["positive_ground_truth"] == 5
    assert metrics["negative_ground_truth"] == 5
    assert metrics["confusion_matrix"]["true_positive"] == 4
    assert metrics["confusion_matrix"]["false_positive"] == 1
    assert metrics["confusion_matrix"]["true_negative"] == 4
    assert metrics["confusion_matrix"]["false_negative"] == 1

    # Accuracy: 8/10 = 80.0%
    assert metrics["accuracy"] == 80.0
    # Precision: 4 / (4 + 1) = 80.0%
    assert metrics["precision"] == 80.0
    # Recall: 4 / (4 + 1) = 80.0%
    assert metrics["recall"] == 80.0
    # F1-Score: 80.0%
    assert metrics["f1_score"] == 80.0
    # FPR: 1 / 5 = 20.0%
    assert metrics["false_positive_rate"] == 20.0


def test_undefined_metric_cases_safe_handling():
    """Verify zero-division cases produce 0.0 or None rather than raising ZeroDivisionError."""
    # All true negative, all predicted negative (no positive predictions)
    y_true = [0, 0, 0]
    y_pred = [0, 0, 0]
    metrics = EvaluationMetricsCalculator.calculate_binary_metrics(y_true, y_pred)
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0
    assert metrics["accuracy"] == 100.0

    # Empty inputs
    empty_metrics = EvaluationMetricsCalculator.calculate_binary_metrics([], [])
    assert empty_metrics["accuracy"] is None
    assert empty_metrics["support"] == 0


def test_macro_and_weighted_averages():
    """Verify macro and weighted averaging across evaluated categories."""
    mock_breakdown = {
        "False Urgency": {
            "status": "Evaluated",
            "support": 10,
            "accuracy": 90.0,
            "precision": 90.0,
            "recall": 90.0,
            "f1_score": 90.0,
        },
        "Basket Sneaking": {
            "status": "Evaluated",
            "support": 20,
            "accuracy": 80.0,
            "precision": 80.0,
            "recall": 80.0,
            "f1_score": 80.0,
        },
        "Forced Action": {
            "status": "Insufficient labeled data",
            "support": 0,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
        }
    }

    avg = EvaluationMetricsCalculator.calculate_macro_and_weighted_averages(mock_breakdown)
    assert avg["categories_evaluated_count"] == 2
    # Macro F1: (90 + 80) / 2 = 85.0
    assert avg["macro_f1"] == 85.0
    # Weighted F1: (90*10 + 80*20) / 30 = 2500 / 30 = 83.33
    assert avg["weighted_f1"] == 83.33


def test_dataset_leakage_prevention():
    """Ensure train and test splits have zero overlap."""
    dm = get_dataset_manager()
    train_samples, test_samples = dm.get_train_test_split(test_size=0.30, random_state=42)

    assert len(train_samples) > 0
    assert len(test_samples) > 0

    train_ids = {s["id"] for s in train_samples}
    test_ids = {s["id"] for s in test_samples}

    # Intersect must be empty (0 leakage)
    overlap = train_ids.intersection(test_ids)
    assert len(overlap) == 0, f"Data leakage detected! Overlapping sample IDs: {overlap}"


def test_literature_repository_verified_records():
    """Verify published research records are distinct and contain verified citations."""
    records = PublishedLiteratureRepository.get_all_records()
    assert len(records) >= 5

    for r in records:
        assert "title" in r and len(r["title"]) > 0
        assert "authors" in r and len(r["authors"]) > 0
        assert "year" in r and r["year"] >= 2018
        assert "doi" in r and len(r["doi"]) > 0
        assert "comparability" in r
        assert r["comparability"] in ("Directly comparable under a shared reproduced protocol", "Partially comparable", "Literature context only")
        assert "comparability_reason" in r and len(r["comparability_reason"]) > 0


def test_baseline_models_training_and_inference():
    """Ensure all baseline models can be trained and evaluated on sample datasets."""
    train_mock = [
        {"id": "t1", "text": "Hurry! 04:59 minutes left on this sale!", "label": "DARK_PATTERN"},
        {"id": "t2", "text": "Add 2-Year Protection Plan for ₹299", "label": "DARK_PATTERN"},
        {"id": "t3", "text": "Order details: Standard shipping delivery ₹50", "label": "BENIGN"},
        {"id": "t4", "text": "I agree to Terms of Service and Privacy Policy", "label": "BENIGN"},
    ]
    test_mock = [
        {"id": "test1", "text": "Hurry, deal ends in 2 mins!", "category": "False Urgency", "label": "DARK_PATTERN"},
        {"id": "test2", "text": "Delivery address: 123 Main St", "category": "Forced Action", "label": "BENIGN"},
    ]

    baselines = [
        TfidfLogisticRegressionBaseline(),
        TfidfLinearSvmBaseline(),
        TextOnlyTransformerBaseline(),
        DeterministicRegexBaseline(),
    ]

    for b in baselines:
        b.train(train_mock)
        preds = b.predict(test_mock)
        assert len(preds) == 2
        assert preds[0]["id"] == "test1"
        assert preds[1]["id"] == "test2"
        assert "detected" in preds[0]
        assert "confidence" in preds[0]


def test_report_generation_csv_and_pdf():
    """Verify CSV and PDF export generator functions produce valid non-empty outputs."""
    service = get_evaluation_service()
    eval_data = service.get_latest_or_run()
    assert eval_data is not None

    csv_content = EvaluationReportGenerator.generate_csv(eval_data)
    assert len(csv_content) > 200
    assert "DARK PATTERN COMPLIANCE AUDITING FRAMEWORK" in csv_content
    assert "SECTION 1: OUR EXPERIMENTAL RESULTS" in csv_content
    assert "SECTION 2: EIGHT-CATEGORY DETECTION ANALYSIS" in csv_content
    assert "SECTION 3: PUBLISHED RESEARCH BENCHMARKS" in csv_content

    pdf_bytes = EvaluationReportGenerator.generate_pdf(eval_data)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
