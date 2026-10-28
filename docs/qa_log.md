# Quality Assurance Bug Log & Cross-Module Defect Tracking

**Owner**: Person 5 (Evaluation & Quality Assurance)  
**Project**: MidPaperPulse-AI (MedLit Explorer)  
**Tracking Period**: October 2026  

This log tracks functional defects, interface mismatches, and integration gaps discovered across project modules. Respecting team ownership boundaries, Person 5 logs issues and suggests corrective actions without altering teammate-owned files.

---

### Defect Log

#### [BUG-001] Streamlit UI Uses Hardcoded Mock Papers Instead of Dynamic Ingestion
- **Date**: 2026-10-28
- **Severity**: Medium
- **Responsible Module / Owner**: `app/ui/` / Person 3 (Streamlit UI)
- **Reproduction Steps**:
  1. Launch `streamlit run streamlit_app.py`.
  2. Navigate to "Explore Literature".
  3. Enter any novel search query (e.g., "Immunotherapy in melanoma").
- **Expected Behavior**: UI should trigger Person 2's PubMed ingestion client (`pubmed_client.py`) and dynamically render retrieved `PaperRecord` objects.
- **Actual Behavior**: UI displays hardcoded static cards defined in `DEFAULT_PAPERS` (`app/ui/search_cards.py`).
- **Evidence**: `DEFAULT_PAPERS` in `app/ui/search_cards.py` contains static dictionary fixtures (`p1`, `p2`, `p3`).
- **Status**: Open
- **Suggested Next Action**: Person 3 should hook the search bar callback to Person 2's `pubmed_client.search_and_fetch()` function once Person 2's implementation is finalized.

---

#### [BUG-002] Ingestion Client and SQLite Cache Files Are Skeleton Placeholders
- **Date**: 2026-10-28
- **Severity**: High (Blocking Full End-to-End Dynamic Integration)
- **Responsible Module / Owner**: `app/ingestion/`, `app/storage/` / Person 2 (Ingestion & Storage)
- **Reproduction Steps**:
  1. Inspect `app/ingestion/pubmed_client.py`, `app/ingestion/xml_parser.py`, and `app/storage/cache.py`.
  2. Attempt to query PubMed programmatically.
- **Expected Behavior**: Modules should download XML from NCBI E-utilities, tag sentences (`S1`, `S2`), and cache records into SQLite.
- **Actual Behavior**: The files exist as 0-byte skeleton placeholders.
- **Evidence**: `app/ingestion/pubmed_client.py` length is 0 bytes.
- **Status**: Open (Pending Person 2 Implementation)
- **Suggested Next Action**: Person 2 to implement `PubMedClient` returning validated `PaperRecord` instances conforming to `app/models.py`.

---

#### [BUG-003] Citation Engine Coverage Field Uncalculated Prior to Person 4 Integration
- **Date**: 2026-10-28
- **Severity**: Low
- **Responsible Module / Owner**: `app/citations/` / Person 4 (Citation Validation)
- **Reproduction Steps**:
  1. Run `summarize_paper(paper)`.
  2. Inspect `summary.coverage` and `claim.valid`.
- **Expected Behavior**: Synthesized summaries should show validated citations with a calculated `coverage` percentage (0.0 to 1.0).
- **Actual Behavior**: Summarizer correctly initializes `coverage=0.0` and `valid=False` to prevent LLM self-validation, awaiting Person 4's citation engine to compute authoritative scores.
- **Evidence**: `app/models.py` sets `valid: bool = False`, and `app/ai/summarizer.py` sets `coverage = 0.0`.
- **Status**: By Design / Awaiting Person 4 Integration
- **Suggested Next Action**: Person 4 to implement `validate_citations(paper, summary)` to update `claim.valid` and `summary.coverage`.

---

#### [BUG-004] Missing `pytest` in Base `requirements.txt`
- **Date**: 2026-10-28
- **Severity**: Low
- **Responsible Module / Owner**: Infrastructure / Project Lead
- **Reproduction Steps**:
  1. Read `requirements.txt`.
  2. Notice that `pytest` is absent from dependencies.
- **Expected Behavior**: Test runner dependency (`pytest>=8.0.0`) should be documented in project requirements for reproducible evaluation runs.
- **Actual Behavior**: Only `streamlit`, `pandas`, `pydantic`, `requests`, and `python-dotenv` are listed.
- **Status**: Reported in `docs/approach.md` and `docs/qa_log.md`
- **Suggested Next Action**: Update `requirements.txt` or create `requirements-dev.txt` including `pytest>=8.0.0`.

---

### QA Test Execution Summary

| Test Suite | Execution Command | Result | Pass Rate |
|---|---|---|---|
| **Shared Models** | `pytest tests/test_models.py` | 12 / 12 Passed | 100% |
| **Prompts & Grounding** | `pytest tests/test_prompts.py` | 5 / 5 Passed | 100% |
| **AI Summarizer** | `pytest tests/test_summarizer.py` | 14 / 14 Passed | 100% |
| **Evaluation Metrics & Judge** | `pytest eval/test_eval.py` | 11 / 11 Passed | 100% |
| **Standardized Dataset Run** | `python -m eval.evaluate --mock` | 16 / 16 Evaluated | 100% |
