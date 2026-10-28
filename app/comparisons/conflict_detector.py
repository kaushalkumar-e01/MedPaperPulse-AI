"""Scientific conflict and comparability detector across paper findings."""

from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from app.comparisons.comparator import compare_papers, NOT_REPORTED


class ComparisonStatus(str, Enum):
    CONFLICT = "Conflict"
    CONSISTENT = "Consistent"
    NOT_COMPARABLE = "Not directly comparable"
    INSUFFICIENT_INFO = "Insufficient information"


@dataclass
class ConflictAnalysisResult:
    """Result of conflict and comparability detection."""
    status: ComparisonStatus
    reason: str
    paper_ids: list[str]
    details: dict[str, Any]


_BENEFIT_WORDS = {"reduced", "decreased", "improved", "effective", "beneficial", "cured", "lowered", "prevented"}
_NULL_WORDS = {"no effect", "ineffective", "no difference", "failed", "did not reduce", "did not improve", "no significant"}
_HARM_WORDS = {"increased mortality", "harmful", "increased risk", "adverse", "toxic", "worsened"}


def _classify_direction(text: str) -> str:
    """Classifies finding direction as positive, null, adverse, or unclear."""
    t = text.lower()
    for w in _NULL_WORDS:
        if w in t:
            return "NULL"
    for w in _HARM_WORDS:
        if w in t:
            return "HARM"
    for w in _BENEFIT_WORDS:
        if w in t:
            return "BENEFIT"
    return "UNCLEAR"


def _compare_two_papers(
    id1: str, p1: dict[str, str],
    id2: str, p2: dict[str, str]
) -> tuple[ComparisonStatus, str]:
    """Evaluates conflict/comparability between two normalized paper field maps."""
    f1 = p1.get("Findings", NOT_REPORTED)
    f2 = p2.get("Findings", NOT_REPORTED)
    int1 = p1.get("Intervention", NOT_REPORTED)
    int2 = p2.get("Intervention", NOT_REPORTED)
    pop1 = p1.get("Population", NOT_REPORTED)
    pop2 = p2.get("Population", NOT_REPORTED)
    des1 = p1.get("Study design", NOT_REPORTED)
    des2 = p2.get("Study design", NOT_REPORTED)

    if f1 == NOT_REPORTED or f2 == NOT_REPORTED:
        return (
            ComparisonStatus.INSUFFICIENT_INFO,
            f"Findings are missing ('{NOT_REPORTED}') in one or both papers ({id1}, {id2}).",
        )

    animal_terms = {"mouse", "mice", "rat", "in vitro", "animal", "cell culture"}
    human_terms = {"patients", "human", "clinical trial", "rct", "phase 3", "phase iii"}

    is_animal_1 = any(t in pop1.lower() or t in des1.lower() for t in animal_terms)
    is_human_2 = any(t in pop2.lower() or t in des2.lower() for t in human_terms)
    is_animal_2 = any(t in pop2.lower() or t in des2.lower() for t in animal_terms)
    is_human_1 = any(t in pop1.lower() or t in des1.lower() for t in human_terms)

    if (is_animal_1 and is_human_2) or (is_animal_2 and is_human_1):
        return (
            ComparisonStatus.NOT_COMPARABLE,
            "Key factors differ materially: one study was conducted in vitro/animal models and the other in human patients.",
        )

    if int1 != NOT_REPORTED and int2 != NOT_REPORTED:
        tokens1 = set(re.findall(r'\b[a-zA-Z]{4,}\b', int1.lower()))
        tokens2 = set(re.findall(r'\b[a-zA-Z]{4,}\b', int2.lower()))
        if tokens1 and tokens2 and not (tokens1 & tokens2):
            return (
                ComparisonStatus.NOT_COMPARABLE,
                f"Studies evaluate materially different interventions: '{int1}' vs '{int2}'.",
            )

    dir1 = _classify_direction(f1)
    dir2 = _classify_direction(f2)

    if (dir1 == "BENEFIT" and dir2 in {"NULL", "HARM"}) or (dir2 == "BENEFIT" and dir1 in {"NULL", "HARM"}):
        return (
            ComparisonStatus.CONFLICT,
            f"Studies reported opposing findings on comparable outcomes: '{id1}' indicated benefit/efficacy while '{id2}' found no significant effect or adverse outcomes.",
        )

    if dir1 == dir2 and dir1 in {"BENEFIT", "NULL", "HARM"}:
        return (
            ComparisonStatus.CONSISTENT,
            f"Both studies reported consistent directional findings ({dir1.lower()}).",
        )

    return (
        ComparisonStatus.CONSISTENT,
        "No explicit contradiction detected based on structured evidence.",
    )


def detect_conflicts(papers: list[Any]) -> ConflictAnalysisResult:
    """Analyzes 2 or 3 papers for scientific conflicts or non-comparability."""
    matrix_obj = compare_papers(papers)
    paper_ids = matrix_obj.paper_ids

    paper_fields: dict[str, dict[str, str]] = {pid: {} for pid in paper_ids}
    for field, p_dict in matrix_obj.matrix.items():
        for pid, val in p_dict.items():
            paper_fields[pid][field] = val

    pairwise_results = []
    for i in range(len(paper_ids)):
        for j in range(i + 1, len(paper_ids)):
            id1, id2 = paper_ids[i], paper_ids[j]
            status, reason = _compare_two_papers(id1, paper_fields[id1], id2, paper_fields[id2])
            pairwise_results.append({
                "pair": (id1, id2),
                "status": status,
                "reason": reason,
            })

    statuses = [r["status"] for r in pairwise_results]
    if ComparisonStatus.CONFLICT in statuses:
        conflict_pair = next(r for r in pairwise_results if r["status"] == ComparisonStatus.CONFLICT)
        final_status = ComparisonStatus.CONFLICT
        final_reason = conflict_pair["reason"]
    elif ComparisonStatus.NOT_COMPARABLE in statuses:
        non_comp = next(r for r in pairwise_results if r["status"] == ComparisonStatus.NOT_COMPARABLE)
        final_status = ComparisonStatus.NOT_COMPARABLE
        final_reason = non_comp["reason"]
    elif ComparisonStatus.INSUFFICIENT_INFO in statuses:
        insuf = next(r for r in pairwise_results if r["status"] == ComparisonStatus.INSUFFICIENT_INFO)
        final_status = ComparisonStatus.INSUFFICIENT_INFO
        final_reason = insuf["reason"]
    else:
        final_status = ComparisonStatus.CONSISTENT
        final_reason = pairwise_results[0]["reason"] if pairwise_results else "Findings are consistent."

    return ConflictAnalysisResult(
        status=final_status,
        reason=final_reason,
        paper_ids=paper_ids,
        details={"pairwise": pairwise_results},
    )