from abc import ABC, abstractmethod
from typing import Any, Dict

from app.models.detection_model import DetectionFinding


class BaseDetector(ABC):
    """Abstract base detector defining standard contract for Dark Pattern detectors."""

    @property
    @abstractmethod
    def pattern_name(self) -> str:
        """Returns the formal name of the Dark Pattern."""
        pass

    @abstractmethod
    def detect(
        self,
        extracted_data: Dict[str, Any],
        evidence_record: Dict[str, Any]
    ) -> DetectionFinding:
        """
        Analyzes extracted webpage data and linked evidence to produce a DetectionFinding.
        Must link real EvidenceItem references for any positive finding.
        """
        pass
