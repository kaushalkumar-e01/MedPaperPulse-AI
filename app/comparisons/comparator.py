"""Comparison engine for 2 or 3 paper summaries, generating structured matrices."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

NOT_REPORTED = "Not reported"

STANDARD_COMPARISON_FIELDS = [
    "Objective",
    "Population",
    "Intervention",
    "Study design",
    "Sample size",
    "Findings",
    "Conclusion",
    "Limitations",
]

_FIELD_KEY_MAP = {
    "objective": ["objective", "aim", "purpose", "study_objective", "background"],
    "population": ["population", "participants", "cohort", "sample_population", "subjects"],
    "intervention": ["intervention", "exposure", "treatment", "drug", "regimen"],
    "study design": ["study design", "study_design", "design", "methodology", "type"],
    "sample size": ["sample size", "sample_size", "n", "sample", "participants_count"],
    "findings": ["findings", "results", "primary_findings", "key_findings", "outcomes"],
    "conclusion": ["conclusion", "conclusions", "summary", "takeaway"],
    "limitations": ["limitations", "study_limitations", "weaknesses"],
}


def _extract_paper_id(paper: Any, index: int) -> str:
    """Extracts paper identity (title or PMID), preserving original identifier."""
    if isinstance(paper, Mapping):
        ident = (
            paper.get("id")
            or paper.get("title")
            or paper.get("pmid")
            or paper.get("paper_id")
            or paper.get("name")
        )
        if ident:
            return str(ident).strip()
    elif hasattr(paper, "pmid") or hasattr(paper, "title"):
        ident = getattr(paper, "id", None) or getattr(paper, "pmid", None) or getattr(paper, "title", None)
        if ident:
            return str(ident).strip()

    return f"Paper {index + 1}"


def _get_field_value(paper: Any, field_name: str) -> str:
    """Extracts field value from paper, strictly returning 'Not reported' if absent or empty."""
    synonyms = _FIELD_KEY_MAP.get(field_name.lower(), [field_name.lower()])
    
    val = None
    if isinstance(paper, Mapping):
        # Case-insensitive mapping lookup
        paper_lower_map = {str(k).lower().strip(): v for k, v in paper.items()}
        for syn in synonyms:
            if syn in paper_lower_map and paper_lower_map[syn] is not None:
                val = paper_lower_map[syn]
                break
    else:
        for syn in synonyms:
            attr_syn = syn.replace(" ", "_")
            if hasattr(paper, attr_syn) and getattr(paper, attr_syn) is not None:
                val = getattr(paper, attr_syn)
                break

    if val is None:
        return NOT_REPORTED

    if isinstance(val, (list, tuple)):
        cleaned_items = [str(x).strip() for x in val if str(x).strip()]
        if not cleaned_items:
            return NOT_REPORTED
        return "; ".join(cleaned_items)

    val_str = str(val).strip()
    return val_str if val_str else NOT_REPORTED


@dataclass
class ComparisonMatrix:
    """Structured matrix comparison of multiple paper summaries."""
    paper_ids: list[str]
    fields: list[str]
    matrix: dict[str, dict[str, str]]
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_ids": self.paper_ids,
            "fields": self.fields,
            "matrix": self.matrix,
            "rows": self.rows,
        }


def compare_papers(papers: list[Any]) -> ComparisonMatrix:
    """Generates a comparison matrix for 2 or 3 paper summaries."""
    if not papers or len(papers) < 2 or len(papers) > 10:
        raise ValueError(
            f"Paper comparison requires between 2 and 10 papers, got {len(papers) if papers else 0}."
        )

    paper_ids = [_extract_paper_id(p, i) for i, p in enumerate(papers)]
    
    matrix: dict[str, dict[str, str]] = {}
    rows: list[dict[str, Any]] = []

    for field in STANDARD_COMPARISON_FIELDS:
        matrix[field] = {}
        row: dict[str, Any] = {"Field": field}
        for pid, paper in zip(paper_ids, papers):
            val = _get_field_value(paper, field)
            matrix[field][pid] = val
            row[pid] = val
        rows.append(row)

    return ComparisonMatrix(
        paper_ids=paper_ids,
        fields=STANDARD_COMPARISON_FIELDS,
        matrix=matrix,
        rows=rows,
    )
