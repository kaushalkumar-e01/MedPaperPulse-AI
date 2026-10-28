"""UI components package for MedPaperPulse-AI."""

from app.ui.styles import apply_custom_styles
from app.ui.pico_badges import render_pico_badges
from app.ui.search_cards import render_search_cards_section, render_search_result_card, DEFAULT_PAPERS
from app.ui.comparison_matrix import render_comparison_matrix
from app.ui.evidence_workspace import render_evidence_workspace
from app.ui.batch_synthesis import render_batch_synthesis
from app.ui.evaluation_lab import render_evaluation_lab
from app.ui.paste_abstract import render_paste_abstract
from app.ui.assistant_dock import render_assistant_dock

__all__ = [
    "apply_custom_styles",
    "render_pico_badges",
    "render_search_cards_section",
    "render_search_result_card",
    "render_comparison_matrix",
    "render_evidence_workspace",
    "render_batch_synthesis",
    "render_evaluation_lab",
    "render_paste_abstract",
    "render_assistant_dock",
    "DEFAULT_PAPERS",
]
