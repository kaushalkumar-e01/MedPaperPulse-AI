"""Evidence coverage calculation for generated summaries."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from app.citations.validator import validate_summary, CitationValidationResult


@dataclass
class CoverageReport:
    """Detailed evidence coverage metrics.
    
    Denominator choice:
    The denominator is strictly the total number of summary claims evaluated.
    If total_claims is 0 (an empty summary), coverage is defined as 0.0%.
    """
    total_claims: int
    valid_claims: int
    partially_valid_claims: int
    invalid_claims: int
    uncited_claims: int
    coverage_percentage: float
    denominator_description: str
    results: list[CitationValidationResult]


def calculate_coverage(claims: list[Any] | None, passages: Any) -> float:
    """Calculates evidence coverage as the percentage of claims with valid citations."""
    if not claims:
        return 0.0

    results = validate_summary(claims, passages)
    total = len(results)
    if total == 0:
        return 0.0

    valid_count = sum(1 for r in results if r.is_valid)
    return round((valid_count / total) * 100.0, 2)


def get_coverage_report(claims: list[Any] | None, passages: Any) -> CoverageReport:
    """Generates a comprehensive coverage report with breakdown and documentation."""
    if not claims:
        return CoverageReport(
            total_claims=0,
            valid_claims=0,
            partially_valid_claims=0,
            invalid_claims=0,
            uncited_claims=0,
            coverage_percentage=0.0,
            denominator_description="Total claims in summary (0 claims provided; coverage is 0.0%).",
            results=[],
        )

    results = validate_summary(claims, passages)
    total = len(results)
    valid_count = sum(1 for r in results if r.status == "VALID")
    partial_count = sum(1 for r in results if r.status == "PARTIALLY_VALID")
    invalid_count = sum(1 for r in results if r.status == "INVALID_CITATION")
    uncited_count = sum(1 for r in results if r.status == "NO_CITATION")

    pct = round((valid_count / total) * 100.0, 2) if total > 0 else 0.0

    return CoverageReport(
        total_claims=total,
        valid_claims=valid_count,
        partially_valid_claims=partial_count,
        invalid_claims=invalid_count,
        uncited_claims=uncited_count,
        coverage_percentage=pct,
        denominator_description="Total number of evaluated summary claims.",
        results=results,
    )