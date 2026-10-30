"""Unit tests for NCBI PubMed API client and search bridge."""

import json
from unittest.mock import MagicMock, patch
import pytest
import requests

from app.ingestion.pubmed_client import (
    PubMedClient,
    PubMedAPIError,
    PubMedNetworkError,
    PubMedRateLimitError,
    RateLimiter,
    search_pubmed,
    SEEDED_PAPERS,
)
from app.models import Paper


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


def test_pubmed_client_search_success(mock_session):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "esearchresult": {
            "idlist": ["39240188", "39011923"]
        }
    }
    mock_session.get.return_value = mock_resp

    client = PubMedClient(session=mock_session)
    pmids = client.search("oncology neurosymbolic", retmax=5)

    assert pmids == ["39240188", "39011923"]
    assert mock_session.get.called
    args, kwargs = mock_session.get.call_args
    assert kwargs["params"]["term"] == "oncology neurosymbolic"
    assert kwargs["params"]["retmax"] == 5


def test_pubmed_client_search_empty_query(mock_session):
    client = PubMedClient(session=mock_session)
    assert client.search("") == []
    assert client.search("   ") == []
    assert not mock_session.get.called


def test_pubmed_client_search_rate_limit(mock_session):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 429
    mock_resp.text = "Too Many Requests"
    mock_session.get.return_value = mock_resp

    client = PubMedClient(session=mock_session)
    with pytest.raises(PubMedRateLimitError) as exc_info:
        client.search("cancer")
    assert exc_info.value.status_code == 429


def test_pubmed_client_search_network_timeout(mock_session):
    mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    client = PubMedClient(session=mock_session)
    with pytest.raises(PubMedNetworkError):
        client.search("hypertension")


def test_pubmed_client_search_invalid_json(mock_session):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_resp.text = "<html>Error</html>"
    mock_session.get.return_value = mock_resp

    client = PubMedClient(session=mock_session)
    with pytest.raises(PubMedAPIError):
        client.search("diabetes")


def test_pubmed_client_fetch_xml_success(mock_session):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = "<PubmedArticleSet><PubmedArticle></PubmedArticle></PubmedArticleSet>"
    mock_session.get.return_value = mock_resp

    client = PubMedClient(session=mock_session)
    xml = client.fetch_xml(["39240188", "39011923"])

    assert "<PubmedArticleSet>" in xml
    args, kwargs = mock_session.get.call_args
    assert kwargs["params"]["id"] == "39240188,39011923"


def test_pubmed_client_fetch_xml_empty_input(mock_session):
    client = PubMedClient(session=mock_session)
    assert client.fetch_xml([]) == ""
    assert client.fetch_xml("") == ""
    assert not mock_session.get.called


def test_search_pubmed_bridge_seeded_keyword_match():
    # Force offline fallback to test keyword matching logic
    with patch("app.ingestion.pubmed_client.get_default_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Offline test simulation")
        mock_get_client.return_value = mock_client

        results = search_pubmed("neurosymbolic oncology", limit=5)
        assert len(results) >= 1
        assert any("neurosymbolic" in p.title.lower() for p in results)


def test_search_pubmed_bridge_fallback_to_seeded():
    with patch("app.ingestion.pubmed_client.get_default_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Offline test simulation")
        mock_get_client.return_value = mock_client

        results = search_pubmed("completelynonexistentquerytoken12345", limit=5)
        assert len(results) == len(SEEDED_PAPERS)


def test_rate_limiter_throttling():
    limiter = RateLimiter(requests_per_second=100.0)
    limiter.throttle()
    limiter.throttle()
