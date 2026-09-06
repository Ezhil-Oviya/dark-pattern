import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import PyMongoError

from app.schemas.data_quality_schema import DataQualityAssessmentResponse
from app.services.data_quality.data_quality_service import (
    assess_audit_data_quality,
    evaluate_audit_quality_by_id,
)
from app.services.evidence.mongodb_evidence_service import (
    get_all_audits_from_mongodb,
    get_audit_details_from_mongodb,
    get_evidence_items_from_mongodb,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/data-quality/audit/{audit_id}",
    response_model=DataQualityAssessmentResponse,
    summary="Get Data Quality Assessment for a specific audit",
)
def get_audit_data_quality(audit_id: str):
    """
    Evaluates the quality and reliability of data collected during a specific audit.
    Calculates six core dimensions:
    - Completeness
    - Validity
    - Consistency
    - Relevance (Detection Readiness)
    - Uniqueness
    - Evidence Availability
    """
    try:
        assessment = evaluate_audit_quality_by_id(audit_id)
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit with ID '{audit_id}' was not found in storage.",
            )
        return assessment
    except HTTPException:
        raise
    except PyMongoError as pe:
        logger.error(f"Database error during data quality evaluation for '{audit_id}': {pe}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable while evaluating data quality: {str(pe)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during data quality assessment for '{audit_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess data quality: {str(e)}",
        )


@router.get(
    "/data-quality/audits",
    summary="List summary data quality scores for all available audits",
)
def list_audits_data_quality() -> List[Dict[str, Any]]:
    """
    Retrieves all available audits and computes high-level data quality scores
    for each audit session.
    """
    try:
        audits = get_all_audits_from_mongodb()
        summaries = []
        for audit_summary in audits:
            a_id = audit_summary.get("audit_id")
            if not a_id:
                continue
            try:
                # Load full details to compute score
                assessment = evaluate_audit_quality_by_id(a_id)
                if assessment:
                    summaries.append({
                        "audit_id": assessment.audit_id,
                        "platform": assessment.platform,
                        "start_time": assessment.start_time,
                        "pages_crawled": assessment.details.completeness.total_pages,
                        "overall_score": assessment.overall_score,
                        "overall_status": assessment.overall_status,
                        "quality_grade": assessment.quality_grade,
                        "completeness_score": assessment.dimensions["completeness"].score,
                        "validity_score": assessment.dimensions["validity"].score,
                        "consistency_score": assessment.dimensions["consistency"].score,
                        "relevance_score": assessment.dimensions["relevance"].score,
                        "uniqueness_score": assessment.dimensions["uniqueness"].score,
                        "evidence_availability_score": assessment.dimensions["evidence_availability"].score,
                    })
            except Exception as e:
                logger.warning(f"Could not compute data quality for audit '{a_id}': {e}")
                summaries.append({
                    "audit_id": a_id,
                    "platform": audit_summary.get("platform", "Unknown"),
                    "start_time": audit_summary.get("start_time", ""),
                    "pages_crawled": audit_summary.get("pages_crawled", 0),
                    "overall_score": None,
                    "overall_status": "INSUFFICIENT_DATA",
                    "quality_grade": "N/A",
                })
        return summaries
    except PyMongoError as pe:
        logger.error(f"Database error retrieving audits list for data quality: {pe}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(pe)}",
        )
    except Exception as e:
        logger.error(f"Error listing audits data quality: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list audits data quality: {str(e)}",
        )


@router.post(
    "/data-quality/evaluate-raw",
    response_model=DataQualityAssessmentResponse,
    summary="Evaluate data quality of a raw audit payload on-demand",
)
def evaluate_raw_audit_data_quality(payload: Dict[str, Any]):
    """
    Directly evaluates a raw audit dictionary and optional evidence items without
    requiring prior database persistence.
    """
    try:
        audit_data = payload.get("audit", payload)
        evidence_items = payload.get("evidence_items", [])
        return assess_audit_data_quality(audit_data, evidence_items)
    except Exception as e:
        logger.error(f"Error evaluating raw audit data quality: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed audit payload: {str(e)}",
        )
