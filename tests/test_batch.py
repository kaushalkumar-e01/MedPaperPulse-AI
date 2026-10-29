"""Tests for multi-abstract batch processing and quality target metrics."""

import pytest
from app.models import (
    BatchSummarizeRequest,
    BatchItemInput,
    BatchSummarizeResponse,
)
from app.ai.summarizer import generate_grounded_summary


def test_batch_summarization_isolation():
    p1 = {
        "id": "P1",
        "title": "Vaccine Study",
        "abstract": "We tested a vaccine in 1,000 patients. Efficacy was 94.5%.",
    }
    p2 = {
        "id": "P2",
        "title": "Oncology Study",
        "abstract": "We evaluated targeted therapy in 300 patients. Survival improved by 12.3%.",
    }

    res1 = generate_grounded_summary(paper_id=p1["id"], raw_abstract=p1["abstract"], title=p1["title"])
    res2 = generate_grounded_summary(paper_id=p2["id"], raw_abstract=p2["abstract"], title=p2["title"])

    assert "vaccine" in res1.summary.lower()
    assert "oncology" not in res1.summary.lower()
    assert "12.3%" not in res1.summary

    assert "targeted" in res2.summary.lower() or "therapy" in res2.summary.lower()
    assert "vaccine" not in res2.summary.lower()
    assert "94.5%" not in res2.summary


def test_batch_models_validation():
    req = BatchSummarizeRequest(
        papers=[
            BatchItemInput(id="1", title="Paper 1", abstract="Test abstract 1."),
            BatchItemInput(id="2", title="Paper 2", abstract="Test abstract 2."),
        ]
    )
    assert len(req.papers) == 2
    assert req.summary_depth == "Standard"

