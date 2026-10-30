"""Unit tests for pasted and custom abstract parsing with PICO badges."""

import pytest
from app.models import MISSING_INFO_INDICATOR
from app.ingestion.paste_parser import parse_pasted_text


SAMPLE_RCT_TEXT = (
    "Background: SGLT2 inhibitors improve outcomes in chronic kidney disease. "
    "Methods: In this trial, 4,304 patients were assigned to receive dapagliflozin (10 mg daily) or matching placebo. "
    "Results: The primary composite endpoint was reduced by 39% (hazard ratio 0.61; 95% CI, 0.51 to 0.72; p < 0.001). "
    "Conclusions: Dapagliflozin significantly lowered the risk of renal failure in CKD."
)

SAMPLE_PROTOCOL_TEXT = (
    "Background: This is a phase 2 study protocol evaluating a novel oncology agent. "
    "Methods: Enrollment has commenced, but outcome data are not yet analyzed. "
    "Conclusions: Outcomes will be reported upon trial completion."
)


def test_parse_pasted_text_rct():
    sentences, pico = parse_pasted_text(SAMPLE_RCT_TEXT)

    assert len(sentences) == 4
    assert sentences[0].tag == "[S1]"
    assert sentences[1].tag == "[S2]"

    # PICO assertions
    assert "4,304" in pico.population["detail"] or "patients" in pico.population["value"].lower()
    assert "dapagliflozin" in pico.intervention["value"].lower()
    assert "placebo" in pico.comparison["value"].lower()
    assert "reduced" in pico.outcome["value"].lower() or "39%" in pico.outcome["detail"]


def test_parse_pasted_text_protocol_honest_missingness():
    sentences, pico = parse_pasted_text(SAMPLE_PROTOCOL_TEXT)

    assert len(sentences) == 3
    # Honest Missingness Standard: outcome should be marked not reported
    assert pico.outcome["value"] == MISSING_INFO_INDICATOR
    assert "Not reported" in pico.outcome["detail"]


def test_parse_pasted_text_empty_input():
    sentences, pico = parse_pasted_text("")
    assert len(sentences) == 0
    assert pico.population["value"] == MISSING_INFO_INDICATOR
    assert pico.intervention["value"] == MISSING_INFO_INDICATOR
    assert pico.comparison["value"] == MISSING_INFO_INDICATOR
    assert pico.outcome["value"] == MISSING_INFO_INDICATOR
