"""Sentence tagger and numeric entity detector for provenance tracking."""

from __future__ import annotations

import re
from typing import List
from app.models import SentenceSpan


# Specific patterns (pp, p-value, percentage) must precede the generic number pattern
NUMERIC_REGEX = re.compile(
    r"(?:\b[+-]?\d+(?:\.\d+)?\s*(?:pp|percentage points?)\b|\bp\s*[<>=≤≥]\s*0?\.\d+|\b[+-]?\d+(?:\.\d+)?%|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b)",
    re.IGNORECASE,
)

# Common scientific, academic, and clinical abbreviations
_PROTECTED_ABBREVIATIONS = [
    r"\bet al\.",
    r"\be\.g\.",
    r"\bi\.e\.",
    r"\bvs\.",
    r"\bFig\.",
    r"\bFigs\.",
    r"\bTab\.",
    r"\bRef\.",
    r"\bRefs\.",
    r"\bDr\.",
    r"\bProf\.",
    r"\bapprox\.",
    r"\bdept\.",
    r"\bno\.",
    r"\bnos\.",
    r"\bvol\.",
    r"\bvols\.",
    r"\b[A-Z]\.",  # Single-letter initials like 'A. Smith'
]


def split_into_sentences(text: str) -> List[str]:
    """Splits text into discrete sentences while respecting abbreviations and initialisms."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []

    # Mask periods in protected abbreviations using temporary token
    masked = cleaned
    for pattern in _PROTECTED_ABBREVIATIONS:
        def _mask(m: re.Match) -> str:
            return m.group(0).replace(".", "__DOT__")
        masked = re.sub(pattern, _mask, masked, flags=re.IGNORECASE)

    # Regex split on terminal punctuation followed by space and capital letter/number
    raw_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", masked)

    # Restore periods and strip
    sentences = [s.replace("__DOT__", ".").strip() for s in raw_splits if s.strip()]
    return sentences


def tag_sentences(text: str) -> List[SentenceSpan]:
    """Tags sentences sequentially with [S1], [S2]... and identifies numeric entities."""
    raw_sentences = split_into_sentences(text)
    spans: List[SentenceSpan] = []

    for idx, s in enumerate(raw_sentences, start=1):
        tag = f"[S{idx}]"
        # Find numeric entities
        numbers = NUMERIC_REGEX.findall(s)

        # Classify rough category based on keywords or position
        lower_s = s.lower()
        if any(w in lower_s for w in ["conclude", "conclusion", "in summary", "limitation", "further", "discuss", "implications"]):
            category = "Conclusion / Discussion"
        elif any(w in lower_s for w in ["result", "improved", "increased", "decreased", "higher", "lower", "yielded", "efficacy", "reduction"]):
            category = "Results"
        elif any(w in lower_s for w in ["we evaluated", "we tested", "methods", "cohort", "enrolled", "dataset", "randomized", "assigned"]):
            category = "Methods"
        elif idx == 1 or "background" in lower_s or "objective" in lower_s:
            category = "Background"
        else:
            category = "Results" if numbers else "Methods"

        spans.append(
            SentenceSpan(
                tag=tag,
                index=idx,
                text=s,
                category=category,
                numeric_entities=numbers,
            )
        )

    return spans
