"""Citation validation and evidence coverage module for MedPaperPulse-AI (Person 4)."""

from app.citations.validator import (
    CitationValidationResult,
    validate_citation,
    validate_summary,
    normalize_passages,
    normalize_claim,
)
from app.citations.coverage import (
    calculate_coverage,
    get_coverage_report,
    CoverageReport,
)
from app.citations.support_checker import (
    check_numeric_support,
    extract_numbers,
    NumericSupportResult,
    ExtractedNumber,
)

__all__ = [
    "CitationValidationResult",
    "validate_citation",
    "validate_summary",
    "normalize_passages",
    "normalize_claim",
    "calculate_coverage",
    "get_coverage_report",
    "CoverageReport",
    "check_numeric_support",
    "extract_numbers",
    "NumericSupportResult",
    "ExtractedNumber",
]