"""Paper comparison and scientific conflict detection module (Person 4)."""

from app.comparisons.comparator import (
    ComparisonMatrix,
    compare_papers,
    STANDARD_COMPARISON_FIELDS,
)
from app.comparisons.conflict_detector import (
    detect_conflicts,
    ConflictAnalysisResult,
    ComparisonStatus,
)

__all__ = [
    "ComparisonMatrix",
    "compare_papers",
    "STANDARD_COMPARISON_FIELDS",
    "detect_conflicts",
    "ConflictAnalysisResult",
    "ComparisonStatus",
]