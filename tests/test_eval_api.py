"""Unit tests for Evaluation Lab API and empirical benchmarks."""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_eval_metrics_endpoint(client):
    response = client.get("/api/eval/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_test_cases"] == 16
    assert data["successful_cases"] == 16
    assert data["composite_quality_score"] >= 85.0
    assert data["meets_85_target"] is True
    assert "metrics" in data
    assert "citation_resolution" in data["metrics"]
    assert "numeric_faithfulness" in data["metrics"]
    assert "pico_extraction" in data["metrics"]
    assert "honest_missingness" in data["metrics"]


def test_eval_run_endpoint(client):
    response = client.post("/api/eval/run")
    assert response.status_code == 200
    data = response.json()
    assert data["composite_quality_score"] >= 85.0
    assert len(data["per_case_results"]) == 16


def test_compare_endpoint_dynamic_columns(client):
    payload = {
        "paper_ids": ["p1", "p2", "p3"],
    }
    response = client.post("/api/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["papers"]) >= 3
    assert len(data["rows"]) == 8
    # Ensure every row has values mapping
    for row in data["rows"]:
        assert "values" in row
        assert "p1" in row["values"]
        assert "p2" in row["values"]
        assert "p3" in row["values"]

