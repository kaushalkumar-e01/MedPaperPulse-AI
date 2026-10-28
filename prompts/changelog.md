# Prompt Changelog & Version History

This document tracks all versioned prompt changes for the MedPaperPulse-AI / MedLit Explorer summarization engine.

All prompt revisions are deterministic and tracked with semantic version tags. The active prompt version is exported in code via `PROMPT_VERSION` in `app/ai/summarizer.py` and included in `SummaryResult.prompt_version` to support cache-key invalidation (Person 2) and evaluation tracking (Person 5).

---

## [v1.0.0] - 2026-10-28

### Active Version
- **Identifier**: `v1` / `v1.0.0`
- **Files Modified**: `prompts/system_prompt.txt`, `prompts/summary_prompt.txt`
- **Author**: Person 1 (Team Lead & AI/Prompt Engineer)

### Changes Introduced
- Initial baseline clinical prompt release.
- Added explicit source grounding rule: the abstract is the sole source of evidence; no external medical facts may be imported.
- Enforced canonical missing information indicator: `"Not reported in the abstract."` across PICO, study design, and limitations.
- Enforced strict citation contract: every claim in `objective`, `findings`, `conclusion`, and `limitations` must cite verified passage IDs (`S1`, `S2`, etc.) in `supported_by`.
- Prohibited LLM self-validation (`valid` flag is owned by downstream citation engine).
- Added untrusted input / prompt injection mitigation defense.
- Added parameterization for 3 summary lengths (`short`, `standard`, `detailed`) and 3 explanation levels (`beginner`, `student`, `researcher`).
- Structured JSON output contract adhering to Pydantic `SummaryResult` schema.

### Reason for Changes
- Establish reproducible, testable baseline for evidence-based clinical abstract summarization while strictly adhering to shared contracts.

### Evaluation & Test Cases
- Synthetic test suite in `tests/test_prompts.py` and `tests/test_summarizer.py`.
- Evaluated on test cases including:
  1. Synthetic oncology abstract with numerical hazard ratios and confidence intervals.
  2. Inconclusive/null finding abstract with statistical uncertainty.
  3. Abstract with missing limitations and unstated study design.
  4. Adversarial prompt injection payload attempting system override.

### Observed Performance & Limitations
- Baseline implementation. Factual accuracy, citation precision, and hallucination rates will be formally benchmarked by Person 5 (Evaluation Lab) using `data/test_set.json`.
- No unsubstantiated performance claims are asserted prior to formal evaluation benchmarking.

