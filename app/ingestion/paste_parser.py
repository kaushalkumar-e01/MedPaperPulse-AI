"""Parser for pasted or uploaded abstracts with PICO extraction."""

import re
from typing import Tuple, List
from app.models import SentenceSpan, PicoBadges
from app.ingestion.sentence_tagger import tag_sentences


def parse_pasted_text(text: str) -> Tuple[List[SentenceSpan], PicoBadges]:
    """Processes pasted abstract text, segments sentences, and extracts PICO signals."""
    sentences = tag_sentences(text)

    # Heuristic PICO extraction from sentences
    pop_text = "Clinical cohort"
    pop_detail = "Records analyzed"
    interv_text = "Evaluated intervention"
    interv_detail = "Clinical protocol"
    comp_text = "Baseline comparator"
    comp_detail = "Standard of care"
    out_text = "Clinical endpoints"
    out_detail = "Reported outcomes"

    for span in sentences:
        txt = span.text.lower()
        if any(w in txt for w in ["patient", "adult", "cohort", "participant", "cases", "records"]):
            # Look for sample size
            match = re.search(r"(\d+(?:,\d+)?)\s*(?:patients|records|cases|subjects|participants)", txt)
            if match:
                pop_detail = f"n = {match.group(1)} records"
            pop_text = span.text[:55] + "..." if len(span.text) > 55 else span.text

        if any(w in txt for w in ["model", "architecture", "pipeline", "drug", "treatment", "therapy", "intervention"]):
            interv_text = span.text[:55] + "..." if len(span.text) > 55 else span.text
            interv_detail = "Active method"

        if any(w in txt for w in ["compared", "baseline", "versus", "standard", "control"]):
            comp_text = span.text[:55] + "..." if len(span.text) > 55 else span.text
            comp_detail = "Control cohort"

        if any(w in txt for w in ["improved", "reduced", "rate", "accuracy", "survival", "score", "percentage", "%"]):
            out_text = span.text[:55] + "..." if len(span.text) > 55 else span.text
            if span.numeric_entities:
                out_detail = f"{span.numeric_entities[0]} change"

    pico = PicoBadges(
        population={"label": "Population", "value": pop_text, "detail": pop_detail, "style": "pop"},
        intervention={"label": "Intervention", "value": interv_text, "detail": interv_detail, "style": "blue"},
        comparison={"label": "Comparison", "value": comp_text, "detail": comp_detail, "style": "mint"},
        outcome={"label": "Outcome", "value": out_text, "detail": out_detail, "style": "peach"},
    )

    return sentences, pico
