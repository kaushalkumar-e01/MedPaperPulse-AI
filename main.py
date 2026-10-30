"""FastAPI backend bridge for MedPaperPulse-AI.
Exposes REST endpoints for literature search, grounded summarization, comparison matrix, and citation resolution.
"""

import os
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    SearchRequest,
    SearchResponse,
    SummarizeRequest,
    SummarizeResponse,
    CompareRequest,
    CompareResponse,
    PasteParseRequest,
    PasteParseResponse,
    ChatRequest,
    ChatResponse,
    BatchSummarizeRequest,
    BatchSummarizeResponse,
    BatchItemResult,
)
from app.ingestion.pubmed_client import search_pubmed, SEEDED_PAPERS
from app.ingestion.paste_parser import parse_pasted_text
from app.ingestion.sentence_tagger import tag_sentences
from app.ingestion.document_loader import ingest_document, DocumentIngestionError
from app.ai.summarizer import generate_grounded_summary
from app.ai.chat import answer_question
from app.ai.gemini_client import is_gemini_available, generate_gemini_chat
from app.comparisons import build_comparison_matrix

app = FastAPI(
    title="MedPaperPulse-AI API Bridge",
    description="Backend services for clinical literature inspection, provenance tracking, and evidence synthesis.",
    version="1.0.0",
)

# Configure CORS Middleware for all origins or local frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root entry point providing service discovery and OpenAPI documentation links."""
    return {
        "service": "MedPaperPulse-AI API Bridge",
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
        "endpoints": [
            "/api/health",
            "/api/papers",
            "/api/search",
            "/api/summarize",
            "/api/compare",
            "/api/paste",
            "/api/upload",
            "/api/upload-batch",
            "/api/chat",
            "/api/batch-summarize",
            "/api/eval/metrics",
            "/api/eval/run",
        ],
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint with active AI provider status."""
    gemini_on = is_gemini_available()
    openai_on = bool(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))

    if gemini_on:
        provider = "Google Gemini"
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        mode = "gemini_live"
    elif openai_on:
        provider = "OpenAI / Compatible Provider"
        model = os.getenv("MODEL_NAME", "gpt-4o-mini")
        mode = "openai_live"
    else:
        provider = "Deterministic Grounded Engine"
        model = "Offline Evidence Rule-Based Engine"
        mode = "offline_deterministic"

    return {
        "status": "ok",
        "service": "MedPaperPulse-AI Backend Bridge",
        "version": "1.0.0",
        "ai_provider": {
            "configured": gemini_on or openai_on,
            "provider": provider,
            "model": model,
            "mode": mode,
            "gemini_active": gemini_on,
        },
    }


@app.get("/api/papers")
async def list_papers():
    """Returns the default curated list of literature papers."""
    return {"papers": SEEDED_PAPERS}


@app.post("/api/search", response_model=SearchResponse)
async def api_search(req: SearchRequest):
    """Searches PubMed and literature database based on query string."""
    query = req.query.strip()
    if not query:
        return SearchResponse(query="", count=len(SEEDED_PAPERS), papers=SEEDED_PAPERS)

    results = search_pubmed(query=query, limit=req.limit)

    # Apply filter if provided and not "All evidence"
    if req.filter_type and req.filter_type != "All evidence":
        results = [
            p for p in results
            if p.type == req.filter_type or p.source == req.filter_type
        ]

    return SearchResponse(query=query, count=len(results), papers=results)


@app.post("/api/summarize", response_model=SummarizeResponse)
async def api_summarize(req: SummarizeRequest):
    """Generates a grounded summary with explicit citation spans and numeric claims."""
    try:
        summary_resp = generate_grounded_summary(
            paper_id=req.paper_id,
            raw_abstract=req.abstract,
            title=req.title,
            depth=req.summary_depth,
            audience=req.audience,
        )
        return summary_resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare", response_model=CompareResponse)
async def api_compare(req: CompareRequest):
    """Generates an evidence comparison matrix across selected studies."""
    paper_ids = req.paper_ids if req.paper_ids else ["p1", "p2"]
    comparison = build_comparison_matrix(paper_ids, papers=req.papers)
    return comparison


@app.post("/api/paste", response_model=PasteParseResponse)
async def api_paste(req: PasteParseRequest):
    """Parses raw abstract text, segments sentences with [S1]...[Sn], and extracts PICO signals."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text body cannot be empty.")

    sentences, pico = parse_pasted_text(req.text)
    word_count = len(req.text.split())

    return PasteParseResponse(
        word_count=word_count,
        sentences=sentences,
        pico=pico,
        title="Custom Abstract Analysis",
    )


@app.post("/api/upload")
async def api_upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    """Ingests a research document (PDF or TXT) and extracts text, sentences, and PICO tags."""
    content = await file.read()
    try:
        doc_result = ingest_document(
            file_bytes=content,
            filename=file.filename,
            user_title=title,
            mime_type=file.content_type,
        )
        return doc_result
    except DocumentIngestionError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected extraction failure: {str(exc)}")


@app.post("/api/upload-batch")
async def api_upload_batch(
    files: List[UploadFile] = File(...),
):
    """Batch ingestion of multiple documents with partial failure resilience."""
    MAX_UPLOAD_FILES = 10
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded {len(files)} files, which exceeds maximum limit of {MAX_UPLOAD_FILES} files.",
        )

    results = []
    for f in files:
        content = await f.read()
        try:
            doc = ingest_document(
                file_bytes=content,
                filename=f.filename,
                mime_type=f.content_type,
            )
            results.append({
                "status": "success",
                "filename": f.filename,
                "document": doc,
            })
        except DocumentIngestionError as err:
            results.append({
                "status": "error",
                "filename": f.filename,
                "error_message": str(err),
            })
        except Exception as exc:
            results.append({
                "status": "error",
                "filename": f.filename,
                "error_message": f"Extraction error: {str(exc)}",
            })

    successful_count = sum(1 for r in results if r["status"] == "success")
    return {
        "total": len(files),
        "successful": successful_count,
        "failed": len(files) - successful_count,
        "results": results,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """Grounded Q&A assistant answering questions strictly from paper passages."""
    query = req.query.strip()
    if not query:
        return ChatResponse(
            response="Please ask a question regarding the paper evidence.",
            citations=[],
            confidence="Low",
            is_grounded=False,
            status="EMPTY_QUERY",
            mode="grounded_qa",
        )

    # Gather passages and paper metadata from request or target papers
    passages: dict[str, str] = {}
    paper_metadata: list[dict] = []

    if req.passages:
        passages = req.passages
    elif req.active_paper_abstract:
        spans = tag_sentences(req.active_paper_abstract)
        passages = {s.tag.strip("[]"): s.text for s in spans}
        paper_metadata.append({
            "id": req.active_paper_id or "active_doc",
            "title": req.active_paper_id or "Active Research Document",
        })
    else:
        target_ids = ([req.active_paper_id] if req.active_paper_id else []) + (req.selected_papers or [])
        matched = [p for p in SEEDED_PAPERS if p.id in target_ids]
        if not matched:
            matched = SEEDED_PAPERS[:2]

        idx = 1
        for p in matched:
            paper_metadata.append({"id": p.id, "title": p.title, "journal": p.journal})
            spans = tag_sentences(p.abstract)
            for s in spans:
                passages[f"S{idx}"] = s.text
                idx += 1

    # Check for Gemini AI provider
    if is_gemini_available():
        try:
            ans, cites, conf, grounded, status = generate_gemini_chat(
                query=query,
                passages=passages,
                paper_metadata=paper_metadata,
            )
            return ChatResponse(
                response=ans,
                citations=cites,
                confidence=conf,
                is_grounded=grounded,
                status=status,
                mode=f"gemini_live ({os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')})",
            )
        except Exception as exc:
            return ChatResponse(
                response=f"Error communicating with Gemini AI: {str(exc)}",
                citations=[],
                confidence="Low",
                is_grounded=False,
                status="PROVIDER_ERROR",
                mode="gemini_error",
            )

    # Fallback to Person 4's citation-verified Q&A engine
    chat_result = answer_question(query, passages)
    has_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))
    mode = "live_llm_grounded" if has_key else "deterministic_grounded_engine"

    return ChatResponse(
        response=chat_result.answer,
        citations=chat_result.evidence_passage_ids,
        confidence="High" if chat_result.is_grounded else "Low",
        is_grounded=chat_result.is_grounded,
        status=chat_result.status,
        mode=mode,
    )


@app.post("/api/batch-summarize", response_model=BatchSummarizeResponse)
async def api_batch_summarize(req: BatchSummarizeRequest):
    """Processes multiple research abstracts in a single batch operation with strict isolation."""
    MAX_BATCH_SIZE = 10
    if len(req.papers) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Requested batch size ({len(req.papers)}) exceeds maximum limit of {MAX_BATCH_SIZE} abstracts.",
        )

    start_total = time.perf_counter()
    results = []
    successful = 0
    failed = 0

    for item in req.papers:
        item_id = item.id.strip() or "unknown_id"
        item_title = (item.title or f"Abstract {item_id}").strip()
        abstract_text = item.abstract.strip() if item.abstract else ""

        start_item = time.perf_counter()

        if not abstract_text:
            failed += 1
            elapsed_ms = round((time.perf_counter() - start_item) * 1000.0, 2)
            results.append(
                BatchItemResult(
                    id=item_id,
                    title=item_title,
                    status="error",
                    error_message="Empty or invalid abstract text provided.",
                    processing_time_ms=elapsed_ms,
                )
            )
            continue

        try:
            summary_resp = generate_grounded_summary(
                paper_id=item_id,
                raw_abstract=abstract_text,
                title=item_title,
                depth=req.summary_depth,
                audience=req.audience,
            )
            elapsed_ms = round((time.perf_counter() - start_item) * 1000.0, 2)
            successful += 1
            results.append(
                BatchItemResult(
                    id=item_id,
                    title=item_title,
                    status="success",
                    summary=summary_resp.summary,
                    sentences=summary_resp.sentences,
                    pico=summary_resp.pico,
                    processing_time_ms=elapsed_ms,
                    mode=summary_resp.mode,
                )
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_item) * 1000.0, 2)
            failed += 1
            results.append(
                BatchItemResult(
                    id=item_id,
                    title=item_title,
                    status="error",
                    error_message=f"Summarization processing failed: {str(exc)}",
                    processing_time_ms=elapsed_ms,
                )
            )

    total_time_ms = round((time.perf_counter() - start_total) * 1000.0, 2)
    return BatchSummarizeResponse(
        total=len(req.papers),
        successful=successful,
        failed=failed,
        max_batch_size=MAX_BATCH_SIZE,
        total_time_ms=total_time_ms,
        results=results,
    )


@app.get("/api/eval/metrics")
async def api_get_eval_metrics():
    """Returns empirical benchmark evaluation metrics with full provenance, formulas, and case counts."""
    from eval.validate_real_engine import run_empirical_validation
    res = run_empirical_validation()
    res["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
    return res


@app.post("/api/eval/run")
async def api_run_eval():
    """Executes a live empirical quality benchmark run against the 16-case test suite and returns verified scores."""
    from eval.validate_real_engine import run_empirical_validation
    res = run_empirical_validation()
    res["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
    return res


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
