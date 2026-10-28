"""Sentence tagger and numeric entity detector for provenance tracking."""

import re
from typing import List
from app.models import SentenceSpan


NUMERIC_REGEX = re.compile(
    r"(?:\b\d+(?:\.\d+)?%|\b\d+(?:,\d+)*(?:\.\d+)?\b|\bp\s*[<>=]\s*0?\.\d+|\b[+-]?\d+(?:\.\d+)?\s*(?:pp|percentage points?))",
    re.IGNORECASE,
)


def split_into_sentences(text: str) -> List[str]:
    """Splits text into discrete sentences while respecting abbreviations."""
    # Clean whitespace
    cleaned = re.sub(r"\s+", " ", text.strip())
    # Regex split on period/exclamation/question mark followed by space and uppercase
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned)
    return [s.strip() for s in sentences if s.strip()]


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
        if any(w in lower_s for w in ["we evaluated", "we tested", "methods", "cohort", "enrolled", "dataset"]):
            category = "Methods"
        elif any(w in lower_s for w in ["result", "improved", "increased", "decreased", "higher", "lower", "yielded"]):
            category = "Results"
        elif any(w in lower_s for w in ["conclude", "in summary", "limitation", "further", "discuss"]):
            category = "Conclusion / Discussion"
        elif idx == 1 or "background" in lower_s:
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
