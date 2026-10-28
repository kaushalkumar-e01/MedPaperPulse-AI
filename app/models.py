"""Shared Pydantic data schemas for MedPaperPulse-AI / MedLit Explorer.

Contains both core domain contracts (Person 1-5 modules) and API REST bridge schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SummaryLength(str, Enum):
    """Supported summary length tiers."""

    SHORT = "short"
    STANDARD = "standard"
    DETAILED = "detailed"


class ExplanationLevel(str, Enum):
    """Target audience explanation complexity levels."""

    BEGINNER = "beginner"
    STUDENT = "student"
    RESEARCHER = "researcher"


class SourceType(str, Enum):
    """Allowed provenance origins for input records."""

    ABSTRACT = "abstract"
    PASTED = "pasted"


# Canonical missing information indicator used system-wide
MISSING_INFO_INDICATOR = "Not reported in the abstract."


class Passage(BaseModel):
    """A single sentence or passage parsed from a source medical abstract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(
        ...,
        description="Stable identifier assigned by ingestion (e.g., 'S1', 'S2').",
        min_length=1,
    )
    text: str = Field(
        ...,
        description="Original source sentence preserved verbatim.",
        min_length=1,
    )
    section: str = Field(
        default="UNSPECIFIED",
        description="Abstract section label (e.g., 'BACKGROUND', 'METHODS', 'RESULTS', 'CONCLUSIONS').",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Passage ID cannot be empty or blank.")
        return v_stripped

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Passage text cannot be empty or blank.")
        return v

    @field_validator("section")
    @classmethod
    def validate_section(cls, v: str) -> str:
        v_stripped = v.strip()
        return v_stripped.upper() if v_stripped else "UNSPECIFIED"


class PaperRecord(BaseModel):
    """Represents an ingested medical publication or user-pasted abstract."""

    model_config = ConfigDict(extra="ignore")

    pmid: Optional[str] = Field(
        default=None,
        description="PubMed Unique Identifier (if retrieved from PubMed).",
    )
    doi: Optional[str] = Field(
        default=None,
        description="Digital Object Identifier.",
    )
    title: str = Field(
        ...,
        description="Title of the research paper.",
        min_length=1,
    )
    authors: List[str] = Field(
        default_factory=list,
        description="List of contributing authors.",
    )
    journal: Optional[str] = Field(
        default=None,
        description="Publishing academic journal name.",
    )
    pub_date: Optional[str] = Field(
        default=None,
        description="Publication date or year string.",
    )
    pub_types: List[str] = Field(
        default_factory=list,
        description="Publication type labels (e.g., 'Journal Article', 'Clinical Trial').",
    )
    url: Optional[str] = Field(
        default=None,
        description="Canonical URL to publication or PubMed record.",
    )
    passages: List[Passage] = Field(
        default_factory=list,
        description="Ordered list of sentence-tagged passages from the abstract.",
    )
    source_type: str = Field(
        default=SourceType.ABSTRACT.value,
        description="Origin indicator: 'abstract' for PubMed queries or 'pasted' for manual user input.",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Paper title cannot be empty or whitespace only.")
        return v_stripped


class Claim(BaseModel):
    """An individual synthesis claim or finding produced by the summarizer."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(
        ...,
        description="Synthesized claim text.",
        min_length=1,
    )
    supported_by: List[str] = Field(
        default_factory=list,
        description="List of Passage IDs (e.g. ['S2', 'S4']) that support this claim.",
    )
    valid: bool = Field(
        default=False,
        description="Authoritative citation support status computed exclusively by citation validator.",
    )

    @field_validator("text")
    @classmethod
    def validate_claim_text(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Claim text cannot be empty or blank.")
        return v_stripped

    @field_validator("supported_by")
    @classmethod
    def clean_supported_by(cls, v: List[str]) -> List[str]:
        cleaned = []
        for pid in v:
            if isinstance(pid, str):
                p = pid.strip().strip("[]").strip()
                if p:
                    cleaned.append(p)
        return cleaned


class SummaryResult(BaseModel):
    """The structured synthesis output contract for an analyzed medical abstract."""

    model_config = ConfigDict(extra="ignore")

    pmid: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    pico: Dict[str, str] = Field(
        default_factory=lambda: {
            "population": MISSING_INFO_INDICATOR,
            "intervention": MISSING_INFO_INDICATOR,
            "comparison": MISSING_INFO_INDICATOR,
            "outcome": MISSING_INFO_INDICATOR,
        }
    )
    design: str = Field(default=MISSING_INFO_INDICATOR)
    objective: Claim
    findings: List[Claim] = Field(default_factory=list)
    conclusion: Claim
    limitations: List[Claim] = Field(default_factory=list)
    glossary: Dict[str, str] = Field(default_factory=dict)
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    summary_length: SummaryLength = Field(default=SummaryLength.STANDARD)
    explanation_level: ExplanationLevel = Field(default=ExplanationLevel.STUDENT)
    prompt_version: str = Field(default="v1")


# ---------------------------------------------------------------------------
# API Bridge Models (Used by FastAPI REST endpoints and React UI)
# ---------------------------------------------------------------------------

class Paper(BaseModel):
    id: str
    title: str
    authors: str
    journal: str
    date: str
    type: str = "Research Article"
    source: str = "PubMed"
    tag: str = "High traceability"
    tone: str = "lilac"
    abstract: str
    pmid_doi: Optional[str] = None
    url: Optional[str] = None


class SentenceSpan(BaseModel):
    tag: str  # e.g. "[S1]"
    index: int
    text: str
    category: str = "General"
    numeric_entities: List[str] = Field(default_factory=list)


class PicoBadges(BaseModel):
    population: Dict[str, str] = Field(
        default_factory=lambda: {
            "label": "Population",
            "value": "Adults with solid tumors",
            "detail": "n = 1,284 records",
            "style": "pop",
        }
    )
    intervention: Dict[str, str] = Field(
        default_factory=lambda: {
            "label": "Intervention",
            "value": "Neurosymbolic model",
            "detail": "Knowledge graph + LLM",
            "style": "blue",
        }
    )
    comparison: Dict[str, str] = Field(
        default_factory=lambda: {
            "label": "Comparison",
            "value": "Standard LLM pipeline",
            "detail": "Retrieval-augmented",
            "style": "mint",
        }
    )
    outcome: Dict[str, str] = Field(
        default_factory=lambda: {
            "label": "Outcome",
            "value": "Traceable reasoning",
            "detail": "94% claim linkage",
            "style": "peach",
        }
    )


class SearchRequest(BaseModel):
    query: str
    filter_type: Optional[str] = "All evidence"
    limit: int = 10


class SearchResponse(BaseModel):
    query: str
    count: int
    papers: List[Paper]


class SummarizeRequest(BaseModel):
    paper_id: Optional[str] = None
    abstract: Optional[str] = None
    summary_depth: str = "Standard"
    audience: str = "Researcher"


class SummarizeResponse(BaseModel):
    paper_id: Optional[str] = None
    title: Optional[str] = None
    summary: str
    sentences: List[SentenceSpan]
    pico: PicoBadges
    preserved_excerpts: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: str = "High"


class CompareRequest(BaseModel):
    paper_ids: List[str] = Field(default_factory=list)


class ComparisonRow(BaseModel):
    metric: str
    first: str
    second: str
    conflict: bool = False
    conflict_label: Optional[str] = None


class CompareResponse(BaseModel):
    papers: List[Paper]
    rows: List[ComparisonRow]
    callout: Dict[str, str]


class ChatRequest(BaseModel):
    query: str
    selected_papers: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    citations: List[str] = Field(default_factory=list)
    confidence: str = "High"


class PasteParseRequest(BaseModel):
    text: str
    filename: Optional[str] = None


class PasteParseResponse(BaseModel):
    word_count: int
    sentences: List[SentenceSpan]
    pico: PicoBadges
    title: str = "Custom Ingested Abstract"
