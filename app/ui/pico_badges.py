"""PICO badge block component for MedPaperPulse-AI.
Renders Population, Intervention, Comparison, and Outcome cards with pastel accents.
"""

from typing import Dict, Optional
import streamlit as st


DEFAULT_PICO = {
    "population": {
        "label": "Population",
        "value": "Adults with solid tumors",
        "detail": "n = 1,284 records",
        "style": "pop",
    },
    "intervention": {
        "label": "Intervention",
        "value": "Neurosymbolic model",
        "detail": "Knowledge graph + LLM",
        "style": "blue",
    },
    "comparison": {
        "label": "Comparison",
        "value": "Standard LLM pipeline",
        "detail": "Retrieval-augmented",
        "style": "mint",
    },
    "outcome": {
        "label": "Outcome",
        "value": "Traceable reasoning",
        "detail": "94% claim linkage",
        "style": "peach",
    },
}


def render_pico_badges(pico_data: Optional[Dict] = None):
    """Renders the 4-quadrant PICO framework badges with clinical styling."""
    data = pico_data or DEFAULT_PICO

    html_cards = []
    for key, info in data.items():
        style_class = info.get("style", "pop")
        label = info.get("label", key.capitalize())
        value = info.get("value", "")
        detail = info.get("detail", "")

        html_cards.append(
            f"""
            <div class="pico-card {style_class}">
                <span class="pico-label">{label}</span>
                <b>{value}</b>
                <small>{detail}</small>
            </div>
            """
        )

    grid_html = f"""
    <div class="pico-grid">
        {"".join(html_cards)}
    </div>
    """
    st.markdown(grid_html, unsafe_allow_html=True)
