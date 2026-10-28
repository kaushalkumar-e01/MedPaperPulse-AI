"""Evidence Workspace (Reader) component for MedPaperPulse-AI.
Includes sentence-tagged source viewing, glossary, AI synthesis controls, and citation inspection.
"""

from typing import Dict, Optional
import streamlit as st
from app.ui.pico_badges import render_pico_badges

SAMPLE_SOURCE_SENTENCES = [
    {
        "tag": "[S1]",
        "text": "We evaluated a hybrid architecture that couples a transformer encoder with a domain-specific oncology graph.",
        "category": "Methods · Architecture",
    },
    {
        "tag": "[S2]",
        "text": "The graph contained 48,210 entities across 12 cancer types and 6 treatment pathways.",
        "category": "Methods · Cohort & Data",
    },
    {
        "tag": "[S3]",
        "text": "Compared with a retrieval-only baseline, the hybrid model improved evidence alignment by 18.6 percentage points.",
        "category": "Results · Evidence Alignment",
    },
    {
        "tag": "[S4]",
        "text": "Clinicians rated explanations as more actionable when claims were connected to explicit graph relations.",
        "category": "Results · Clinician Evaluation",
    },
    {
        "tag": "[S5]",
        "text": "The study was limited by retrospective records and a single-institution evaluation cohort.",
        "category": "Discussion · Limitations",
    },
]

GLOSSARY_ITEMS = [
    ("LLM", "Large Language Model"),
    ("RCT", "Randomized Controlled Trial"),
    ("KG", "Knowledge Graph"),
    ("AUC", "Area Under the ROC Curve"),
    ("NLP", "Natural Language Processing"),
]


def render_evidence_workspace(paper: Optional[Dict] = None):
    """Renders the comprehensive two-pane Evidence Workspace."""
    title = paper.get("title", "Neurosymbolic reasoning for multimodal oncology decision support") if paper else "Neurosymbolic reasoning for multimodal oncology decision support"
    meta = paper.get("authors", "Mehta et al.") + " · " + paper.get("journal", "Nature Digital Medicine") + " · " + paper.get("date", "08 Aug 2024") if paper else "Mehta et al. · Nature Digital Medicine · 08 Aug 2024"

    # Header section
    st.markdown(
        f"""
        <div style="margin-bottom: 18px;">
            <span class="section-label lilac">Evidence Workspace · Clinical Reading</span>
            <h1 style="margin: 4px 0 6px 0;">{title}</h1>
            <p style="color: #7a7786; font-size: 0.95rem; margin-bottom: 12px;">{meta}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # PICO Badge Row
    render_pico_badges()

    # Two column layout: Left = Source, Right = AI Synthesis
    col_source, col_ai = st.columns([1, 1], gap="medium")

    with col_source:
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 14px;">
                <div>
                    <span class="eyebrow">Original Source</span>
                    <h3 style="margin: 0;">Abstract</h3>
                </div>
                <span class="badge-source" style="background:#e8f5e9; color:#2e7d32;">✓ Abstract-only</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <p style="color: #635f6f; font-size: 0.88rem; line-height: 1.5; margin-bottom: 14px;">
                <i>Neurosymbolic systems combine learned representations with explicit clinical knowledge to make model outputs inspectable in high-stakes oncology settings.</i>
            </p>
            """,
            unsafe_allow_html=True,
        )

        selected_cite = st.session_state.get("selected_citation", "[S3]")

        # Render sentence list with interactive buttons
        for item in SAMPLE_SOURCE_SENTENCES:
            tag = item["tag"]
            is_active = (selected_cite == tag)
            tag_style = "background: #f26f61; color: white;" if is_active else "background: #fff0eb; color: #f26f61;"

            s_col1, s_col2 = st.columns([0.18, 0.82])
            with s_col1:
                if st.button(tag, key=f"btn_src_{tag}", use_container_width=True):
                    st.session_state["selected_citation"] = tag
                    st.rerun()
            with s_col2:
                st.markdown(
                    f"""
                    <div style="font-size: 0.86rem; color: #3d3b47; padding: 5px 0;">
                        {item['text']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Glossary strip
        st.markdown(
            """
            <div style="margin-top: 18px; padding-top: 14px; border-top: 1px dashed #e5e0dc;">
                <span class="eyebrow">Clinical Glossary (Hover to expand)</span>
                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px;">
            """
            + "".join(
                [
                    f'<span style="background:#f4f1ee; color:#5c5867; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:600; cursor:help;" title="{meaning}">{term}</span>'
                    for term, meaning in GLOSSARY_ITEMS
                ]
            )
            + """
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_ai:
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 14px;">
                <div>
                    <span class="eyebrow">AI Synthesis</span>
                    <h3 style="margin: 0;">What this paper says</h3>
                </div>
                <span class="badge-source">Grounded Pipeline</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Controls cluster
        ctl_col1, ctl_col2 = st.columns([1, 1])
        with ctl_col1:
            summary_length = st.radio(
                "Summary Depth",
                ["Short", "Standard", "Detailed"],
                horizontal=True,
                index=1,
                key="radio_summary_depth",
            )
        with ctl_col2:
            audience = st.radio(
                "Audience Persona",
                ["Beginner", "Student", "Researcher"],
                horizontal=True,
                index=2,
                key="radio_audience",
            )

        # Dynamic synthesis text
        if summary_length == "Short":
            body = "A hybrid language model plus oncology knowledge graph improves evidence alignment and makes reasoning easier to inspect [S3]."
        elif summary_length == "Detailed":
            body = (
                "The authors present a hybrid clinical AI design that pairs a language model with an oncology knowledge graph. "
                "The key contribution is not only stronger empirical alignment, but a verifiable path from prediction to underlying evidence, "
                "with explicit graph relations preserving the audit trail for clinical reviewers [S3]."
            )
        else:
            body = (
                "The authors present a hybrid clinical AI design that pairs a language model with an oncology knowledge graph. "
                "The primary breakthrough is a more legible path from output to evidence [S3]."
            )

        st.markdown(
            f"""
            <div style="background:#ffffff; border:1px solid #ebe6e2; border-radius:12px; padding:18px; margin: 12px 0;">
                <p style="font-size:0.92rem; line-height:1.6; color:#2b2d42; margin-bottom:12px;">
                    {body}
                </p>
                <p style="font-size:0.88rem; line-height:1.55; color:#555260;">
                    For a <b>{audience.lower()}</b> perspective, the practical takeaway is that explicit domain relationships help reviewers understand <i>why</i> a model reached a conclusion [S4].
                </p>
                <div style="background:#fffcf9; border-left:3px solid #f26f61; padding:10px 14px; border-radius:4px; margin-top:14px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#f26f61; font-weight:700; text-transform:uppercase;">
                        <span>🎯 Preserved Evidence Excerpt</span>
                        <span>Confidence: High</span>
                    </div>
                    <div style="font-size:0.86rem; color:#2b2d42; margin-top:4px;">
                        “...improved evidence alignment by 18.6 percentage points.”
                    </div>
                    <small style="color:#8c8996; font-size:0.72rem;">Linked to <b>[S3]</b> · numeric claim strictly preserved</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Citation inspection box
    active_tag = st.session_state.get("selected_citation", "[S3]")
    matched = next((s for s in SAMPLE_SOURCE_SENTENCES if s["tag"] == active_tag), SAMPLE_SOURCE_SENTENCES[2])

    st.markdown(
        f"""
        <div style="background:#fff5f2; border:1px solid #fdd7ce; border-radius:10px; padding:14px 18px; margin-top:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="eyebrow" style="color:#d65143;">Active Citation Inspector: {matched['tag']}</span>
                <span style="font-size:0.72rem; color:#7d7986;">{matched['category']}</span>
            </div>
            <div style="font-size:0.9rem; font-weight:600; color:#2b2d42; margin:6px 0 4px 0;">
                {matched['text']}
            </div>
            <small style="color:#9c97a5;">Source: Mehta et al. (Nature Digital Medicine) · Sentence verification passed</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
