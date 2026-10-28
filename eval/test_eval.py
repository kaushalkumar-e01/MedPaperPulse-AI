"""Unit tests for Person 5 evaluation tools (eval/metrics.py, eval/llm_judge.py, eval/evaluate.py)."""

import json
from pathlib import Path
import pytest

from app.models import (
    PaperRecord,
    Passage,
    SummaryResult,
    Claim,
    SummaryLength,
    ExplanationLevel,
    MISSING_INFO_INDICATOR,
)
from eval.metrics import (
    extract_numeric_tokens,
    evaluate_numeric_faithfulness,
    evaluate_citation_resolution,
    evaluate_required_fields,
    evaluate_summary,
)
from eval.llm_judge import evaluate_with_llm_judge, MockJudgeClient
from eval.evaluate import load_dataset, record_to_paper, run_evaluation


@pytest.fixture
def sample_eval_paper() -> PaperRecord:
    return PaperRecord(
        pmid="11223344",
        title="Trial of Antihypertensive Drug Alpha",
        passages=[
            Passage(id="S1", section="METHODS", text="We randomized 1,200 patients to Drug Alpha 50 mg daily or placebo."),
            Passage(id="S2", section="RESULTS", text="Systolic blood pressure decreased by 14.2 mmHg with Drug Alpha versus 3.1 mmHg with placebo (P<0.001)."),
            Passage(id="S3", section="RESULTS", text="Major cardiovascular events occurred in 4.5% versus 8.0% (HR 0.55; 95% CI 0.41 to 0.74)."),
            Passage(id="S4", section="CONCLUSIONS", text="Drug Alpha significantly reduced blood pressure and cardiovascular events."),
        ],
    )


@pytest.fixture
def sample_eval_summary() -> SummaryResult:
    return SummaryResult(
        pmid="11223344",
        title="Trial of Antihypertensive Drug Alpha",
        pico={
            "population": "1,200 patients with hypertension",
            "intervention": "Drug Alpha 50 mg daily",
            "comparison": "Placebo",
            "outcome": "Blood pressure and cardiovascular events",
        },
        design="Randomized Controlled Trial",
        objective=Claim(text="Evaluate Drug Alpha 50 mg daily versus placebo.", supported_by=["S1"]),
        findings=[
            Claim(text="Systolic blood pressure decreased by 14.2 mmHg vs 3.1 mmHg (P<0.001).", supported_by=["S2"]),
            Claim(text="Major cardiovascular events occurred in 4.5% vs 8.0% (HR 0.55; 95% CI 0.41 to 0.74).", supported_by=["S3"]),
        ],
        conclusion=Claim(text="Drug Alpha significantly reduced blood pressure and cardiovascular events.", supported_by=["S4"]),
        limitations=[Claim(text=MISSING_INFO_INDICATOR, supported_by=[])],
        glossary={"BP": "Blood Pressure"},
    )


def test_extract_numeric_tokens():
    text = "In 1,200 patients, systolic BP dropped by 14.2 mmHg (P<0.001) with HR 0.55 (95% CI 0.41 to 0.74)."
    tokens = extract_numeric_tokens(text)
    assert any("1,200" in t or "1200" in t for t in tokens)
    assert any("14.2" in t for t in tokens)
    assert any("0.55" in t for t in tokens)


def test_numeric_faithfulness_fully_supported(sample_eval_paper, sample_eval_summary):
    res = evaluate_numeric_faithfulness(sample_eval_paper, sample_eval_summary)
    assert res["total_numeric_claims"] >= 2
    assert res["unsupported_claims"] == 0
    assert res["faithfulness_rate"] == 100.0
    assert res["requires_manual_review"] is False


def test_numeric_faithfulness_unsupported_value(sample_eval_paper, sample_eval_summary):
    # Alter summary finding to include a hallucinated number "99.9%"
    sample_eval_summary.findings.append(
        Claim(text="Adverse events were reported in 99.9% of patients.", supported_by=["S2"])
    )
    res = evaluate_numeric_faithfulness(sample_eval_paper, sample_eval_summary)
    assert res["unsupported_claims"] == 1
    assert res["faithfulness_rate"] < 100.0
    assert res["requires_manual_review"] is True
    assert "99.9%" in str(res["unsupported_details"])


def test_citation_resolution_valid(sample_eval_paper, sample_eval_summary):
    res = evaluate_citation_resolution(sample_eval_paper, sample_eval_summary)
    assert res["citation_resolution_rate"] == 100.0
    assert res["unresolvable_claims"] == 0


def test_citation_resolution_invalid_ids(sample_eval_paper, sample_eval_summary):
    # Insert a fake citation ID "S99"
    sample_eval_summary.findings.append(
        Claim(text="Another finding claim.", supported_by=["S99"])
    )
    res = evaluate_citation_resolution(sample_eval_paper, sample_eval_summary)
    assert res["unresolvable_claims"] == 1
    assert res["citation_resolution_rate"] < 100.0
    assert "S99" in str(res["unresolved_details"])


def test_required_field_presence_complete(sample_eval_summary):
    res = evaluate_required_fields(sample_eval_summary)
    assert res["field_presence_rate"] == 100.0
    assert len(res["missing_fields"]) == 0


def test_required_field_presence_missing_pico(sample_eval_summary):
    sample_eval_summary.pico["population"] = ""
    res = evaluate_required_fields(sample_eval_summary)
    assert res["field_presence_rate"] < 100.0
    assert "pico.population" in res["missing_fields"]


def test_llm_judge_mock(sample_eval_paper, sample_eval_summary):
    client = MockJudgeClient(scores={
        "factual_consistency": 5,
        "completeness": 4,
        "readability": 5,
        "evidence_support": 4,
    })
    res = evaluate_with_llm_judge(sample_eval_paper, sample_eval_summary, client=client)
    assert res["factual_consistency"] == 5
    assert res["completeness"] == 4
    assert res["overall_score"] == 4.5
    assert "explanation" in res


def test_load_dataset_valid():
    records = load_dataset(Path("data/test_set.json"))
    assert len(records) >= 15
    assert any(r["source_type"] == "synthetic" for r in records)
    assert any(r["source_type"] == "real" for r in records)


def test_load_dataset_nonexistent():
    with pytest.raises(FileNotFoundError):
        load_dataset(Path("data/non_existent_file.json"))


def test_run_evaluation_pipeline_mock(tmp_path):
    out_file = tmp_path / "eval_results.json"
    report = run_evaluation(
        dataset_path=Path("data/test_set.json"),
        output_path=out_file,
        use_mock=True,
        run_judge=True,
        verbose=False,
    )
    assert report["total_test_cases"] >= 15
    assert report["successful_cases"] == report["total_test_cases"]
    assert report["aggregate_metrics"]["citation_resolution"]["meets_target"] is True
    assert report["aggregate_metrics"]["numeric_faithfulness"]["meets_target"] is True
    assert report["aggregate_metrics"]["required_field_presence"]["meets_target"] is True
    assert out_file.is_file()
