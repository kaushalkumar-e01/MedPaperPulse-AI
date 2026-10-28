"""AI Summarization package for MedPaperPulse-AI / MedLit Explorer."""

from app.ai.summarizer import (
    BaseLLMClient,
    ConfigurationError,
    MockLLMClient,
    OpenAICompatibleClient,
    OutputParsingError,
    PROMPT_VERSION,
    ProviderAPIError,
    RateLimitError,
    SummarizerError,
    clean_json_text,
    format_passages,
    load_prompt_templates,
    summarize_paper,
)

__all__ = [
    "summarize_paper",
    "PROMPT_VERSION",
    "SummarizerError",
    "ConfigurationError",
    "ProviderAPIError",
    "RateLimitError",
    "OutputParsingError",
    "BaseLLMClient",
    "OpenAICompatibleClient",
    "MockLLMClient",
    "load_prompt_templates",
    "format_passages",
    "clean_json_text",
]

