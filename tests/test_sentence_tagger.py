"""Unit tests for sentence segmentation and sentence-ID assignment."""

import pytest
from app.ingestion.sentence_tagger import split_into_sentences, tag_sentences, NUMERIC_REGEX


def test_split_into_sentences_basic():
    text = "Background: Heart failure is common. Methods: We studied 4,000 patients. Results: Mortality dropped."
    s = split_into_sentences(text)
    assert len(s) == 3
    assert s[0] == "Background: Heart failure is common."
    assert s[1] == "Methods: We studied 4,000 patients."
    assert s[2] == "Results: Mortality dropped."


def test_split_into_sentences_abbreviations():
    text = "As shown by Smith et al. Patients who received drug X showed improvement vs. Placebo at week 12."
    s = split_into_sentences(text)
    # 'et al.' and 'vs.' should not cause premature sentence fragmentation
    assert len(s) == 1
    assert "Smith et al." in s[0]
    assert "vs. Placebo" in s[0]


def test_tag_sentences_stable_ids():
    text = "First sentence here. Second sentence with 50% efficacy. Third conclusion sentence."
    spans = tag_sentences(text)
    assert len(spans) == 3

    assert spans[0].tag == "[S1]"
    assert spans[0].index == 1
    assert spans[0].text == "First sentence here."

    assert spans[1].tag == "[S2]"
    assert spans[1].index == 2
    assert spans[1].text == "Second sentence with 50% efficacy."
    assert "50%" in spans[1].numeric_entities

    assert spans[2].tag == "[S3]"
    assert spans[2].index == 3
    assert spans[2].category == "Conclusion / Discussion"


def test_numeric_entity_extraction():
    text = "At week 72, the primary endpoint had p < 0.001 and weight was -20.9% (delta of 17.8 pp)."
    numbers = NUMERIC_REGEX.findall(text)
    assert any("72" in n for n in numbers)
    assert any("p < 0.001" in n or "< 0.001" in n for n in numbers)
    assert any("20.9%" in n for n in numbers)
    assert any("17.8 pp" in n or "pp" in n for n in numbers)


def test_tag_sentences_empty():
    assert tag_sentences("") == []
    assert tag_sentences("   ") == []
