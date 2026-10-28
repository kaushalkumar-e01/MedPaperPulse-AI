"""Comparison matrix component for MedPaperPulse-AI.
Renders side-by-side clinical evidence matrices with metric comparisons and conflict flags.
"""

from typing import List, Dict, Optional
import streamlit as st

DEFAULT_COMPARISONS = [
    {
        "metric": "Research question",
        "paper1": "Can hybrid models make oncology reasoning more inspectable?",
        "paper2": "Can retrieval improve tumor board synthesis without losing faithfulness?",
        "conflict": False,
    },
    {
        "metric": "Study design",
        "paper1": "Retrospective evaluation · single institution",
        "paper2": "Randomized workflow study · 6 tumor boards",
        "conflict": False,
    },
    {
        "metric": "Sample size",
        "paper1": "1,284 patient records",
        "paper2": "312 cases · 24 clinicians",
        "conflict": False,
    },
    {
        "metric": "Key finding",
        "paper1": "<b>+18.6 pp</b> evidence alignment",
        "paper2": "<b>−31%</b> review time",
        "conflict": True,
        "conflict_label": "Different primary outcome",
    },
    {
        "metric": "Limitation",
        "paper1": "Single institution; retrospective cohort",
        "paper2": "Rare disease cases underrepresented",
        "conflict": False,
    },
]


def render_comparison_matrix(
    paper1_title: str = "Neurosymbolic reasoning for oncology",
    paper1_meta: str = "Mehta et al. · Nature Digital Medicine",
    paper2_title: str = "Retrieval-augmented generation for tumor boards",
    paper2_meta: str = "Chandra et al. · JAMA Network Open",
    comparison_rows: Optional[List[Dict]] = None,
):
    """Renders an editorial clinical side-by-side comparison matrix."""
    rows = comparison_rows or DEFAULT_COMPARISONS

    # Header
    header_html = f"""
    <div class="comparison-container">
        <div class="comp-header">
            <div class="comp-metric">Dimension / Metric</div>
            <div>
                <span class="badge-source">PubMed</span><br/>
                <b>{paper1_title}</b><br/>
                <small style="color: #8c8996;">{paper1_meta}</small>
            </div>
            <div>
                <span class="badge-source">PubMed</span><br/>
                <b>{paper2_title}</b><br/>
                <small style="color: #8c8996;">{paper2_meta}</small>
            </div>
        </div>
    """

    # Rows
    rows_html = []
    for item in rows:
        metric = item.get("metric", "")
        p1 = item.get("paper1", "")
        p2 = item.get("paper2", "")
        conflict_flag = ""
        if item.get("conflict"):
            lbl = item.get("conflict_label", "Different outcome")
            conflict_flag = f'<span class="conflict-badge">⚠️ {lbl}</span>'

        rows_html.append(
            f"""
            <div class="comp-row">
                <div class="comp-metric">{metric} {conflict_flag}</div>
                <div>{p1}</div>
                <div>{p2}</div>
            </div>
            """
        )

    full_html = header_html + "".join(rows_html) + "</div>"
    st.markdown(full_html, unsafe_allow_html=True)

    # Callout banner
    st.markdown(
        """
        <div class="insight-banner">
            <div class="insight-icon">⚡</div>
            <div style="flex: 1;">
                <b style="font-size: 0.95rem; color: #2b2d42;">Comparable enough to synthesize</b>
                <p style="margin: 3px 0 0; font-size: 0.84rem; color: #6d6a78;">
                    Both studies measure clinician trust, but use different primary endpoints (+18.6 pp evidence alignment vs. −31% review time). Keep the distinction visible in your brief.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Proceed to Batch Synthesis →", key="btn_goto_batch", use_container_width=True):
        st.session_state["nav_view"] = "batch"
        st.rerun()
