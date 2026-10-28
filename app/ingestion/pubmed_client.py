"""PubMed API client for MedPaperPulse AI.

Retrieves biomedical literature metadata and abstracts via the NCBI Entrez
E-utilities API (esearch and efetch).

Features:
- Search PubMed for PMIDs using ESearch
- Retrieve PubMed XML records using EFetch
- Configurable timeouts and network error resilience
- NCBI compliance: API key support, tool & email identification, and request throttling
- Modular parser integration with app.ingestion.xml_parser and app.models.PaperRecord
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Sequence
import requests
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

logger = logging.getLogger(__name__)

# NCBI E-utilities base URL
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TOOL_NAME = "MedPaperPulse-AI"
DEFAULT_SEARCH_TIMEOUT = 15.0
DEFAULT_FETCH_TIMEOUT = 25.0


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class PubMedError(Exception):
    """Base exception for all PubMed API errors."""
    pass


class PubMedNetworkError(PubMedError):
    """Raised when network requests to NCBI time out or fail to connect."""
    pass


class PubMedAPIError(PubMedError):
    """Raised when NCBI returns an error status code or API error message."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class PubMedRateLimitError(PubMedAPIError):
    """Raised when NCBI rate limits requests (HTTP 429)."""
    pass


class PubMedNotFoundError(PubMedError):
    """Raised when a requested PubMed ID is not found."""
    pass


# ---------------------------------------------------------------------------
# Throttler
# ---------------------------------------------------------------------------

class RequestThrottler:
    """Thread-safe rate limiter to comply with NCBI E-utilities usage policies.

    NCBI policy guidelines:
    - Without an API key: Max 3 requests/second (~0.34s interval).
    - With an API key: Max 10 requests/second (~0.11s interval).
    """

    def __init__(self, min_interval: float = 0.34):
        self.min_interval = min_interval
        self._last_request_time: float = 0.0
        self._lock = threading.Lock()

    def throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_time = time.monotonic()

    def update_interval(self, min_interval: float) -> None:
        with self._lock:
            self.min_interval = min_interval


# ---------------------------------------------------------------------------
# PubMed Client Class
# ---------------------------------------------------------------------------

class PubMedClient:
    """Client for interacting with NCBI Entrez E-utilities."""

    def __init__(
        self,
        api_key: str | None = None,
        email: str | None = None,
        tool: str = DEFAULT_TOOL_NAME,
        search_timeout: float = DEFAULT_SEARCH_TIMEOUT,
        fetch_timeout: float = DEFAULT_FETCH_TIMEOUT,
        session: requests.Session | None = None,
    ):
        self.api_key = api_key or os.getenv("NCBI_API_KEY")
        self.email = email or os.getenv("NCBI_EMAIL")
        self.tool = tool or os.getenv("NCBI_TOOL", DEFAULT_TOOL_NAME)
        self.search_timeout = search_timeout
        self.fetch_timeout = fetch_timeout
        self.session = session or requests.Session()

        # NCBI allows up to 10 req/sec with API key, 3 req/sec without
        min_interval = 0.11 if self.api_key else 0.34
        self._throttler = RequestThrottler(min_interval=min_interval)

    def _get_common_params(self) -> dict[str, str]:
        """Construct standard NCBI parameters."""
        params: dict[str, str] = {
            "tool": self.tool,
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def search(
        self,
        query: str,
        retmax: int = 10,
        retstart: int = 0,
    ) -> list[str]:
        """Search PubMed using ESearch and return a list of PMIDs.

        Args:
            query: PubMed search query string.
            retmax: Maximum number of PMIDs to return (1-500).
            retstart: Index of first record to retrieve.

        Returns:
            list[str]: List of matching PubMed IDs.

        Raises:
            PubMedNetworkError: If the request fails due to network/timeout.
            PubMedRateLimitError: If rate limited by NCBI.
            PubMedAPIError: If NCBI returns an API or HTTP error.
        """
        trimmed_query = query.strip()
        if not trimmed_query:
            return []

        retmax = max(1, min(retmax, 500))
        retstart = max(0, retstart)

        params: dict[str, Any] = {
            **self._get_common_params(),
            "db": "pubmed",
            "term": trimmed_query,
            "retmode": "json",
            "retmax": retmax,
            "retstart": retstart,
        }

        url = f"{EUTILS_BASE_URL}/esearch.fcgi"
        self._throttler.throttle()

        try:
            response = self.session.get(url, params=params, timeout=self.search_timeout)
        except requests.exceptions.Timeout as exc:
            raise PubMedNetworkError(
                f"PubMed search request timed out after {self.search_timeout}s: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise PubMedNetworkError(f"PubMed search request failed: {exc}") from exc

        if response.status_code == 429:
            raise PubMedRateLimitError(
                "NCBI rate limit exceeded (HTTP 429).",
                status_code=429,
                response_text=response.text,
            )
        elif not response.ok:
            raise PubMedAPIError(
                f"PubMed search returned HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise PubMedAPIError(
                "Failed to parse JSON response from PubMed ESearch",
                response_text=response.text,
            ) from exc

        esearch_result = data.get("esearchresult", {})
        if "ERROR" in esearch_result:
            error_msg = esearch_result["ERROR"]
            raise PubMedAPIError(f"PubMed ESearch error: {error_msg}")

        return [str(pmid) for pmid in esearch_result.get("idlist", [])]

    def fetch_xml(self, pmids: str | Sequence[str]) -> str:
        """Fetch raw XML data from PubMed for one or more PMIDs using EFetch.

        Args:
            pmids: A single PMID or sequence of PMIDs.

        Returns:
            str: Raw PubMed XML string, or empty string if no valid PMIDs provided.

        Raises:
            PubMedNetworkError: If the request fails due to network/timeout.
            PubMedRateLimitError: If rate limited by NCBI.
            PubMedAPIError: If NCBI returns an API or HTTP error.
        """
        if isinstance(pmids, str):
            clean_ids = [pmids.strip()] if pmids.strip() else []
        else:
            clean_ids = [str(pid).strip() for pid in pmids if str(pid).strip()]

        if not clean_ids:
            return ""

        params: dict[str, Any] = {
            **self._get_common_params(),
            "db": "pubmed",
            "id": ",".join(clean_ids),
            "retmode": "xml",
        }

        url = f"{EUTILS_BASE_URL}/efetch.fcgi"
        self._throttler.throttle()

        try:
            response = self.session.get(url, params=params, timeout=self.fetch_timeout)
        except requests.exceptions.Timeout as exc:
            raise PubMedNetworkError(
                f"PubMed fetch request timed out after {self.fetch_timeout}s: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise PubMedNetworkError(f"PubMed fetch request failed: {exc}") from exc

        if response.status_code == 429:
            raise PubMedRateLimitError(
                "NCBI rate limit exceeded (HTTP 429).",
                status_code=429,
                response_text=response.text,
            )
        elif not response.ok:
            raise PubMedAPIError(
                f"PubMed fetch returned HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )

        return response.text

    def fetch_papers(
        self,
        pmids: str | Sequence[str],
        parser: Callable[[str], list[Any]] | None = None,
    ) -> list[Any]:
        """Fetch paper records for given PMIDs.

        If a parser function is provided, it is used to parse the XML.
        Otherwise, attempts to use `parse_pubmed_xml` from `app.ingestion.xml_parser`.

        Args:
            pmids: Single PMID or sequence of PMIDs.
            parser: Optional callable taking an XML string and returning a list of paper models.

        Returns:
            list[Any]: Parsed paper records (typically PaperRecord instances).
        """
        xml_content = self.fetch_xml(pmids)
        if not xml_content.strip():
            return []

        parse_func = parser
        if parse_func is None:
            try:
                from app.ingestion.xml_parser import parse_pubmed_xml  # type: ignore
                parse_func = parse_pubmed_xml
            except (ImportError, AttributeError):
                parse_func = None

        if parse_func is not None:
            return parse_func(xml_content)

        raise NotImplementedError(
            "XML parsing dependency 'app.ingestion.xml_parser.parse_pubmed_xml' is not yet implemented. "
            "Please provide a custom parser callable or implement the XML parser module."
        )

    def get_paper_by_pmid(
        self,
        pmid: str,
        parser: Callable[[str], list[Any]] | None = None,
    ) -> Any | None:
        """Fetch a single paper record by PMID."""
        papers = self.fetch_papers([pmid], parser=parser)
        return papers[0] if papers else None

    def search_and_fetch(
        self,
        query: str,
        retmax: int = 10,
        parser: Callable[[str], list[Any]] | None = None,
    ) -> list[Any]:
        """Search PubMed and fetch the corresponding paper records."""
        pmids = self.search(query, retmax=retmax)
        if not pmids:
            return []
        return self.fetch_papers(pmids, parser=parser)


# ---------------------------------------------------------------------------
# Default Module-level Client & Convenience Functions
# ---------------------------------------------------------------------------

_default_client: PubMedClient | None = None


def get_default_client() -> PubMedClient:
    """Get or initialize the shared PubMedClient singleton."""
    global _default_client
    if _default_client is None:
        _default_client = PubMedClient()
    return _default_client


def search_pmids(query: str, retmax: int = 10) -> list[str]:
    """Search PubMed and return matching PMIDs."""
    return get_default_client().search(query=query, retmax=retmax)


def fetch_paper_xml(pmids: str | Sequence[str]) -> str:
    """Fetch raw PubMed XML for one or more PMIDs."""
    return get_default_client().fetch_xml(pmids=pmids)


def fetch_papers(
    pmids: str | Sequence[str],
    parser: Callable[[str], list[Any]] | None = None,
) -> list[Any]:
    """Fetch and parse paper records for the given PMIDs."""
    return get_default_client().fetch_papers(pmids=pmids, parser=parser)


def get_paper_by_pmid(
    pmid: str,
    parser: Callable[[str], list[Any]] | None = None,
) -> Any | None:
    """Fetch a single paper record by PMID."""
    return get_default_client().get_paper_by_pmid(pmid=pmid, parser=parser)
