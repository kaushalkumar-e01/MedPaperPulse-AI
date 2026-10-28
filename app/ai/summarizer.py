"""AI Summarization Service for MedPaperPulse-AI / MedLit Explorer.

Provides evidence-grounded clinical abstract summarization with strict
PICO extraction, citation tracking, and structured output validation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from app.models import (
    Claim,
    ExplanationLevel,
    PaperRecord,
    Passage,
    SummaryLength,
    SummaryResult,
    MISSING_INFO_INDICATOR,
)

logger = logging.getLogger(__name__)

# Active deterministic prompt version
PROMPT_VERSION = "v1"

# Default prompt templates path
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


# ============================================================================
# Exceptions
# ============================================================================


class SummarizerError(Exception):
    """Base exception for all summarization errors."""

    pass


class ConfigurationError(SummarizerError):
    """Raised when required API credentials or provider endpoints are missing."""

    pass


class ProviderAPIError(SummarizerError):
    """Raised when upstream LLM provider fails (HTTP errors, timeouts, connection issues)."""

    pass


class RateLimitError(ProviderAPIError):
    """Raised when upstream LLM provider returns HTTP 429 (rate limit exceeded)."""

    pass


class OutputParsingError(SummarizerError):
    """Raised when model output fails JSON parsing or Pydantic validation after retries."""

    pass


# ============================================================================
# LLM Client Interfaces & Implementations
# ============================================================================


class BaseLLMClient(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generates completion text given system and user prompts.

        Args:
            system_prompt: System prompt containing grounding rules.
            user_prompt: User prompt containing passages and synthesis request.

        Returns:
            Raw string completion from the model.
        """
        pass


class OpenAICompatibleClient(BaseLLMClient):
    """Production client for OpenAI-compatible APIs (OpenAI, OpenRouter, Groq, Ollama, vLLM).

    Configuration is read lazily at runtime from environment variables:
    - LLM_API_KEY or OPENAI_API_KEY
    - MODEL_NAME (default: 'gpt-4o-mini')
    - LLM_BASE_URL or OPENAI_BASE_URL (default: 'https://api.openai.com/v1')
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._base_url = base_url
        self.timeout = timeout

    @property
    def api_key(self) -> str:
        key = (
            self._api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not key or not key.strip():
            raise ConfigurationError(
                "LLM API key is missing. Please set LLM_API_KEY or OPENAI_API_KEY in your environment."
            )
        return key.strip()

    @property
    def model_name(self) -> str:
        return (
            self._model_name
            or os.getenv("MODEL_NAME")
            or os.getenv("OPENAI_MODEL_NAME")
            or "gpt-4o-mini"
        )

    @property
    def base_url(self) -> str:
        url = (
            self._base_url
            or os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        return url.rstrip("/")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=self.timeout
            )
        except requests.exceptions.Timeout as e:
            raise ProviderAPIError(f"LLM provider request timed out after {self.timeout}s.") from e
        except requests.exceptions.RequestException as e:
            raise ProviderAPIError(f"LLM network communication error: {type(e).__name__}") from e

        if response.status_code == 429:
            raise RateLimitError("LLM rate limit reached (HTTP 429). Please retry later.")
        elif response.status_code in (401, 403):
            raise ConfigurationError("LLM authentication failed. Please verify your API key.")
        elif response.status_code != 200:
            raise ProviderAPIError(
                f"LLM provider returned error status {response.status_code}."
            )

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderAPIError(
                "Invalid response structure received from LLM provider."
            ) from e


class MockLLMClient(BaseLLMClient):
    """Mock client for deterministic unit testing without external API calls."""

    def __init__(self, response_generator=None) -> None:
        self.call_history: List[Dict[str, str]] = []
        self.response_generator = response_generator

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.call_history.append({"system": system_prompt, "user": user_prompt})
        if callable(self.response_generator):
            return self.response_generator(system_prompt, user_prompt)
        elif isinstance(self.response_generator, str):
            return self.response_generator
        # Default minimal valid response fixture
        return json.dumps({
            "pico": {
                "population": "Adult oncology patients",
                "intervention": "Targeted immunotherapy",
                "comparison": "Placebo",
                "outcome": "Overall survival",
            },
            "design": "Randomized Controlled Trial",
            "objective": {"text": "Evaluate targeted immunotherapy.", "supported_by": ["S1"]},
            "findings": [
                {"text": "Median survival increased by 4 months.", "supported_by": ["S2"]},
            ],
            "conclusion": {"text": "Immunotherapy was well-tolerated and effective.", "supported_by": ["S3"]},
            "limitations": [
                {"text": "Small sample size from single center.", "supported_by": ["S4"]},
            ],
            "glossary": {"OS": "Overall Survival"},
        })


# ============================================================================
# Prompt Loading & Formatting
# ============================================================================


def load_prompt_templates(prompts_dir: Optional[Path] = None) -> tuple[str, str]:
    """Loads system and summary prompt files from the prompts directory.

    Args:
        prompts_dir: Optional path override for directory containing prompt files.

    Returns:
        Tuple of (system_prompt_text, summary_prompt_text).
    """
    directory = prompts_dir or PROMPTS_DIR
    sys_path = directory / "system_prompt.txt"
    sum_path = directory / "summary_prompt.txt"

    if not sys_path.is_file():
        raise ConfigurationError(f"System prompt template missing at: {sys_path}")
    if not sum_path.is_file():
        raise ConfigurationError(f"Summary prompt template missing at: {sum_path}")

    return (
        sys_path.read_text(encoding="utf-8"),
        sum_path.read_text(encoding="utf-8"),
    )


def format_passages(passages: List[Passage]) -> str:
    """Formats PaperRecord passages into sentence-tagged source lines.

    Example:
        [S1] (METHODS): We evaluated a hybrid architecture...
    """
    if not passages:
        return "[S1] (UNSPECIFIED): No source passages provided."

    formatted_lines = []
    for p in passages:
        section = p.section if p.section else "UNSPECIFIED"
        formatted_lines.append(f"[{p.id}] ({section}): {p.text}")
    return "\n".join(formatted_lines)


def clean_json_text(raw_text: str) -> str:
    """Extracts raw JSON content, removing any markdown code blocks."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


# ============================================================================
# Core Summarization Pipeline
# ============================================================================


def _parse_and_validate_summary(
    raw_response: str,
    paper: PaperRecord,
    length: SummaryLength,
    level: ExplanationLevel,
    prompt_version: str = PROMPT_VERSION,
) -> SummaryResult:
    """Parses JSON text and validates into a SummaryResult model.

    Enforces that all generated claims have `valid=False` (preventing LLM self-validation)
    and attaches paper metadata.
    """
    cleaned = clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise OutputParsingError(f"Model output is not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise OutputParsingError("Model output JSON is not a key-value object.")

    # Invariant: force claims to valid=False regardless of LLM output
    for key in ("objective", "conclusion"):
        if key in data and isinstance(data[key], dict):
            data[key]["valid"] = False

    for list_key in ("findings", "limitations"):
        if list_key in data and isinstance(data[list_key], list):
            for item in data[list_key]:
                if isinstance(item, dict):
                    item["valid"] = False

    # Attach metadata
    data["pmid"] = paper.pmid
    data["title"] = paper.title
    data["summary_length"] = length.value
    data["explanation_level"] = level.value
    data["prompt_version"] = prompt_version
    # Coverage must be authoritatively calculated by Person 4's citation engine
    data["coverage"] = 0.0

    try:
        return SummaryResult.model_validate(data)
    except Exception as e:
        raise OutputParsingError(f"Model output schema validation failed: {e}") from e


def summarize_paper(
    paper: PaperRecord,
    length: Union[str, SummaryLength] = SummaryLength.STANDARD,
    level: Union[str, ExplanationLevel] = ExplanationLevel.STUDENT,
    client: Optional[BaseLLMClient] = None,
    prompts_dir: Optional[Path] = None,
    max_retries: int = 1,
) -> SummaryResult:
    """Summarizes a PaperRecord into an evidence-grounded SummaryResult.

    Public interface for Person 1 module. Consumed by Person 3 (Streamlit UI),
    Person 4 (Citation validator), and Person 5 (Evaluation).

    Args:
        paper: Validated PaperRecord containing metadata and passages.
        length: Summary length ('short', 'standard', 'detailed').
        level: Explanation level ('beginner', 'student', 'researcher').
        client: Optional injected LLM client. Defaults to OpenAICompatibleClient.
        prompts_dir: Optional directory override for prompt templates.
        max_retries: Maximum number of parsing retry attempts (default 1, bounded).

    Returns:
        Validated SummaryResult conforming to shared contract.

    Raises:
        ConfigurationError: If API credentials or prompt templates are missing.
        ProviderAPIError: If upstream LLM service encounters network or status errors.
        RateLimitError: If LLM provider reports rate limits.
        OutputParsingError: If model response cannot be parsed into a valid SummaryResult.
    """
    if not isinstance(paper, PaperRecord):
        raise ValueError(f"Expected PaperRecord instance, got {type(paper).__name__}")

    # Normalize enums
    if isinstance(length, str):
        length = SummaryLength(length.lower().strip())
    if isinstance(level, str):
        level = ExplanationLevel(level.lower().strip())

    # Initialize client lazily if not provided
    llm_client = client or OpenAICompatibleClient()

    # Load prompt templates
    system_template, summary_template = load_prompt_templates(prompts_dir)

    # Format passages
    passages_block = format_passages(paper.passages)

    # Construct user prompt
    user_prompt = summary_template.format(
        summary_length=length.value,
        explanation_level=level.value,
        prompt_version=PROMPT_VERSION,
        title=paper.title or "Untitled Publication",
        pmid=paper.pmid or MISSING_INFO_INDICATOR,
        passages_block=passages_block,
    )

    # Attempt generation with bounded retry on parsing failure
    attempts = 0
    last_error: Optional[Exception] = None
    current_user_prompt = user_prompt

    while attempts <= max_retries:
        raw_response = llm_client.generate(system_template, current_user_prompt)
        try:
            return _parse_and_validate_summary(
                raw_response=raw_response,
                paper=paper,
                length=length,
                level=level,
                prompt_version=PROMPT_VERSION,
            )
        except OutputParsingError as err:
            last_error = err
            attempts += 1
            if attempts <= max_retries:
                logger.warning(
                    "Model output parsing failed (attempt %d/%d). Retrying with correction prompt...",
                    attempts,
                    max_retries,
                )
                current_user_prompt = (
                    f"{user_prompt}\n\n"
                    f"CRITICAL CORRECTION REQUIRED:\n"
                    f"Your previous response failed validation with error: {str(err)}\n"
                    f"Please output ONLY a raw valid JSON object exactly conforming to the schema."
                )

    raise OutputParsingError(
        f"Failed to obtain valid structured output after {max_retries + 1} attempt(s). Last error: {last_error}"
    ) from last_error

