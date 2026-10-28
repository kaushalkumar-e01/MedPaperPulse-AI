"""Main Evaluation Pipeline for MedPaperPulse-AI.

Command-line entry point:
    python -m eval.evaluate [--dataset PATH] [--output PATH] [--mock] [--llm-judge] [--verbose]

Loads the standardized dataset, generates summaries (using live provider or deterministic mock),
computes automated metrics (numeric faithfulness, citation resolution, field presence),
runs optional LLM judge, and produces structured and tabular reports.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models import PaperRecord, Passage, SummaryResult, SummaryLength, ExplanationLevel, MISSING_INFO_INDICATOR
from app.ai.summarizer import summarize_paper, MockLLMClient, BaseLLMClient
from eval.metrics import evaluate_summary
from eval.llm_judge import evaluate_with_llm_judge, MockJudgeClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATASET_PATH = Path("data/test_set.json")
DEFAULT_OUTPUT_PATH = Path("eval/results.json")


def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    """Loads and validates the test dataset JSON."""
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        raise ValueError("Evaluation dataset contains 0 records.")
    return records


def record_to_paper(record: Dict[str, Any]) -> PaperRecord:
    """Converts a dataset dictionary record into a validated PaperRecord."""
    passages = [
        Passage(id=p["id"], text=p["text"], section=p.get("section", "UNSPECIFIED"))
        for p in record.get("passages", [])
    ]
    return PaperRecord(
        pmid=record.get("pmid"),
        doi=record.get("doi"),
        title=record["title"],
        authors=record.get("authors", []),
        journal=record.get("journal"),
        pub_date=record.get("pub_date"),
        pub_types=record.get("pub_types", []),
        url=record.get("url"),
        passages=passages,
        source_type=record.get("source_type", "abstract"),
    )


def create_deterministic_mock_summary(paper: PaperRecord, record: Dict[str, Any]) -> str:
    """Generates an accurate, deterministic mock summary response tailored to the test case."""
    exp = record.get("expected_behaviors", {})
    pico = exp.get("pico", {
        "population": "Target patient cohort",
        "intervention": "Tested clinical intervention",
        "comparison": "Placebo or active comparator",
        "outcome": "Primary and secondary clinical endpoints",
    })

    # Pick valid passage IDs for findings
    result_passages = [p for p in paper.passages if p.section in ("RESULTS", "METHODS")]
    if not result_passages:
        result_passages = paper.passages

    # If missing results expected (e.g. protocol)
    if exp.get("missing_results_expected"):
        findings = [{"text": MISSING_INFO_INDICATOR, "supported_by": []}]
    else:
        # Construct faithful finding sentences from passages
        findings = []
        for p in result_passages[:2]:
            findings.append({"text": p.text, "supported_by": [p.id]})

    limitations = [
        {"text": "Sample restricted to study cohort.", "supported_by": [paper.passages[-1].id]}
    ] if paper.passages else [{"text": MISSING_INFO_INDICATOR, "supported_by": []}]

    mock_data = {
        "pico": pico,
        "design": record.get("study_design", "Clinical Study"),
        "objective": {
            "text": f"Evaluate {pico.get('intervention', 'intervention')}.",
            "supported_by": [paper.passages[0].id] if paper.passages else ["S1"],
        },
        "findings": findings,
        "conclusion": {
            "text": paper.passages[-1].text if paper.passages else "Study completed.",
            "supported_by": [paper.passages[-1].id] if paper.passages else ["S1"],
        },
        "limitations": limitations,
        "glossary": {"RCT": "Randomized Controlled Trial"},
    }
    return json.dumps(mock_data)


def run_evaluation(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    use_mock: bool = True,
    run_judge: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Runs the full evaluation pipeline and saves results."""
    records = load_dataset(dataset_path)
    total_cases = len(records)
    logger.info("Loaded %d test cases from %s", total_cases, dataset_path)

    results_per_case: List[Dict[str, Any]] = []

    # Aggregators
    total_numeric_claims = 0
    supported_numeric_claims = 0
    total_claims = 0
    resolvable_claims = 0
    total_fields = 0
    present_fields = 0

    judge_scores: List[float] = []

    for idx, rec in enumerate(records, 1):
        paper = record_to_paper(rec)
        case_id = rec.get("id", f"CASE-{idx}")

        # Choose client
        if use_mock:
            mock_json = create_deterministic_mock_summary(paper, rec)
            client: BaseLLMClient = MockLLMClient(response_generator=mock_json)
        else:
            client = None  # Uses default OpenAICompatibleClient

        try:
            summary = summarize_paper(paper, client=client)
        except Exception as err:
            logger.error("Failed to summarize case %s: %s", case_id, err)
            results_per_case.append({
                "case_id": case_id,
                "title": paper.title,
                "status": "error",
                "error": str(err),
            })
            continue

        # Automated metrics
        case_metrics = evaluate_summary(paper, summary)
        case_metrics["case_id"] = case_id
        case_metrics["source_type"] = rec.get("source_type", "unknown")
        case_metrics["test_category"] = rec.get("test_category", "general")

        # Accumulate
        num_res = case_metrics["numeric_faithfulness"]
        cite_res = case_metrics["citation_resolution"]
        field_res = case_metrics["required_fields"]

        total_numeric_claims += num_res["total_numeric_claims"]
        supported_numeric_claims += num_res["supported_claims"]
        total_claims += cite_res["total_claims"]
        resolvable_claims += cite_res["resolvable_claims"]
        total_fields += field_res["total_fields"]
        present_fields += field_res["present_fields"]

        # LLM Judge (optional)
        if run_judge:
            judge_client = MockJudgeClient() if use_mock else None
            judge_res = evaluate_with_llm_judge(paper, summary, client=judge_client)
            case_metrics["llm_judge"] = judge_res
            if "overall_score" in judge_res:
                judge_scores.append(float(judge_res["overall_score"]))

        results_per_case.append(case_metrics)

        if verbose:
            logger.info(
                "[%d/%d] %s: Faithfulness: %.1f%%, Citation: %.1f%%, Fields: %.1f%%",
                idx,
                total_cases,
                case_id,
                num_res["faithfulness_rate"],
                cite_res["citation_resolution_rate"],
                field_res["field_presence_rate"],
            )

    # Compute aggregate percentages
    overall_faithfulness = (
        round((supported_numeric_claims / total_numeric_claims * 100.0), 2)
        if total_numeric_claims > 0
        else 100.0
    )
    overall_citation_res = (
        round((resolvable_claims / total_claims * 100.0), 2)
        if total_claims > 0
        else 100.0
    )
    overall_field_presence = (
        round((present_fields / total_fields * 100.0), 2)
        if total_fields > 0
        else 100.0
    )
    avg_judge_score = (
        round(sum(judge_scores) / len(judge_scores), 2) if judge_scores else None
    )

    summary_report = {
        "dataset_path": str(dataset_path),
        "total_test_cases": total_cases,
        "successful_cases": len([r for r in results_per_case if r.get("status") != "error"]),
        "evaluation_mode": "mock" if use_mock else "live_provider",
        "aggregate_metrics": {
            "numeric_faithfulness": {
                "rate_percentage": overall_faithfulness,
                "supported_claims": supported_numeric_claims,
                "total_numeric_claims": total_numeric_claims,
                "target_percentage": 95.0,
                "meets_target": overall_faithfulness >= 95.0,
            },
            "citation_resolution": {
                "rate_percentage": overall_citation_res,
                "resolvable_claims": resolvable_claims,
                "total_claims": total_claims,
                "target_percentage": 95.0,
                "meets_target": overall_citation_res >= 95.0,
            },
            "required_field_presence": {
                "rate_percentage": overall_field_presence,
                "present_fields": present_fields,
                "total_fields": total_fields,
                "target_percentage": 90.0,
                "meets_target": overall_field_presence >= 90.0,
            },
            "llm_judge_score": {
                "average_score": avg_judge_score,
                "target_score": 4.0,
                "evaluated_count": len(judge_scores),
            },
        },
        "per_case_results": results_per_case,
    }

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)
    logger.info("Evaluation results written to %s", output_path)

    # Print summary table
    print_evaluation_table(summary_report)

    return summary_report


def print_evaluation_table(report: Dict[str, Any]) -> None:
    """Prints a formatted ASCII evaluation results table to stdout."""
    agg = report["aggregate_metrics"]
    num = agg["numeric_faithfulness"]
    cite = agg["citation_resolution"]
    field = agg["required_field_presence"]
    judge = agg["llm_judge_score"]

    print("\n" + "=" * 78)
    print("           MEDPAPERPULSE-AI / MEDLIT EXPLORER EVALUATION REPORT")
    print("=" * 78)
    print(f"Dataset Size:    {report['total_test_cases']} cases ({report['successful_cases']} evaluated successfully)")
    print(f"Evaluation Mode: {report['evaluation_mode'].upper()}")
    print("-" * 78)
    print(f"{'Metric':<28} | {'Measured':<14} | {'Sample Size':<16} | {'Target':<10}")
    print("-" * 78)
    print(f"{'Citation resolution rate':<28} | {cite['rate_percentage']}%{'':<9} | {cite['total_claims']} claims{'':<7} | 95%+")
    print(f"{'Numeric faithfulness':<28} | {num['rate_percentage']}%{'':<9} | {num['total_numeric_claims']} claims{'':<7} | 95%+")
    print(f"{'Required-field presence':<28} | {field['rate_percentage']}%{'':<9} | {field['total_fields']} fields{'':<7} | 90%+")
    
    if judge["average_score"] is not None:
        print(f"{'LLM-judge quality':<28} | {judge['average_score']}/5.0{'':<8} | {judge['evaluated_count']} summaries{'':<4} | 4.0/5")
    else:
        print(f"{'LLM-judge quality':<28} | {'Not evaluated':<14} | {'0 summaries':<16} | 4.0/5")

    print(f"{'Manual review (dual)':<28} | {'Template ready':<14} | {'16 cases seeded':<16} | 8-10 cases")
    print("=" * 78 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MedPaperPulse-AI summarization.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH, help="Path to test_set.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Path for results.json")
    parser.add_argument("--mock", action="store_true", default=True, help="Run with deterministic mock client")
    parser.add_argument("--live", action="store_true", help="Run with live LLM provider")
    parser.add_argument("--llm-judge", action="store_true", help="Include LLM judge evaluation")
    parser.add_argument("--verbose", action="store_true", help="Print detailed progress per paper")

    args = parser.parse_args()
    use_mock = not args.live

    run_evaluation(
        dataset_path=args.dataset,
        output_path=args.output,
        use_mock=use_mock,
        run_judge=args.llm_judge,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
