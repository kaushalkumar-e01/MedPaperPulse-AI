"""Numeric extraction and evidence support checker for medical claims."""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
from app.citations.validator import normalize_claim, normalize_passages


@dataclass
class ExtractedNumber:
    """Represents an extracted numeric token with canonical normalization."""
    raw: str
    kind: str  # "percentage", "range", "scientific", "p_value", "number"
    canonical_val: float | tuple[float, float]
    text_representation: str


@dataclass
class NumericSupportResult:
    """Structured result of numeric evidence checking."""
    is_supported: bool
    status: str  # "SUPPORTED", "MISMATCH", "UNSUPPORTED", "NO_NUMBERS", "NO_EVIDENCE"
    claim_numbers: list[str]
    evidence_numbers: list[str]
    matched_numbers: list[str]
    unmatched_numbers: list[str]
    details: str


def _clean_commas(val_str: str) -> str:
    return val_str.replace(",", "")


def extract_numbers(text: str) -> list[ExtractedNumber]:
    """Extracts numeric values from text: percentages, decimals, integers, ranges,
    scientific notation, and p-values.
    """
    if not text:
        return []

    results: list[ExtractedNumber] = []
    text_lower = text.lower()

    # 1. Scientific notation (e.g., 1.5e-3, 2.3 x 10^-4, 1.2 * 10^5)
    sci_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:[x×*]\s*10\^?([+-]?\d+)|e([+-]?\d+))\b')
    for m in sci_pattern.finditer(text_lower):
        raw = m.group(0)
        base = float(m.group(1))
        exp = int(m.group(2) or m.group(3))
        val = base * (10 ** exp)
        results.append(ExtractedNumber(
            raw=raw,
            kind="scientific",
            canonical_val=round(val, 8),
            text_representation=f"{val:.6e}",
        ))

    # 2. P-values (e.g., p < 0.05, p = 0.001, p <= 0.01)
    p_pattern = re.compile(r'\bp\s*([<>=≤≥]|<=|>=)\s*(\d+(?:\.\d+)?)\b')
    for m in p_pattern.finditer(text_lower):
        raw = m.group(0)
        op = m.group(1)
        val = float(m.group(2))
        results.append(ExtractedNumber(
            raw=raw,
            kind="p_value",
            canonical_val=val,
            text_representation=f"p{op}{val}",
        ))

    # 3. Percentages (e.g., 12%, 12.5 %, 12 percent, 12 percentage)
    pct_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)\b')
    for m in pct_pattern.finditer(text_lower):
        raw = m.group(0)
        val = float(m.group(1))
        results.append(ExtractedNumber(
            raw=raw,
            kind="percentage",
            canonical_val=val,
            text_representation=f"{val}%",
        ))

    # 4. Ranges (e.g., 10-20, 10 to 20, 10–20)
    range_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:-|–|—|\bto\b)\s*(\d+(?:\.\d+)?)\b')
    for m in range_pattern.finditer(text_lower):
        raw = m.group(0)
        start, end = float(m.group(1)), float(m.group(2))
        results.append(ExtractedNumber(
            raw=raw,
            kind="range",
            canonical_val=(start, end),
            text_representation=f"{start}-{end}",
        ))

    # 5. Standalone integers and decimals (with or without comma formatting)
    num_pattern = re.compile(r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b')
    for m in num_pattern.finditer(text_lower):
        raw = m.group(0)
        val = float(_clean_commas(raw))
        already_captured = any(
            (isinstance(r.canonical_val, float) and abs(r.canonical_val - val) < 1e-6)
            or (isinstance(r.canonical_val, tuple) and val in r.canonical_val)
            for r in results
        )
        if not already_captured:
            results.append(ExtractedNumber(
                raw=raw,
                kind="number",
                canonical_val=val,
                text_representation=str(val if val % 1 != 0 else int(val)),
            ))

    return results


def _numbers_match(n1: ExtractedNumber, n2: ExtractedNumber) -> bool:
    """Checks whether two extracted numbers match, handling formatting equivalences."""
    if n1.kind == "range" and n2.kind == "range":
        return n1.canonical_val == n2.canonical_val
    if n1.kind == "percentage" and n2.kind == "percentage":
        return abs(n1.canonical_val - n2.canonical_val) < 1e-4  # type: ignore
    if isinstance(n1.canonical_val, float) and isinstance(n2.canonical_val, float):
        return abs(n1.canonical_val - n2.canonical_val) < 1e-4
    return False


def check_numeric_support(claim: Any, passages: Any) -> NumericSupportResult:
    """Validates whether numbers in a claim are factually supported by cited passages."""
    claim_text, cited_ids = normalize_claim(claim)
    passage_map = normalize_passages(passages)

    claim_nums = extract_numbers(claim_text)
    claim_num_reprs = [n.text_representation for n in claim_nums]

    if not claim_nums:
        return NumericSupportResult(
            is_supported=True,
            status="NO_NUMBERS",
            claim_numbers=[],
            evidence_numbers=[],
            matched_numbers=[],
            unmatched_numbers=[],
            details="No numeric values present in the claim.",
        )

    cited_sentences = [passage_map[cid] for cid in cited_ids if cid in passage_map]
    if not cited_sentences:
        return NumericSupportResult(
            is_supported=False,
            status="NO_EVIDENCE",
            claim_numbers=claim_num_reprs,
            evidence_numbers=[],
            matched_numbers=[],
            unmatched_numbers=claim_num_reprs,
            details="Claim cited no existing passage IDs to verify numbers against.",
        )

    combined_evidence_text = " ".join(cited_sentences)
    evidence_nums = extract_numbers(combined_evidence_text)
    evidence_num_reprs = [n.text_representation for n in evidence_nums]

    matched: list[str] = []
    unmatched: list[str] = []

    for cn in claim_nums:
        if any(_numbers_match(cn, en) for en in evidence_nums):
            matched.append(cn.text_representation)
        else:
            unmatched.append(cn.text_representation)

    if not unmatched:
        return NumericSupportResult(
            is_supported=True,
            status="SUPPORTED",
            claim_numbers=claim_num_reprs,
            evidence_numbers=evidence_num_reprs,
            matched_numbers=matched,
            unmatched_numbers=[],
            details="All numeric values in claim matched the cited evidence.",
        )
    elif matched and unmatched:
        return NumericSupportResult(
            is_supported=False,
            status="MISMATCH",
            claim_numbers=claim_num_reprs,
            evidence_numbers=evidence_num_reprs,
            matched_numbers=matched,
            unmatched_numbers=unmatched,
            details=f"Partial number match: {unmatched} not found in cited evidence.",
        )
    else:
        return NumericSupportResult(
            is_supported=False,
            status="UNSUPPORTED",
            claim_numbers=claim_num_reprs,
            evidence_numbers=evidence_num_reprs,
            matched_numbers=[],
            unmatched_numbers=unmatched,
            details="None of the claim's numeric values appear in cited evidence.",
        )