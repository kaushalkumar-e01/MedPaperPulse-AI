"""Domain data models and schemas for MedPaperPulse-AI."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


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
    category: str = "General"  # Background, Methods, Results, Conclusion
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
    summary_depth: str = "Standard"  # Short, Standard, Detailed
    audience: str = "Researcher"      # Beginner, Student, Researcher


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
