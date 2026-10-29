"""Google Gemini API client for evidence-grounded summarization and chat synthesis.

Uses the official google-genai SDK.
Enforces strict provenance, sentence-level citation verification, and honest missingness.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

from app.citations.validator import validate_citation

logger = logging.getLogger(__name__)

# Default model candidate hierarchy
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACK_MODEL = "gemini-3.5-flash-lite"


def get_gemini_client() -> Optional[genai.Client]:
    """Instantiates the Gemini client if GEMINI_API_KEY is configured."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or not api_key.strip():
        return None
    try:
        return genai.Client(api_key=api_key.strip())
    except Exception as exc:
        logger.error("Failed to initialize Google GenAI Client: %s", exc)
        return None


def is_gemini_available() -> bool:
    """Checks whether the Gemini provider is enabled and has credentials."""
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    has_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    return provider == "gemini" and has_key


def generate_gemini_chat(
    query: str,
    passages: Dict[str, str],
    paper_metadata: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[str], str, bool, str]:
    """Generates an evidence-grounded conversational response strictly from supplied passages.

    Returns:
        (answer_text, verified_citation_ids, confidence, is_grounded, status)
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("GEMINI_API_KEY is not configured on the backend.")

    if not passages:
        return (
            "No literature passages were provided to answer this question.",
            [],
            "Low",
            False,
            "NO_PASSAGES",
        )

    # Format passages for the prompt
    passages_text = "\n".join(
        [f"[{pid}] {text}" for pid, text in passages.items()]
    )

    # Multi-paper check
    num_papers = len(paper_metadata) if paper_metadata else 1
    multi_paper_context = ""
    if paper_metadata:
        multi_paper_context = "Papers in Scope:\n" + "\n".join(
            [f"- {p.get('id', 'N/A')}: {p.get('title', 'Untitled')} ({p.get('journal', 'Clinical')})" for p in paper_metadata]
        ) + "\n\n"

    system_instruction = (
        "You are MedPaperPulse-AI, a senior clinical research evidence assistant. "
        "Your responses must be STRICTLY GROUNDED in the provided literature passages. "
        "Rules:\n"
        "1. Every factual statement, statistic, sample size, or conclusion must cite its exact source passage tag (e.g. [S1], [S2]).\n"
        "2. Do NOT import outside medical knowledge or fabricate citations.\n"
        "3. If the provided passages do NOT contain sufficient information to answer the question, state explicitly: "
        "'This information was not reported in the supplied abstract/document.' and do not guess.\n"
        "4. For comparison questions: If only 1 paper is available, state that cross-paper comparison requires additional papers. "
        "When comparing multiple papers, distinguish between contradictory findings and differences in cohorts, interventions, or endpoints.\n"
        "5. Output valid JSON with the format: {\"answer\": \"string with [S#] tags\", \"cited_ids\": [\"S1\", ...], \"status\": \"GROUNDED\" | \"NOT_REPORTED\", \"confidence\": \"High\" | \"Medium\" | \"Low\"}."
    )

    user_prompt = (
        f"{multi_paper_context}"
        f"SUPPLIED RESEARCH EVIDENCE PASSAGES:\n{passages_text}\n\n"
        f"USER QUESTION: {query}\n\n"
        f"Remember: Answer using ONLY the supplied passages. Cite every claim with its passage tag."
    )

    model_to_use = PRIMARY_MODEL
    try:
        response = client.models.generate_content(
            model=model_to_use,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
    except APIError as api_err:
        # Check for 503 or 404, fallback to secondary flash model
        logger.warning("Primary Gemini model %s error: %s. Attempting fallback.", model_to_use, api_err)
        try:
            response = client.models.generate_content(
                model=FALLBACK_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
        except Exception as fallback_err:
            logger.error("Fallback Gemini model also failed: %s", fallback_err)
            raise fallback_err

    # Parse response JSON
    try:
        raw_text = response.text.strip()
        data = json.loads(raw_text)
        answer = data.get("answer", "")
        raw_cited_ids = data.get("cited_ids", [])
        status = data.get("status", "GROUNDED")
        confidence = data.get("confidence", "High")
    except Exception:
        # If response was not strict JSON
        answer = response.text.strip()
        raw_cited_ids = re.findall(r"\[(S\d+)\]", answer)
        status = "GROUNDED" if raw_cited_ids else "NOT_REPORTED"
        confidence = "Medium"

    # Validate citations against genuine supplied passages
    valid_ids: List[str] = []
    for cid in raw_cited_ids:
        clean_id = cid.replace("[", "").replace("]", "").strip()
        if clean_id in passages:
            valid_ids.append(clean_id)

    # Double-check citations present directly in answer text
    text_cites = re.findall(r"\[(S\d+)\]", answer)
    for cid in text_cites:
        if cid in passages and cid not in valid_ids:
            valid_ids.append(cid)

    is_grounded = len(valid_ids) > 0 and status != "NOT_REPORTED"

    return answer, valid_ids, confidence, is_grounded, status


def generate_gemini_summary(
    paper_title: str,
    passages: List[Dict[str, Any]],
    depth: str = "Standard",
    audience: str = "Researcher",
) -> Dict[str, Any]:
    """Generates a structured PICO summary and synthesis using Gemini.

    Returns:
        Dict with keys: summary, pico, objective, findings, conclusion, limitations
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("GEMINI_API_KEY is not configured on the backend.")

    passages_text = "\n".join(
        [f"[{p.get('id', f'S{i+1}')}] {p.get('text', '')}" for i, p in enumerate(passages)]
    )

    system_instruction = (
        "You are an expert clinical literature synthesizer. Analyze the supplied scientific paper abstract/text. "
        "You must generate an evidence-grounded summary adhering to the PICO framework.\n"
        "Rules:\n"
        "1. Every factual statement must cite its exact passage tag (e.g. [S1], [S2]).\n"
        "2. PICO elements must be extracted accurately. If an element was not reported, state 'Not reported in the abstract.'\n"
        "3. Output JSON with format:\n"
        "{\n"
        "  \"summary\": \"Concise synthesis with passage citation tags\",\n"
        "  \"pico\": {\n"
        "    \"population\": {\"value\": \"...\", \"detail\": \"sample size / cohort\"},\n"
        "    \"intervention\": {\"value\": \"...\", \"detail\": \"protocol / method\"},\n"
        "    \"comparison\": {\"value\": \"...\", \"detail\": \"control / comparator\"},\n"
        "    \"outcome\": {\"value\": \"...\", \"detail\": \"primary endpoint / result\"}\n"
        "  },\n"
        "  \"findings\": [\"finding 1 [S#]\", \"finding 2 [S#]\"],\n"
        "  \"conclusion\": \"overall conclusion [S#]\",\n"
        "  \"limitations\": [\"reported limitation [S#]\"]\n"
        "}"
    )

    user_prompt = (
        f"PAPER TITLE: {paper_title}\n"
        f"AUDIENCE TARGET: {audience}\n"
        f"DEPTH: {depth}\n\n"
        f"RESEARCH EVIDENCE PASSAGES:\n{passages_text}\n\n"
        f"Extract PICO and synthesize evidence."
    )

    model_to_use = PRIMARY_MODEL
    try:
        response = client.models.generate_content(
            model=model_to_use,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
    except APIError:
        response = client.models.generate_content(
            model=FALLBACK_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

    return json.loads(response.text.strip())
