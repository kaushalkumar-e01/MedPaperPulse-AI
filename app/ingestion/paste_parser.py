"""Parser for pasted or uploaded abstracts with PICO extraction and honest missingness."""

from __future__ import annotations

import re
from typing import Tuple, List
from app.models import SentenceSpan, PicoBadges, MISSING_INFO_INDICATOR
from app.ingestion.sentence_tagger import tag_sentences


def _clean_pico_val(text: str, max_len: int = 120) -> str:
    """Strips leading section labels and formats snippet cleanly without mid-word truncation."""
    cleaned = re.sub(r"^(?:background|methods|results|conclusions?|objective):\s*", "", text.strip(), flags=re.IGNORECASE)
    if len(cleaned) > max_len:
        truncated = cleaned[:max_len]
        if " " in truncated:
            return truncated.rsplit(" ", 1)[0] + "..."
        return truncated + "..."
    return cleaned


def parse_pasted_text(text: str) -> Tuple[List[SentenceSpan], PicoBadges]:
    """Processes pasted abstract text, segments sentences, and extracts PICO signals."""
    sentences = tag_sentences(text)

    # Missing info defaults following project Honest Missingness Standard
    pop_text: str = ""
    pop_detail: str = "Unstated in abstract"
    interv_text: str = ""
    interv_detail: str = "Unstated in abstract"
    comp_text: str = ""
    comp_detail: str = "Unstated in abstract"
    out_text: str = ""
    out_detail: str = "Unstated in abstract"

    full_lower = text.lower()

    # Detect if abstract is an uncompleted protocol or missing results
    is_protocol = any(
        w in full_lower
        for w in [
            "trial protocol",
            "study protocol",
            "enrollment has commenced, but outcome data are not yet",
            "enrollment is ongoing",
            "outcomes will be reported upon trial completion",
            "results are pending",
            "outcome data are not yet analyzed",
        ]
    )

    for span in sentences:
        txt = span.text
        txt_l = txt.lower()

        # 1. Population extraction
        if not pop_text or pop_detail == "Unstated in abstract":
            if any(w in txt_l for w in ["patient", "adult", "cohort", "participant", "cases", "records", "persons"]):
                n_match = re.search(r"(?:total of\s*|randomized\s*|assigned\s*)?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{2,7})\s*(?:participants|patients|adults|records|cases|subjects|persons)", txt_l)
                if not n_match:
                    n_match = re.search(r"n\s*=\s*([0-9,]+)", txt_l)
                if n_match:
                    pop_detail = f"n = {n_match.group(1)} records"
                else:
                    pop_detail = "Target cohort"
                pop_text = _clean_pico_val(txt)

        # 2. Intervention extraction
        if not interv_text or interv_detail == "Unstated in abstract":
            if any(w in txt_l for w in ["assigned to receive", "evaluated", "administered", "treated with", "dose", "vaccine", "model", "therapy", "intervention", "drug"]):
                interv_text = _clean_pico_val(txt)
                interv_detail = "Active protocol"

        # 3. Comparison extraction
        if not comp_text or comp_detail == "Unstated in abstract":
            if any(w in txt_l for w in ["placebo", "control", "versus", "standard of care", "comparator", "chemotherapy"]):
                if "placebo" in txt_l:
                    comp_text = "Placebo control"
                    comp_detail = "Placebo comparator"
                elif "usual care" in txt_l or "standard of care" in txt_l:
                    comp_text = "Standard of care"
                    comp_detail = "Standard comparator"
                else:
                    comp_text = _clean_pico_val(txt)
                    comp_detail = "Control cohort"

        # 4. Outcome extraction (if not a pure protocol without results)
        if not is_protocol:
            if not out_text or out_detail == "Unstated in abstract":
                if any(w in txt_l for w in ["efficacy", "incidence", "reduced", "improved", "hazard ratio", "survival", "percentage", "%", "p<", "p="]):
                    out_text = _clean_pico_val(txt)
                    if span.numeric_entities:
                        out_detail = f"{span.numeric_entities[0]} reported"
                    else:
                        out_detail = "Primary endpoint"

    if is_protocol or not out_text:
        out_text = MISSING_INFO_INDICATOR
        out_detail = "Not reported in abstract"

    if not pop_text:
        pop_text = MISSING_INFO_INDICATOR
    if not interv_text:
        interv_text = MISSING_INFO_INDICATOR
    if not comp_text:
        comp_text = MISSING_INFO_INDICATOR

    pico = PicoBadges(
        population={"label": "Population", "value": pop_text, "detail": pop_detail, "style": "pop"},
        intervention={"label": "Intervention", "value": interv_text, "detail": interv_detail, "style": "blue"},
        comparison={"label": "Comparison", "value": comp_text, "detail": comp_detail, "style": "mint"},
        outcome={"label": "Outcome", "value": out_text, "detail": out_detail, "style": "peach"},
    )

    return sentences, pico
