import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.services.evaluation.evaluation_service import get_evaluation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/algorithm-analysis", tags=["Algorithm Analysis & Evaluation"])


class RunEvaluationRequest(BaseModel):
    random_seed: int = Field(default=42, description="Random seed for reproducible train/test split")
    test_size: float = Field(default=0.30, ge=0.1, le=0.5, description="Proportion of held-out test split")


@router.get("/overview", summary="Get comprehensive algorithm evaluation overview")
async def get_overview():
    """
    Returns latest empirical evaluation results for our proposed multi-modal model
    along with reproduced baselines, per-category metrics, and dataset provenance.
    """
    try:
        service = get_evaluation_service()
        return service.get_overview()
    except Exception as e:
        logger.error(f"Error retrieving evaluation overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate evaluation overview: {str(e)}")


@router.get("/algorithms", summary="Get detailed architectures and configurations for all algorithms")
async def get_algorithms():
    """
    Returns deep technical documentation, architectures, hyperparameters,
    and limitations for the proposed architecture and all reproduced baselines.
    """
    service = get_evaluation_service()
    return {
        "status": "success",
        "algorithms": service.get_algorithm_details()
    }


@router.get("/metrics", summary="Get overall performance metrics and macro/weighted averages")
async def get_metrics(evaluation_id: Optional[str] = Query(default=None)):
    """
    Returns accuracy, precision, recall, F1, specificity, FPR, and predicted detection rate.
    """
    service = get_evaluation_service()
    eval_data = service.repository.get_evaluation_by_id(evaluation_id) if evaluation_id else service.get_latest_or_run()
    if not eval_data:
        raise HTTPException(status_code=404, detail="No evaluation record found.")

    return {
        "evaluation_id": eval_data.get("evaluation_id"),
        "created_at": eval_data.get("created_at"),
        "proposed_metrics": eval_data.get("proposed_metrics"),
        "averages": eval_data.get("proposed_averages"),
        "baselines": [
            {"name": b.get("name"), "paradigm": b.get("paradigm"), "metrics": b.get("metrics")}
            for b in eval_data.get("baseline_evaluations", [])
        ]
    }


@router.get("/categories", summary="Get per-category evaluation metrics across all 8 dark patterns")
async def get_categories(evaluation_id: Optional[str] = Query(default=None)):
    """
    Returns sample counts, TP, FP, TN, FN, precision, recall, and F1 for all 8 categories.
    """
    service = get_evaluation_service()
    eval_data = service.repository.get_evaluation_by_id(evaluation_id) if evaluation_id else service.get_latest_or_run()
    if not eval_data:
        raise HTTPException(status_code=404, detail="No evaluation record found.")

    return {
        "evaluation_id": eval_data.get("evaluation_id"),
        "categories": eval_data.get("category_breakdown", {}),
        "total_categories": len(eval_data.get("category_breakdown", {})),
    }


@router.get("/confusion-matrix", summary="Get interactive confusion matrix data")
async def get_confusion_matrix(
    category: Optional[str] = Query(default=None, description="Dark pattern category, or None for overall"),
    evaluation_id: Optional[str] = Query(default=None)
):
    """
    Returns confusion matrix counts (TP, FP, TN, FN) and row-normalized percentages.
    """
    service = get_evaluation_service()
    eval_data = service.repository.get_evaluation_by_id(evaluation_id) if evaluation_id else service.get_latest_or_run()
    if not eval_data:
        raise HTTPException(status_code=404, detail="No evaluation record found.")

    if category and category in eval_data.get("category_breakdown", {}):
        cat_data = eval_data["category_breakdown"][category]
        return {
            "scope": category,
            "confusion_matrix": cat_data.get("confusion_matrix"),
            "confusion_matrix_percentages": cat_data.get("confusion_matrix_percentages"),
            "support": cat_data.get("support")
        }

    # Overall matrix
    prop_met = eval_data.get("proposed_metrics", {})
    return {
        "scope": "Overall Model Performance",
        "confusion_matrix": prop_met.get("confusion_matrix"),
        "confusion_matrix_percentages": prop_met.get("confusion_matrix_percentages"),
        "support": prop_met.get("support")
    }


@router.get("/literature", summary="Get verified published research benchmarks and citations")
async def get_literature():
    """
    Returns verified academic literature records with paper titles, authors,
    DOIs, reported metrics, datasets, and explicit comparability designations.
    """
    service = get_evaluation_service()
    records = service.get_literature()
    return {
        "status": "success",
        "total_records": len(records),
        "literature_benchmarks": records
    }


@router.get("/evaluations", summary="List historical evaluation runs")
async def list_evaluations():
    """Returns list of previous experiment evaluation runs with timestamps and F1 scores."""
    service = get_evaluation_service()
    evals = service.repository.list_evaluations()
    summaries = []
    for e in evals:
        summaries.append({
            "evaluation_id": e.get("evaluation_id"),
            "created_at": e.get("created_at"),
            "dataset_name": e.get("dataset_name"),
            "dataset_version": e.get("dataset_version"),
            "test_sample_count": e.get("test_sample_count"),
            "f1_score": e.get("proposed_metrics", {}).get("f1_score"),
            "accuracy": e.get("proposed_metrics", {}).get("accuracy"),
        })
    return {
        "status": "success",
        "total_runs": len(summaries),
        "evaluations": summaries
    }


@router.get("/evaluations/{evaluation_id}", summary="Get specific evaluation run details")
async def get_evaluation_by_id(evaluation_id: str):
    service = get_evaluation_service()
    data = service.repository.get_evaluation_by_id(evaluation_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Evaluation '{evaluation_id}' not found.")
    return data


@router.post("/evaluate", summary="Execute a fresh evaluation run")
async def trigger_evaluation(payload: RunEvaluationRequest):
    """
    Runs a fresh, reproducible scientific evaluation of the proposed pipeline
    and baselines on a held-out test split with the specified random seed.
    """
    try:
        service = get_evaluation_service()
        result = service.run_evaluation(
            random_seed=payload.random_seed,
            test_size=payload.test_size
        )
        return {
            "status": "success",
            "message": f"Evaluation '{result.get('evaluation_id')}' completed successfully.",
            "evaluation": result
        }
    except Exception as e:
        logger.error(f"Error executing evaluation run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation run failed: {str(e)}")


@router.get("/evaluations/{evaluation_id}/export/csv", summary="Export evaluation report as CSV")
async def export_csv(evaluation_id: str):
    service = get_evaluation_service()
    csv_content = service.export_csv(evaluation_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={evaluation_id}_report.csv"}
    )


@router.get("/evaluations/{evaluation_id}/export/pdf", summary="Export evaluation report as PDF")
async def export_pdf(evaluation_id: str):
    service = get_evaluation_service()
    pdf_bytes = service.export_pdf(evaluation_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={evaluation_id}_report.pdf"}
    )
