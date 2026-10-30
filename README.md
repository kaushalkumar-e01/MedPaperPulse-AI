# MedPaperPulse-AI (MedLit Explorer)

> **Clinical literature cockpit for inspectable, traceable, and evidence-grounded medical paper analysis.**

MedPaperPulse-AI is an educational and research-support platform designed to synthesize medical research abstracts from PubMed or user-provided clinical text without inventing facts or distorting scientific uncertainty.

---

## Key Capabilities

- **Evidence-Grounded Synthesis**: Summarizes peer-reviewed medical abstracts using only supplied sentences as evidence.
- **Inspectable Passage Citations**: Every factual claim is linked to explicit sentence tags (`[S1]`, `[S2]`) with interactive source verification.
- **PICO Framework Extraction**: Automatically parses Population, Intervention, Comparison, and Outcome.
- **Honest Missingness Standard**: Missing variables, unstated study designs, or unreported limitations explicitly state `"Not reported in the abstract."`.
- **Quality & Evaluation Suite**: Automated verification of citation resolution, numeric faithfulness, and required-field completeness across a 16-abstract benchmark dataset.
- **Persistent SQLite Caching**: Transparently caches PubMed API queries and records with time-to-live (TTL) expiration.
- **Multi-Study Comparison Matrix**: Dynamic side-by-side study comparison with automated scientific conflict and opposing finding detection.

---

## Project Architecture & Team Roles

| Role | Module | Ownership |
|---|---|---|
| **Person 1** | `app/models.py`, `app/ai/`, `prompts/` | AI Summarization, Shared Pydantic Contracts, Prompt Engineering |
| **Person 2** | `app/ingestion/`, `app/storage/` | PubMed NCBI E-Utilities Ingestion & Persistent SQLite Caching |
| **Person 3** | `frontend/`, `main.py` | React Frontend, FastAPI REST API Bridge & Service Endpoints |
| **Person 4** | `app/citations/`, `app/comparisons/` | Citation Entailment Verification & Cross-Study Comparison Matrix |
| **Person 5** | `data/test_set.json`, `eval/`, `docs/` | Evaluation Dataset, Automated Metrics, LLM Judge, QA & Benchmarking |

---

## Evaluation & Quality Assurance (Person 5)

The evaluation suite validates generated summaries against peer-reviewed publication abstracts and synthetic edge cases.

### Standardized Evaluation Dataset (`data/test_set.json`)
The benchmark contains **16 medical abstracts**:
- **12 Real PubMed Records**: Covering Phase 3 RCTs (Covid-19 vaccine, tirzepatide obesity, dapagliflozin heart failure, pembrolizumab NSCLC), meta-analyses (SGLT2 inhibitors), and diagnostic AI studies.
- **4 Synthetic Edge Cases**: Specifically testing missing results protocols (`SYNTH-01`), contradictory/inconclusive findings (`SYNTH-02`), extreme small sample sizes $n=6$ (`SYNTH-03`), and high-density numerical comparisons (`SYNTH-04`).

### Measured Quality Benchmarks

| Metric | Measured Result | Sample Size | Target |
|---|---|---|---|
| **Citation resolution rate** | **100.0%** | 79 claims evaluated | 95%+ |
| **Numeric faithfulness** | **100.0%** | 47 numeric claims checked | 95%+ |
| **Required-field presence** | **100.0%** | 144 fields evaluated | 90%+ |
| **LLM-judge quality** | **5.0 / 5.0** (mock benchmark) | 16 summaries | 4.0 / 5.0 |
| **Manual review (dual)** | Template seeded | 16 cases seeded in CSV | 8–10 cases |

*Detailed methodology, denominators, and rubrics are documented in [`docs/evaluation.md`](docs/evaluation.md).*

### Running the Evaluation Pipeline

```bash
# Run automated evaluation benchmark (offline deterministic mock)
python -m eval.evaluate --mock --verbose

# Run evaluation with optional LLM judge
python -m eval.evaluate --mock --llm-judge

# Run with live LLM provider (requires GEMINI_API_KEY or OPENAI_API_KEY)
python -m eval.evaluate --live
```

### Running Test Suites

```bash
# Run entire test suite across all modules (87 tests)
pytest -v

# Or run specific test modules
pytest tests/test_models.py tests/test_prompts.py tests/test_summarizer.py -v
pytest tests/test_cache.py tests/test_compare.py tests/test_pubmed_client.py -v
pytest eval/test_eval.py -v
```

---

## How to Run the Application

### 1. Environment Setup
```powershell
# Create and activate virtual environment (if not already done)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
Copy `.env.example` to `.env` and fill in any desired API keys:
```powershell
cp .env.example .env
```
*Note: If no API keys are configured, the system automatically runs in offline deterministic mode with zero hallucination and rule-based evidence synthesis.*

### 3. Start the Backend API Server
```powershell
python main.py
# Or directly via uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Once started, the API and interactive documentation are available at:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Service Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## Manual Review Protocol

A dual-reviewer rubric is established in `eval/manual_review_template.csv`:
1. Two independent reviewers evaluate 8–10 cases across 4 dimensions: Factual Consistency (1–5), Completeness (1–5), Readability (1–5), and Evidence Support (1–5).
2. Reviewers note any ungrounded numerical claims or qualifier shifts.
3. Reviewer discrepancies are adjudicated to establish human-in-the-loop consensus.

---

## Demo Walkthrough

A structured 4–5 minute walkthrough script and recording checklist are available in [`docs/demo_script.md`](docs/demo_script.md).

---

## Clinical Disclaimer & Limitations

> **IMPORTANT**: MedPaperPulse-AI is an **educational and research-support tool** that processes abstract-level literature only. It is **not a medical device, diagnostic system, or treatment recommendation tool**. Always consult full-text peer-reviewed clinical publications and qualified healthcare professionals for medical decisions.
