"""Unit tests for multi-paper comparison and scientific conflict detection."""

import pytest
from app.models import Paper, CompareRequest
from app.comparisons import build_comparison_matrix, STANDARD_COMPARISON_FIELDS
from app.comparisons.comparator import compare_papers, ComparisonMatrix
from app.comparisons.conflict_detector import detect_conflicts, ComparisonStatus


def test_compare_papers_multi_column():
    papers = [
        {"id": "p1", "title": "Paper 1", "Findings": "Drug A improved overall survival.", "Intervention": "Drug A", "Population": "Human clinical trial", "Study design": "RCT"},
        {"id": "p2", "title": "Paper 2", "Findings": "Drug A had no effect on survival.", "Intervention": "Drug A", "Population": "Human clinical trial", "Study design": "RCT"},
        {"id": "p3", "title": "Paper 3", "Findings": "Drug B was beneficial in cell culture.", "Intervention": "Drug B", "Population": "In vitro cell culture", "Study design": "Laboratory"},
    ]
    matrix = compare_papers(papers)
    assert len(matrix.paper_ids) == 3
    assert len(matrix.fields) == 8
    assert "p1" in matrix.matrix["Findings"]
    assert "p2" in matrix.matrix["Findings"]
    assert "p3" in matrix.matrix["Findings"]


def test_conflict_detection_opposing_findings():
    papers = [
        {"id": "study_a", "title": "Study A", "Findings": "Treatment improved outcomes significantly.", "Intervention": "Drug X", "Population": "Human patients"},
        {"id": "study_b", "title": "Study B", "Findings": "Treatment failed and had no effect.", "Intervention": "Drug X", "Population": "Human patients"},
    ]
    res = detect_conflicts(papers)
    assert res.status == ComparisonStatus.CONFLICT
    assert "opposing" in res.reason.lower() or "benefit" in res.reason.lower()


def test_build_comparison_matrix_seeded_and_custom():
    custom_paper = Paper(
        id="custom_1",
        title="Custom Trial of SGLT2 in Renal Disease",
        authors="J. Smith et al.",
        journal="NEJM",
        date="2024",
        abstract="Background: We evaluated SGLT2 inhibition in 1,450 patients with CKD. Results: Renal decline was reduced by 34%. Conclusions: SGLT2 slows CKD progression.",
    )
    resp = build_comparison_matrix(["p1", "custom_1"], papers=[custom_paper])
    assert len(resp.papers) >= 2
    assert len(resp.rows) == 8
    assert any(p.id == "custom_1" for p in resp.papers)
    # Check that rows contain values dict
    for row in resp.rows:
        assert isinstance(row.values, dict)
        assert "p1" in row.values
        assert "custom_1" in row.values

