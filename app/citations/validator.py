"""Citation validator checking citation existence and validating claim references."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class CitationValidationResult:
    """Structured result of citation validation for a single claim."""
    claim_text: str
    cited_ids: list[str]
    valid_ids: list[str]
    missing_ids: list[str]
    status: str  # "VALID", "INVALID_CITATION", "NO_CITATION", "PARTIALLY_VALID"
    is_valid: bool  # True only if has citations and NO missing IDs
    has_citations: bool
    details: str = ""
    support_status: dict[str, Any] = field(default_factory=dict)


def normalize_passages(passages: Any) -> dict[str, str]:
    """Safely normalizes passages into a dict mapping sentence ID -> text."""
    if not passages:
        return {}

    if isinstance(passages, Mapping):
        normalized = {}
        for k, v in passages.items():
            if isinstance(v, str):
                normalized[str(k).strip()] = v.strip()
            elif isinstance(v, Mapping):
                text = v.get("text") or v.get("content") or v.get("sentence") or ""
                normalized[str(k).strip()] = str(text).strip()
            elif hasattr(v, "text"):
                normalized[str(k).strip()] = str(v.text).strip()
            else:
                normalized[str(k).strip()] = str(v).strip()
        return normalized

    if isinstance(passages, (list, tuple, set)):
        normalized = {}
        for idx, item in enumerate(passages):
            if isinstance(item, Mapping):
                s_id = item.get("id") or item.get("sentence_id") or item.get("passage_id") or f"s{idx+1}"
                text = item.get("text") or item.get("content") or item.get("sentence") or ""
                normalized[str(s_id).strip()] = str(text).strip()
            elif hasattr(item, "id") or hasattr(item, "sentence_id"):
                s_id = getattr(item, "id", None) or getattr(item, "sentence_id", None) or f"s{idx+1}"
                text = getattr(item, "text", None) or getattr(item, "content", "")
                normalized[str(s_id).strip()] = str(text).strip()
            elif isinstance(item, str):
                normalized[f"s{idx+1}"] = item.strip()
        return normalized

    return {}


def normalize_claim(claim: Any) -> tuple[str, list[str]]:
    """Extracts (claim_text, list_of_cited_ids) safely from a claim object or dict."""
    if not claim:
        return "", []

    claim_text = ""
    raw_citations = []

    if isinstance(claim, Mapping):
        claim_text = claim.get("claim") or claim.get("text") or claim.get("claim_text") or ""
        raw_citations = claim.get("citations") or claim.get("cited_ids") or claim.get("citation_ids") or []
    elif hasattr(claim, "claim") or hasattr(claim, "text"):
        claim_text = getattr(claim, "claim", None) or getattr(claim, "text", "") or ""
        raw_citations = getattr(claim, "citations", None) or getattr(claim, "cited_ids", None) or []
    elif isinstance(claim, str):
        claim_text = claim
        raw_citations = []

    if not isinstance(raw_citations, (list, tuple, set)):
        if isinstance(raw_citations, str):
            raw_citations = [raw_citations] if raw_citations.strip() else []
        else:
            raw_citations = []

    seen = set()
    cleaned_citations = []
    for c in raw_citations:
        c_str = str(c).strip()
        if c_str and c_str not in seen:
            seen.add(c_str)
            cleaned_citations.append(c_str)

    return str(claim_text).strip(), cleaned_citations


def validate_citation(claim: Any, passages: Any) -> CitationValidationResult:
    """Validates citations of a single summary claim against supplied paper passages."""
    claim_text, cited_ids = normalize_claim(claim)
    passage_map = normalize_passages(passages)

    if not cited_ids:
        return CitationValidationResult(
            claim_text=claim_text,
            cited_ids=[],
            valid_ids=[],
            missing_ids=[],
            status="NO_CITATION",
            is_valid=False,
            has_citations=False,
            details="Claim has no associated citation IDs.",
        )

    valid_ids = [cid for cid in cited_ids if cid in passage_map]
    missing_ids = [cid for cid in cited_ids if cid not in passage_map]

    if not missing_ids and valid_ids:
        status = "VALID"
        is_valid = True
        details = f"All {len(valid_ids)} cited passage ID(s) exist in source text."
    elif missing_ids and valid_ids:
        status = "PARTIALLY_VALID"
        is_valid = False
        details = f"Missing IDs: {missing_ids}; Valid IDs: {valid_ids}."
    else:
        status = "INVALID_CITATION"
        is_valid = False
        details = f"All cited IDs are nonexistent: {missing_ids}."

    return CitationValidationResult(
        claim_text=claim_text,
        cited_ids=cited_ids,
        valid_ids=valid_ids,
        missing_ids=missing_ids,
        status=status,
        is_valid=is_valid,
        has_citations=True,
        details=details,
    )


def validate_summary(claims: list[Any] | None, passages: Any) -> list[CitationValidationResult]:
    """Validates all claims in a summary against the supplied paper passages."""
    if not claims:
        return []
    return [validate_citation(c, passages) for c in claims]