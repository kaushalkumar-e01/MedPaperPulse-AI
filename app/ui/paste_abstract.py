"""Paste Abstract component for MedPaperPulse-AI.
Allows researchers to paste custom text or upload abstracts for immediate citation sentence tagging.
"""

import streamlit as st

SAMPLE_ABSTRACT_TEXT = (
    "Background: Clinical language models are increasingly evaluated for their ability to support evidence synthesis.\n\n"
    "Methods: We tested a citation-aware pipeline across 120 synthetic oncology abstracts and verified claim-to-sentence linkages.\n\n"
    "Results: Sentence tagging retained 96.4% of numeric entities while reducing hallucinated assertions by 22%.\n\n"
    "Conclusion: Traceable citation tags provide an actionable audit trail for clinical researchers."
)


def render_paste_abstract():
    """Renders the paste and upload custom abstract workspace."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <span class="section-label coral">Bring Your Own Evidence</span>
            <h1 style="margin: 4px 0 6px 0;">Paste an abstract.<br/><i>See it clearly.</i></h1>
            <p style="color: #7a7786; font-size: 0.95rem;">
                Drop in a test abstract, synthetic study, or new paper. We will preserve your source text and map claims to exact sentences.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_edit, col_side = st.columns([1.3, 0.7], gap="medium")

    with col_edit:
        uploaded_file = st.file_uploader("Upload .txt file", type=["txt"], key="abstract_file_upload")
        default_val = SAMPLE_ABSTRACT_TEXT
        if uploaded_file is not None:
            try:
                default_val = uploaded_file.read().decode("utf-8")
            except Exception:
                pass

        pasted = st.text_area(
            "Abstract Input",
            value=default_val,
            height=260,
            help="Paste clinical literature abstract here for sentence-level parsing and PICO extraction.",
            key="txt_pasted_abstract",
        )

        word_count = len(pasted.split()) if pasted.strip() else 0
        st.caption(f"Word count: {word_count} words | Max limit: 4,000 words")

        if st.button("🔬 Parse Abstract & Extract Signals →", type="primary", use_container_width=True):
            st.session_state["nav_view"] = "reader"
            st.session_state["pasted_abstract"] = pasted
            st.rerun()

    with col_side:
        st.markdown(
            """
            <div style="background:#ffffff; border:1px solid #ebe6e2; border-radius:12px; padding:20px; height:100%;">
                <span class="eyebrow">Extraction Capabilities</span>
                <h4 style="margin:6px 0 10px 0; color:#2b2d42;">What Happens on Parse</h4>
                <ul style="font-size:0.86rem; color:#605c6c; line-height:1.6; padding-left:18px;">
                    <li><b>Sentence Tagging:</b> Splits abstract into verifiable <code>[S1]...[Sn]</code> spans.</li>
                    <li><b>PICO Extraction:</b> Detects Population, Intervention, Comparison, and Outcomes.</li>
                    <li><b>Numeric Claim Lock:</b> Flags and preserves numeric metrics with zero modification.</li>
                    <li><b>Provenance Audit:</b> All AI summaries remain linked to source sentence tags.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
