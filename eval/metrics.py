"""Automated Quality and Faithfulness Metrics for MedPaperPulse-AI.

Implements:
1. Numeric faithfulness (numeric token extraction and passage verification)
2. Citation resolution rate (verifying supported_by passage IDs against source passages)
3. Required-field presence (PICO, design, objective, findings, conclusion, limitations)
4. Overall composite metrics and edge-case validation
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models import PaperRecord, Passage, SummaryResult, MISSING_INFO_INDICATOR


# Regex pattern to identify numeric tokens: integers, decimals, percentages, ratios, scientific notation
NUMERIC_PATTERN = re.compile(
    r"""
    (?:\b|(?<=[^\w\.]))
    (?:
        [+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:%|mg|ug|g|kg|ml|l|months?|years?|days?|hours?|pts?|%)?
        |
        [pP]\s*[<>=]\s*0?\.\d+
        |
        (?:HR|OR|RR|AUC)\s*[=:]?\s*\d+\.\d+
    )
    (?:\b|(?=[^\w\.]))
    """,
    re.VERBOSE | re.IGNORECASE,
)


def extract_numeric_tokens(text: str) -> List[str]:
    """Extracts normalized numeric tokens from text for verification."""
    if not text or text == MISSING_INFO_INDICATOR:
        return []
    
    matches = NUMERIC_PATTERN.findall(text)
    cleaned = []
    for m in matches:
        token = m.strip().rstrip(".,;:)")
        # Exclude solitary section/passage IDs like S1, S2
        if re.match(r"^S\d+$", token, re.IGNORECASE):
            continue
        if any(c.isdigit() for c in token):
            cleaned.append(token)
    return cleaned


def normalize_num(token: str) -> str:
    """Normalizes numeric representations (e.g. '1,420' -> '1420', '0.74' -> '.74')."""
    t = token.replace(",", "").strip().lower()
    t = re.sub(r"\s+", "", t)
    return t


def token_is_in_text(token: str, text: str) -> bool:
    """Checks whether a normalized numeric token is represented in target text."""
    norm_token = normalize_num(token)
    norm_text = normalize_num(text)
    
    if norm_token in norm_text:
        return True
    
    # Try purely numeric component (stripping trailing units)
    pure_num_match = re.search(r"[-+]?\d*\.?\d+", norm_token)
    if pure_num_match:
        pure_num = pure_num_match.group(0)
        if pure_num and pure_num in norm_text:
            return True
            
    return False


def evaluate_numeric_faithfulness(
    paper: PaperRecord,
    summary: SummaryResult,
) -> Dict[str, Any]:
    """Evaluates whether numbers in generated claims are supported by cited passages.
    
    Returns:
        Dict with total_checked, supported, unsupported, faithfulness_rate, and details.
    """
    passage_map: Dict[str, str] = {p.id: p.text for p in paper.passages}
    abstract_full_text = " ".join([p.text for p in paper.passages])

    all_claims = []
    if summary.objective:
        all_claims.append(("objective", summary.objective))
    all_claims.extend([("finding", f) for f in summary.findings])
    if summary.conclusion:
        all_claims.append(("conclusion", summary.conclusion))
    all_claims.extend([("limitation", lim) for lim in summary.limitations])

    total_numeric_claims = 0
    supported_claims = 0
    unsupported_claims = 0
    unsupported_details: List[Dict[str, Any]] = []

    for claim_type, claim in all_claims:
        if not claim.text or claim.text == MISSING_INFO_INDICATOR:
            continue
            
        numbers = extract_numeric_tokens(claim.text)
        if not numbers:
            continue
            
        total_numeric_claims += 1

        # Determine target text to verify against
        cited_texts = [passage_map[pid] for pid in claim.supported_by if pid in passage_map]
        verification_text = " ".join(cited_texts) if cited_texts else abstract_full_text

        missing_numbers = []
        for num in numbers:
            if not token_is_in_text(num, verification_text):
                # Fallback to full abstract if cited passage omitted the baseline
                if not token_is_in_text(num, abstract_full_text):
                    missing_numbers.append(num)

        if not missing_numbers:
            supported_claims += 1
        else:
            unsupported_claims += 1
            unsupported_details.append({
                "claim_type": claim_type,
                "claim_text": claim.text,
                "supported_by": claim.supported_by,
                "missing_tokens": missing_numbers,
            })

    faithfulness_rate = (
        (supported_claims / total_numeric_claims * 100.0)
        if total_numeric_claims > 0
        else 100.0
    )

    return {
        "total_numeric_claims": total_numeric_claims,
        "supported_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "faithfulness_rate": round(faithfulness_rate, 2),
        "unsupported_details": unsupported_details,
        "requires_manual_review": len(unsupported_details) > 0,
    }


def evaluate_citation_resolution(
    paper: PaperRecord,
    summary: SummaryResult,
) -> Dict[str, Any]:
    """Verifies whether each claim's supported_by passage IDs exist in source passages.
    
    Returns:
        Dict with total_claims, resolvable_claims, unresolvable_claims, resolution_rate.
    """
    known_passage_ids: Set[str] = {p.id for p in paper.passages}

    all_claims = []
    if summary.objective:
        all_claims.append(summary.objective)
    all_claims.extend(summary.findings)
    if summary.conclusion:
        all_claims.append(summary.conclusion)
    all_claims.extend(summary.limitations)

    total_claims = 0
    resolvable_claims = 0
    unresolvable_claims = 0
    unresolved_details: List[Dict[str, Any]] = []

    for claim in all_claims:
        if not claim.text:
            continue
            
        total_claims += 1
        # Claims with "Not reported in the abstract." may legitimately have empty supported_by
        if claim.text == MISSING_INFO_INDICATOR and not claim.supported_by:
            resolvable_claims += 1
            continue

        if not claim.supported_by:
            unresolvable_claims += 1
            unresolved_details.append({
                "claim_text": claim.text,
                "supported_by": claim.supported_by,
                "reason": "Missing citation references",
            })
            continue

        invalid_ids = [pid for pid in claim.supported_by if pid not in known_passage_ids]
        if not invalid_ids:
            resolvable_claims += 1
        else:
            unresolvable_claims += 1
            unresolved_details.append({
                "claim_text": claim.text,
                "supported_by": claim.supported_by,
                "invalid_ids": invalid_ids,
                "reason": "Unknown passage IDs",
            })

    resolution_rate = (
        (resolvable_claims / total_claims * 100.0)
        if total_claims > 0
        else 100.0
    )

    return {
        "total_claims": total_claims,
        "resolvable_claims": resolvable_claims,
        "unresolvable_claims": unresolvable_claims,
        "citation_resolution_rate": round(resolution_rate, 2),
        "unresolved_details": unresolved_details,
    }


def evaluate_required_fields(summary: SummaryResult) -> Dict[str, Any]:
    """Checks whether all required structured fields in SummaryResult are present and valid."""
    fields_to_check = [
        ("objective", bool(summary.objective and summary.objective.text)),
        ("pico.population", bool(summary.pico.get("population"))),
        ("pico.intervention", bool(summary.pico.get("intervention"))),
        ("pico.comparison", bool(summary.pico.get("comparison"))),
        ("pico.outcome", bool(summary.pico.get("outcome"))),
        ("design", bool(summary.design)),
        ("findings", len(summary.findings) > 0),
        ("conclusion", bool(summary.conclusion and summary.conclusion.text)),
        ("limitations", len(summary.limitations) > 0),
    ]

    total_fields = len(fields_to_check)
    present_fields = sum(1 for name, ok in fields_to_check if ok)
    missing_field_names = [name for name, ok in fields_to_check if not ok]

    presence_rate = round((present_fields / total_fields * 100.0), 2)

    return {
        "total_fields": total_fields,
        "present_fields": present_fields,
        "missing_fields": missing_field_names,
        "field_presence_rate": presence_rate,
    }


def evaluate_summary(
    paper: PaperRecord,
    summary: SummaryResult,
) -> Dict[str, Any]:
    """Runs all automated evaluation checks on a single paper-summary pair."""
    num_res = evaluate_numeric_faithfulness(paper, summary)
    cite_res = evaluate_citation_resolution(paper, summary)
    field_res = evaluate_required_fields(summary)

    return {
        "paper_id": paper.pmid or "SYNTHETIC",
        "title": paper.title,
        "numeric_faithfulness": num_res,
        "citation_resolution": cite_res,
        "required_fields": field_res,
    }
