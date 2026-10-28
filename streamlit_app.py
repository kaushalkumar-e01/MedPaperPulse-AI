"""MedLit Explorer / MedPaperPulse-AI.
Main Streamlit application entry point.
Clinical literature cockpit for inspectable, traceable medical paper analysis.
"""

import streamlit as st
from app.ui.styles import apply_custom_styles
from app.ui.search_cards import render_search_cards_section, DEFAULT_PAPERS
from app.ui.comparison_matrix import render_comparison_matrix
from app.ui.evidence_workspace import render_evidence_workspace
from app.ui.batch_synthesis import render_batch_synthesis
from app.ui.evaluation_lab import render_evaluation_lab
from app.ui.paste_abstract import render_paste_abstract
from app.ui.assistant_dock import render_assistant_dock

# Streamlit Page Setup
st.set_page_config(
    page_title="MedLit Explorer · Clinical Literature Cockpit",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Editorial Clinical CSS Theme
apply_custom_styles()

# Initialize Session State
if "nav_view" not in st.session_state:
    st.session_state["nav_view"] = "explore"
if "selected_papers" not in st.session_state:
    st.session_state["selected_papers"] = ["p1", "p2", "p3"]
if "active_paper_id" not in st.session_state:
    st.session_state["active_paper_id"] = "p1"
if "search_query" not in st.session_state:
    st.session_state["search_query"] = "Neurosymbolic AI in oncology"
if "active_filter" not in st.session_state:
    st.session_state["active_filter"] = "All evidence"


def main():
    # Sidebar Navigation
    with st.sidebar:
        st.markdown(
            """
            <div class="brand-mark">
                <span>medlit<span class="dot">•</span></span>
                <span class="brand-badge">Clinical AI</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("+ New Scan", key="btn_new_scan", use_container_width=True):
            st.session_state["nav_view"] = "explore"
            st.session_state["search_query"] = ""
            st.session_state["active_filter"] = "All evidence"
            st.rerun()

        st.markdown("<p class='eyebrow' style='margin-top:18px;'>Research Desk</p>", unsafe_allow_html=True)

        nav_options = [
            ("explore", "🔍 Explore Literature"),
            ("reader", "📖 Evidence Workspace"),
            ("batch", "🗂️ Batch Synthesis"),
            ("compare", "⚖️ Compare Papers"),
        ]

        current_view = st.session_state["nav_view"]

        for view_key, label in nav_options:
            is_active = (current_view == view_key)
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{view_key}", use_container_width=True, type=btn_type):
                st.session_state["nav_view"] = view_key
                st.rerun()

        st.markdown("<p class='eyebrow' style='margin-top:22px;'>Signal & Tools</p>", unsafe_allow_html=True)
        signal_options = [
            ("qa", "🛡️ Evaluation Lab (QA)"),
            ("paste", "📋 Paste Abstract"),
        ]
        for view_key, label in signal_options:
            is_active = (current_view == view_key)
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{view_key}", use_container_width=True, type=btn_type):
                st.session_state["nav_view"] = view_key
                st.rerun()

        # User profile chip & Sync badge
        st.markdown(
            """
            <div style="margin-top: 40px; padding-top: 16px; border-top: 1px solid #e9e5e1;">
                <div style="font-size:0.75rem; color:#8a8694; display:flex; align-items:center; gap:6px; margin-bottom:12px;">
                    <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#55bd87;"></span>
                    <span>PubMed index synced · <b>18.4k</b> papers</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:32px; height:32px; border-radius:50%; background:#f6ccb8; color:#a64d42; display:grid; place-items:center; font-size:0.75rem; font-weight:700;">
                        AM
                    </div>
                    <div>
                        <b style="font-size:0.82rem; color:#2b2d42;">Alex Morgan</b><br/>
                        <span style="font-size:0.72rem; color:#95919f;">Clinical Fellow</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Topbar breadcrumb
    view_titles = {
        "explore": "Literature Explorer",
        "reader": "Evidence Workspace",
        "batch": "Batch Synthesis",
        "compare": "Compare Papers",
        "qa": "Evaluation Lab (QA)",
        "paste": "Paste Abstract",
    }
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #ebe6e2; padding-bottom:10px; margin-bottom:18px;">
            <div style="font-size:0.8rem; color:#9c97a5;">
                Research Desk / <b style="color:#2b2d42;">{view_titles.get(current_view, 'Workspace')}</b>
            </div>
            <div style="font-size:0.75rem; color:#60ba8d; font-weight:700; text-transform:uppercase; letter-spacing:0.08em;">
                ● Live Evidence Index Active
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Active View Routing
    if current_view == "explore":
        # Hero Section
        st.markdown(
            """
            <div style="margin-bottom: 24px;">
                <span class="section-label coral">Clinical literature, made inspectable</span>
                <h1 style="margin: 4px 0 10px 0;">Find the signal.<br/><i>Keep the evidence.</i></h1>
                <p style="color: #6d6a78; font-size: 1.05rem; max-width: 680px;">
                    MedLit turns dense papers into a traceable research surface — so every useful clinical claim has an verifiable place to land.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Search Panel
        col_q, col_btn = st.columns([4, 1])
        with col_q:
            query = st.text_input(
                "Search query",
                value=st.session_state["search_query"],
                placeholder="Search PubMed, oncology, trials, mechanisms...",
                label_visibility="collapsed",
                key="input_search_query",
            )
            st.session_state["search_query"] = query
        with col_btn:
            if st.button("Explore →", key="btn_run_search", type="primary", use_container_width=True):
                st.session_state["nav_view"] = "explore"
                st.rerun()

        # Preset lenses
        st.markdown("<span style='font-size:0.76rem; color:#8d8997;'>Try a preset lens: </span>", unsafe_allow_html=True)
        l_col1, l_col2, l_col3 = st.columns(3)
        with l_col1:
            if st.button("Neurosymbolic AI in oncology", key="lens1", use_container_width=True):
                st.session_state["search_query"] = "Neurosymbolic AI in oncology"
                st.rerun()
        with l_col2:
            if st.button("Citation faithfulness in clinical LLMs", key="lens2", use_container_width=True):
                st.session_state["search_query"] = "Citation faithfulness in clinical LLMs"
                st.rerun()
        with l_col3:
            if st.button("Tumor board synthesis", key="lens3", use_container_width=True):
                st.session_state["search_query"] = "Tumor board synthesis"
                st.rerun()

        st.markdown("<br/>", unsafe_allow_html=True)

        # Filter Pills
        filter_cols = st.columns([1, 1, 1, 1, 1])
        filters = ["All evidence", "Randomized Trial", "Systematic Review", "PubMed", "arXiv"]
        for idx, f in enumerate(filters):
            with filter_cols[idx]:
                is_selected = (st.session_state["active_filter"] == f)
                btn_type = "primary" if is_selected else "secondary"
                if st.button(f, key=f"filter_{f}", use_container_width=True, type=btn_type):
                    st.session_state["active_filter"] = f
                    st.rerun()

        st.markdown("<br/>", unsafe_allow_html=True)

        # Render Search Results
        render_search_cards_section(
            active_filter=st.session_state["active_filter"],
            search_query=st.session_state["search_query"],
        )

        # Research pulse strip
        st.markdown(
            """
            <div class="insight-banner">
                <div class="insight-icon">⚡</div>
                <div style="flex:1;">
                    <b style="color:#2b2d42; font-size:0.95rem;">Research pulse</b>
                    <p style="margin:2px 0 0 0; font-size:0.85rem; color:#6d6a78;">
                        3 fresh papers match your focus on transparent clinical AI. Your strongest literature overlap is in <b>citation-aware generation.</b>
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif current_view == "reader":
        active_id = st.session_state.get("active_paper_id", "p1")
        matched_paper = next((p for p in DEFAULT_PAPERS if p["id"] == active_id), DEFAULT_PAPERS[0])
        render_evidence_workspace(matched_paper)

    elif current_view == "batch":
        render_batch_synthesis(DEFAULT_PAPERS)

    elif current_view == "compare":
        st.markdown(
            """
            <div style="margin-bottom: 20px;">
                <span class="section-label mint">Side-by-side reading</span>
                <h1 style="margin: 4px 0 6px 0;">Compare the shape <i>of the evidence.</i></h1>
                <p style="color: #7a7786; font-size: 0.95rem;">
                    Two papers, one transparent view of where their methodologies agree — and where outcomes diverge.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_comparison_matrix()

    elif current_view == "qa":
        render_evaluation_lab()

    elif current_view == "paste":
        render_paste_abstract()

    # Grounded Research Assistant Dock
    st.markdown("<br/>", unsafe_allow_html=True)
    render_assistant_dock()

    # Legal & Clinical Disclaimer
    st.markdown(
        """
        <footer class="disclaimer-foot">
            <span>🛡️</span>
            <span>Educational and research aid only — not a diagnostic tool, and not a substitute for qualified clinical judgment.</span>
        </footer>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
