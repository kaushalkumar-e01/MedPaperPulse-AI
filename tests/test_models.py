"""Unit tests for shared Pydantic data contracts (app/models.py)."""

import pytest
from pydantic import ValidationError

from app.models import (
    Passage,
    PaperRecord,
    Claim,
    SummaryResult,
    SummaryLength,
    ExplanationLevel,
    SourceType,
    MISSING_INFO_INDICATOR,
)


def test_passage_valid():
    p = Passage(id="S1", text="This is a test sentence.", section="BACKGROUND")
    assert p.id == "S1"
    assert p.text == "This is a test sentence."
    assert p.section == "BACKGROUND"


def test_passage_empty_id_rejected():
    with pytest.raises(ValidationError):
        Passage(id="", text="Some sentence.", section="METHODS")

    with pytest.raises(ValidationError):
        Passage(id="   ", text="Some sentence.", section="METHODS")


def test_passage_empty_text_rejected():
    with pytest.raises(ValidationError):
        Passage(id="S1", text="", section="METHODS")

    with pytest.raises(ValidationError):
        Passage(id="S1", text="   ", section="METHODS")


def test_passage_section_normalization():
    p = Passage(id="S1", text="Sentence.", section="results")
    assert p.section == "RESULTS"

    p2 = Passage(id="S2", text="Sentence.")
    assert p2.section == "UNSPECIFIED"


def test_paper_record_valid():
    record = PaperRecord(
        pmid="12345678",
        doi="10.1000/xyz123",
        title="Efficacy of Drug X in Oncology",
        authors=["Alice Smith", "Bob Jones"],
        journal="Journal of Clinical Oncology",
        pub_date="2024-01-15",
        pub_types=["Clinical Trial"],
        url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        passages=[
            Passage(id="S1", text="Drug X was tested.", section="METHODS"),
            Passage(id="S2", text="Survival increased by 20%.", section="RESULTS"),
        ],
        source_type="abstract",
    )
    assert record.pmid == "12345678"
    assert len(record.passages) == 2
    assert record.source_type == "abstract"


def test_paper_record_empty_title_rejected():
    with pytest.raises(ValidationError):
        PaperRecord(title="")

    with pytest.raises(ValidationError):
        PaperRecord(title="   ")


def test_claim_valid_and_self_validation_prevention():
    # LLM cannot self-validate: default is False
    c = Claim(text="Drug X improved progression-free survival (HR=0.75).", supported_by=["S2"])
    assert c.valid is False
    assert c.supported_by == ["S2"]

    # Even if instantiated without explicit valid, it remains False
    c2 = Claim(text="Another claim", supported_by=["S1", "[S3]"])
    assert c2.valid is False
    assert c2.supported_by == ["S1", "S3"]  # Strips brackets cleanly


def test_claim_empty_text_rejected():
    with pytest.raises(ValidationError):
        Claim(text="", supported_by=["S1"])


def test_summary_result_valid():
    res = SummaryResult(
        pmid="12345678",
        title="Efficacy of Drug X",
        pico={
            "population": "Adults with Stage III melanoma",
            "intervention": "Drug X 100mg daily",
            "comparison": "Standard chemotherapy",
            "outcome": "Overall survival at 2 years",
        },
        design="Phase 3 Double-Blind Randomized Controlled Trial",
        objective=Claim(text="To evaluate Drug X versus standard chemotherapy.", supported_by=["S1"]),
        findings=[
            Claim(text="Drug X improved median survival by 4.2 months (p=0.01).", supported_by=["S2"]),
        ],
        conclusion=Claim(text="Drug X showed superior overall survival.", supported_by=["S3"]),
        limitations=[
            Claim(text="Study was conducted at a single geographical region.", supported_by=["S4"]),
        ],
        glossary={"HR": "Hazard Ratio", "OS": "Overall Survival"},
        coverage=0.85,
        summary_length=SummaryLength.DETAILED,
        explanation_level=ExplanationLevel.RESEARCHER,
        prompt_version="v1",
    )
    assert res.pmid == "12345678"
    assert res.coverage == 0.85
    assert res.summary_length == SummaryLength.DETAILED
    assert res.explanation_level == ExplanationLevel.RESEARCHER
    assert res.findings[0].supported_by == ["S2"]


def test_summary_result_defaults_and_missing_pico():
    res = SummaryResult(
        objective=Claim(text="Study objective.", supported_by=["S1"]),
        conclusion=Claim(text="Study conclusion.", supported_by=["S2"]),
    )
    # Check default PICO fills missing information indicators
    assert res.pico["population"] == MISSING_INFO_INDICATOR
    assert res.pico["intervention"] == MISSING_INFO_INDICATOR
    assert res.pico["comparison"] == MISSING_INFO_INDICATOR
    assert res.pico["outcome"] == MISSING_INFO_INDICATOR
    assert res.design == MISSING_INFO_INDICATOR
    assert res.coverage == 0.0
    assert res.summary_length == SummaryLength.STANDARD
    assert res.explanation_level == ExplanationLevel.STUDENT
    assert res.prompt_version == "v1"


def test_summary_result_json_roundtrip():
    res = SummaryResult(
        pmid="999",
        pico={"population": "Cohort of 500 patients"},
        objective=Claim(text="Assess safety.", supported_by=["S1"]),
        conclusion=Claim(text="Safe profile.", supported_by=["S2"]),
    )
    json_str = res.model_dump_json()
    assert "Cohort of 500 patients" in json_str

    deserialized = SummaryResult.model_validate_json(json_str)
    assert deserialized.pmid == "999"
    assert deserialized.pico["population"] == "Cohort of 500 patients"
    assert deserialized.pico["intervention"] == MISSING_INFO_INDICATOR
    assert deserialized.objective.text == "Assess safety."


def test_enums_validation():
    assert SummaryLength("short") == SummaryLength.SHORT
    assert ExplanationLevel("beginner") == ExplanationLevel.BEGINNER
    assert SourceType("pasted") == SourceType.PASTED

    with pytest.raises(ValueError):
        SummaryLength("ultra-long")

    with pytest.raises(ValueError):
        ExplanationLevel("expert_phd")

