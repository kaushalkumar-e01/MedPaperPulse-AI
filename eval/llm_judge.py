"""LLM-as-Judge Evaluation Tool for MedPaperPulse-AI.

Assesses generated medical summaries across 4 dimensions on a 1-5 rubric:
1. Factual Consistency (preservation of facts, numbers, uncertainty, no hallucination)
2. Completeness (PICO, design, key findings, conclusions, limitations)
3. Readability (structure, tone, clarity for target audience)
4. Evidence Support (tight alignment between claims and cited source sentences)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import PaperRecord, SummaryResult
from app.ai.summarizer import BaseLLMClient, OpenAICompatibleClient, clean_json_text

logger = logging.getLogger(__name__)

JUDGE_RUBRIC_TEXT = """
You are an expert clinical epidemiologist and medical evaluation judge.
Your task is to evaluate an AI-generated medical summary against the original source abstract.

Score the summary across 4 dimensions on a 1 to 5 scale:

1. FACTUAL CONSISTENCY (1-5):
   - Score 5: Absolute fidelity to source abstract. All reported numbers, effect sizes, p-values, and uncertainty qualifiers ("may", "might", "suggests") are accurately preserved. No external clinical facts are imported.
   - Score 3: Mostly faithful to the abstract, but contains minor phrasing drift or slight overstatement of certainty (e.g., describing a correlation as near-causal).
   - Score 1: Major hallucination, contradiction of primary findings, fabricated statistics, or invented patient outcomes.

2. COMPLETENESS (1-5):
   - Score 5: Thoroughly addresses study objective, PICO framework, study design, primary quantitative results, authors' conclusion, and explicitly reported limitations (or honestly states "Not reported in the abstract.").
   - Score 3: Captures primary result and conclusion, but omits important PICO elements, study design, or limitations.
   - Score 1: Incomplete or truncated; fails to state the primary findings or core objective.

3. READABILITY (1-5):
   - Score 5: Exceptionally well-structured, clear, concise, fluent scientific prose, appropriate for clinical literature review.
   - Score 3: Understandable and coherent, but suffers from awkward phrasing, redundancy, or disjointed transitions.
   - Score 1: Incoherent, heavily repetitive, or severely unreadable formatting.

4. EVIDENCE SUPPORT (1-5):
   - Score 5: Every factual claim cites valid source passage IDs (e.g. [S1], [S2]) that directly and strictly justify the statement.
   - Score 3: Most claims are linked to passages, but some citations are loose, incomplete, or cite background sentences rather than direct results.
   - Score 1: Citations are largely missing, cite irrelevant sentences, or reference fabricated/non-existent passage IDs.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact schema:
{
  "factual_consistency": 5,
  "completeness": 5,
  "readability": 5,
  "evidence_support": 5,
  "overall_score": 5.0,
  "explanation": "Detailed explanation justifying the assigned scores...",
  "unsupported_claims": []
}
"""


class MockJudgeClient(BaseLLMClient):
    """Deterministic mock client for testing LLM-as-judge without API calls."""

    def __init__(self, scores: Optional[Dict[str, int]] = None) -> None:
        self.scores = scores or {
            "factual_consistency": 5,
            "completeness": 5,
            "readability": 5,
            "evidence_support": 5,
        }

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        overall = sum(self.scores.values()) / len(self.scores)
        return json.dumps({
            "factual_consistency": self.scores["factual_consistency"],
            "completeness": self.scores["completeness"],
            "readability": self.scores["readability"],
            "evidence_support": self.scores["evidence_support"],
            "overall_score": round(overall, 2),
            "explanation": "Mocked deterministic evaluation report.",
            "unsupported_claims": [],
        })


def format_judge_input(paper: PaperRecord, summary: SummaryResult) -> str:
    """Formats the paper passages and summary into a structured judge prompt."""
    source_lines = [f"[{p.id}] ({p.section}): {p.text}" for p in paper.passages]
    source_block = "\n".join(source_lines)

    summary_json = summary.model_dump_json(indent=2)

    return f"""
EVALUATION CASE:
Paper Title: {paper.title}
PMID: {paper.pmid or "N/A"}

ORIGINAL SOURCE ABSTRACT PASSAGES:
{source_block}

AI-GENERATED SUMMARY TO EVALUATE:
{summary_json}

Evaluate the summary above against the source passages according to the 1-5 rubric.
Return ONLY the raw JSON object.
"""


def evaluate_with_llm_judge(
    paper: PaperRecord,
    summary: SummaryResult,
    client: Optional[BaseLLMClient] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs LLM-as-judge evaluation on a single paper-summary pair.

    Returns:
        Structured evaluation dict with scores, explanation, and metadata.
    """
    judge_client = client or OpenAICompatibleClient(model_name=model_name or "gpt-4o-mini")
    user_prompt = format_judge_input(paper, summary)

    try:
        raw_response = judge_client.generate(JUDGE_RUBRIC_TEXT, user_prompt)
        cleaned = clean_json_text(raw_response)
        data = json.loads(cleaned)

        scores = [
            int(data.get("factual_consistency", 3)),
            int(data.get("completeness", 3)),
            int(data.get("readability", 3)),
            int(data.get("evidence_support", 3)),
        ]
        overall = round(sum(scores) / len(scores), 2)

        return {
            "judge_model": getattr(judge_client, "model_name", "mock-judge"),
            "evaluation_date": datetime.now().isoformat(),
            "factual_consistency": scores[0],
            "completeness": scores[1],
            "readability": scores[2],
            "evidence_support": scores[3],
            "overall_score": data.get("overall_score", overall),
            "explanation": data.get("explanation", "No explanation provided."),
            "unsupported_claims": data.get("unsupported_claims", []),
        }
    except Exception as e:
        logger.warning("LLM judge evaluation failed: %s", e)
        return {
            "judge_model": getattr(judge_client, "model_name", "unknown"),
            "evaluation_date": datetime.now().isoformat(),
            "error": str(e),
            "status": "failed",
        }
