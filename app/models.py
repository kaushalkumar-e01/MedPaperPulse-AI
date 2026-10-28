"""Shared Pydantic data schemas for MedPaperPulse-AI / MedLit Explorer.

This module defines the core data contracts shared across all system components:
- Person 1: AI Summarization & Prompt Engineering
- Person 2: PubMed Ingestion & SQLite Caching
- Person 3: Streamlit UI & Visual Components
- Person 4: Citation Validation & Claim Verification
- Person 5: Evaluation & Quality Metrics

All models are built with Pydantic v2 conventions and support clean JSON
serialization and deserialization without external side-effects or network calls.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


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
    """A single sentence or passage parsed from a source medical abstract.

    Passage IDs (e.g., 'S1', 'S2') are assigned strictly by the ingestion layer
    and must never be hallucinated or rewritten by the language model.
    """

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
    """Represents an ingested medical publication or user-pasted abstract.

    Produced by the ingestion layer (Person 2) and consumed by the AI summarizer
    (Person 1), UI layer (Person 3), and cache storage.
    """

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

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        v_norm = v.strip().lower()
        allowed = {s.value for s in SourceType}
        if v_norm not in allowed:
            # Allow custom string identifiers, but default to abstract if empty
            if not v_norm:
                return SourceType.ABSTRACT.value
        return v_norm


class Claim(BaseModel):
    """An individual synthesis claim or finding produced by the summarizer.

    Grounding invariant:
    - `supported_by` must reference valid `Passage.id` strings (e.g. ['S1', 'S3']).
    - `valid` defaults to False. The LLM must NEVER assert its own validity.
      Authoritative validation is performed strictly by Person 4's citation engine.
    """

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
    """The structured synthesis output contract for an analyzed medical abstract.

    Adheres strictly to the PICO framework and evidence-grounded claim structure.
    Coverage is defined as the fraction of claims with confirmed passage support
    and is calculated by the citation validation layer.
    """

    model_config = ConfigDict(extra="ignore")

    pmid: Optional[str] = Field(
        default=None,
        description="PubMed ID associated with this paper.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Title of the summarized paper.",
    )
    pico: Dict[str, str] = Field(
        default_factory=lambda: {
            "population": MISSING_INFO_INDICATOR,
            "intervention": MISSING_INFO_INDICATOR,
            "comparison": MISSING_INFO_INDICATOR,
            "outcome": MISSING_INFO_INDICATOR,
        },
        description="PICO framework breakdown (population, intervention, comparison, outcome).",
    )
    design: str = Field(
        default=MISSING_INFO_INDICATOR,
        description="Study methodology / design (e.g., 'Randomized Controlled Trial', 'Cohort Study').",
    )
    objective: Claim = Field(
        ...,
        description="Study research question or objective with supporting passage references.",
    )
    findings: List[Claim] = Field(
        default_factory=list,
        description="Key reported results and numerical evidence with supporting passage references.",
    )
    conclusion: Claim = Field(
        ...,
        description="Authors' primary reported conclusion preserving scientific uncertainty.",
    )
    limitations: List[Claim] = Field(
        default_factory=list,
        description="Explicit limitations reported in the abstract. If none reported, text states 'Not reported in the abstract.'",
    )
    glossary: Dict[str, str] = Field(
        default_factory=dict,
        description="Up to five medical acronyms/terms and their explicitly reported expansions.",
    )
    coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of claims validated against source passages (computed by Person 4).",
    )
    summary_length: SummaryLength = Field(
        default=SummaryLength.STANDARD,
        description="Requested summary length tier.",
    )
    explanation_level: ExplanationLevel = Field(
        default=ExplanationLevel.STUDENT,
        description="Requested audience complexity level.",
    )
    prompt_version: str = Field(
        default="v1",
        description="Version identifier of prompt template used to generate this summary.",
    )

    @field_validator("pico")
    @classmethod
    def validate_pico_keys(cls, v: Dict[str, str]) -> Dict[str, str]:
        canonical_keys = {"population", "intervention", "comparison", "outcome"}
        normalized = {}
        for k, val in v.items():
            key_lower = k.lower().strip()
            normalized[key_lower] = val.strip() if isinstance(val, str) else str(val)

        # Ensure all 4 canonical keys exist with default if missing
        for key in canonical_keys:
            if key not in normalized or not normalized[key]:
                normalized[key] = MISSING_INFO_INDICATOR
        return normalized

    @field_validator("design")
    @classmethod
    def validate_design(cls, v: str) -> str:
        v_stripped = v.strip()
        return v_stripped if v_stripped else MISSING_INFO_INDICATOR

