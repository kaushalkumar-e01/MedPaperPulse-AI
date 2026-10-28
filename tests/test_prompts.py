"""Unit tests for prompt templates and prompt versioning (prompts/ and app/ai/summarizer.py)."""

from pathlib import Path
import pytest

from app.models import SummaryLength, ExplanationLevel, MISSING_INFO_INDICATOR


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def test_system_prompt_file_exists_and_loads():
    sys_file = PROMPTS_DIR / "system_prompt.txt"
    assert sys_file.is_file(), f"Missing system prompt file at {sys_file}"
    content = sys_file.read_text(encoding="utf-8")
    assert len(content) > 100


def test_summary_prompt_file_exists_and_loads():
    summary_file = PROMPTS_DIR / "summary_prompt.txt"
    assert summary_file.is_file(), f"Missing summary prompt file at {summary_file}"
    content = summary_file.read_text(encoding="utf-8")
    assert len(content) > 100


def test_system_prompt_contains_mandatory_grounding_rules():
    sys_prompt = (PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")

    # Source grounding
    assert "ONLY source of evidence" in sys_prompt or "only source of evidence" in sys_prompt.lower()
    assert "NEVER invent" in sys_prompt or "never invent" in sys_prompt.lower()

    # Exact missing info phrase
    assert MISSING_INFO_INDICATOR in sys_prompt
    assert "Not reported in the abstract." in sys_prompt

    # Citation requirement
    assert "supported_by" in sys_prompt
    assert "passage IDs" in sys_prompt or "passage ID" in sys_prompt.lower()

    # Injection defense
    assert "untrusted" in sys_prompt.lower()
    assert "ignore previous instructions" in sys_prompt.lower()


def test_prompt_supports_all_lengths_and_levels():
    sys_prompt = (PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")
    summary_prompt = (PROMPTS_DIR / "summary_prompt.txt").read_text(encoding="utf-8")

    # All lengths present in system guidance
    for length in SummaryLength:
        assert length.value in sys_prompt

    # All explanation levels present in system guidance
    for level in ExplanationLevel:
        assert level.value in sys_prompt

    # Summary prompt formatting placeholders
    assert "{summary_length}" in summary_prompt
    assert "{explanation_level}" in summary_prompt
    assert "{passages_block}" in summary_prompt
    assert "{title}" in summary_prompt
    assert "{pmid}" in summary_prompt


def test_changelog_documented_and_version_consistent():
    changelog = (PROMPTS_DIR / "changelog.md").read_text(encoding="utf-8")
    assert "v1" in changelog
    assert "Active Version" in changelog
    assert "Changes Introduced" in changelog
    assert "Evaluation" in changelog

