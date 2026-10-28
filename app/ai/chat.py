"""Grounded Q&A chat engine answering medical questions exclusively from paper text."""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
from app.citations.validator import normalize_passages, validate_citation

ABSTAIN_RESPONSE = "This information was not reported in the supplied paper text."

_STOPWORDS = {
    "a", "an", "the", "in", "on", "of", "for", "to", "at", "by", "from",
    "with", "is", "was", "are", "were", "what", "which", "how", "did",
    "does", "do", "study", "paper", "patient", "patients"
}


@dataclass
class ChatResponse:
    """Structured response for grounded chat."""
    answer: str
    evidence_passage_ids: list[str]
    is_grounded: bool
    status: str  # "GROUNDED", "NOT_REPORTED", "NO_PASSAGES"


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', text.lower()) if w not in _STOPWORDS]


def answer_question(question: str, passages: Any) -> ChatResponse:
    """Answers user queries strictly grounded in supplied paper passages without hallucinations."""
    if not question or not question.strip():
        return ChatResponse(
            answer=ABSTAIN_RESPONSE,
            evidence_passage_ids=[],
            is_grounded=False,
            status="NOT_REPORTED",
        )

    passage_map = normalize_passages(passages)
    if not passage_map:
        return ChatResponse(
            answer=ABSTAIN_RESPONSE,
            evidence_passage_ids=[],
            is_grounded=False,
            status="NO_PASSAGES",
        )

    query_tokens = _tokenize(question)
    if not query_tokens:
        return ChatResponse(
            answer=ABSTAIN_RESPONSE,
            evidence_passage_ids=[],
            is_grounded=False,
            status="NOT_REPORTED",
        )

    scored_passages: list[tuple[str, str, float]] = []

    for pid, ptext in passage_map.items():
        p_tokens = set(_tokenize(ptext))
        matched = set(query_tokens) & p_tokens
        if matched:
            score = len(matched) / len(set(query_tokens))
            scored_passages.append((pid, ptext, score))

    if not scored_passages:
        return ChatResponse(
            answer=ABSTAIN_RESPONSE,
            evidence_passage_ids=[],
            is_grounded=False,
            status="NOT_REPORTED",
        )

    scored_passages.sort(key=lambda x: x[2], reverse=True)
    best_id, best_text, best_score = scored_passages[0]

    if best_score < 0.3:
        return ChatResponse(
            answer=ABSTAIN_RESPONSE,
            evidence_passage_ids=[],
            is_grounded=False,
            status="NOT_REPORTED",
        )

    validation = validate_citation(
        {"claim": best_text, "citations": [best_id]},
        passage_map,
    )

    if not validation.is_valid:
        return ChatResponse(
            answer=ABSTAIN_RESPONSE,
            evidence_passage_ids=[],
            is_grounded=False,
            status="NOT_REPORTED",
        )

    return ChatResponse(
        answer=best_text,
        evidence_passage_ids=[best_id],
        is_grounded=True,
        status="GROUNDED",
    )