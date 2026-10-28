"""Search results and literature cards component for MedPaperPulse-AI.
Includes search input, preset lenses, filter pills, and paper cards.
"""

from typing import List, Dict, Optional, Callable
import streamlit as st

DEFAULT_PAPERS: List[Dict] = [
    {
        "id": "p1",
        "title": "Neurosymbolic reasoning for multimodal oncology decision support",
        "authors": "A. Mehta · L. Solberg · K. Ito",
        "journal": "Nature Digital Medicine",
        "date": "08 Aug 2024",
        "type": "Systematic Review",
        "source": "PubMed",
        "tag": "High traceability",
        "tone": "lilac",
        "pmid_doi": "PMID · 39240188",
        "abstract": "Neurosymbolic architectures combine learned representations with explicit clinical knowledge graphs to support transparent oncology reasoning.",
    },
    {
        "id": "p2",
        "title": "Retrieval-augmented generation for longitudinal tumor board synthesis",
        "authors": "R. Chandra · M. Okafor · E. Lin",
        "journal": "JAMA Network Open",
        "date": "21 Jul 2024",
        "type": "Randomized Trial",
        "source": "PubMed",
        "tag": "Numeric review",
        "tone": "peach",
        "pmid_doi": "PMID · 39011923",
        "abstract": "A retrieval-grounded assistant reduced review time while maintaining agreement with multidisciplinary tumor board recommendations.",
    },
    {
        "id": "p3",
        "title": "Clinical language models and the anatomy of trustworthy citations",
        "authors": "S. Weber · N. Alvarez",
        "journal": "arXiv preprint",
        "date": "02 Jun 2024",
        "type": "Methods Paper",
        "source": "arXiv",
        "tag": "Methods",
        "tone": "mint",
        "pmid_doi": "DOI · 10.48550/arXiv.2406.118",
        "abstract": "Citation-aware generation can expose unsupported claims when source spans are preserved through the summarization pipeline.",
    },
]


def render_search_result_card(
    paper: Dict,
    on_open_reader: Optional[Callable[[str], None]] = None,
    on_toggle_select: Optional[Callable[[str], None]] = None,
    is_selected: bool = False,
):
    """Renders an individual paper card with clinical metadata and actions."""
    card_html = f"""
    <div class="paper-card {paper.get('tone', 'lilac')}">
        <div class="paper-card-top">
            <span class="badge-source">{paper.get('source', 'PubMed')}</span>
            <span class="badge-type">{paper.get('type', 'Article')}</span>
        </div>
        <div class="paper-title">{paper.get('title', '')}</div>
        <div class="paper-abstract">{paper.get('abstract', '')}</div>
        <div class="paper-meta">
            <span>👤 {paper.get('authors', '')}</span>
            <span>📖 {paper.get('journal', '')}</span>
            <span>📅 {paper.get('date', '')}</span>
        </div>
        <div class="paper-card-bottom">
            <span class="trace-chip">🛡️ {paper.get('tag', 'Faithful')}</span>
            <span class="id-chip">{paper.get('pmid_doi', '')}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📖 Inspect in Workspace", key=f"btn_reader_{paper['id']}", use_container_width=True):
            if on_open_reader:
                on_open_reader(paper["id"])
            st.session_state["active_paper_id"] = paper["id"]
            st.session_state["nav_view"] = "reader"
            st.rerun()

    with col2:
        btn_label = "✓ In Compare List" if is_selected else "+ Add to Compare"
        if st.button(btn_label, key=f"btn_sel_{paper['id']}", use_container_width=True):
            if on_toggle_select:
                on_toggle_select(paper["id"])
            else:
                sel = st.session_state.setdefault("selected_papers", ["p1", "p2"])
                if paper["id"] in sel:
                    sel.remove(paper["id"])
                else:
                    sel.append(paper["id"])
                st.session_state["selected_papers"] = sel
            st.rerun()


def render_search_cards_section(
    papers: Optional[List[Dict]] = None,
    active_filter: str = "All evidence",
    search_query: str = "",
):
    """Renders the full literature exploration section with filter pills and paper cards."""
    paper_list = papers or DEFAULT_PAPERS

    # Filter logic
    filtered = []
    for p in paper_list:
        if active_filter != "All evidence":
            if p.get("type") != active_filter and p.get("source") != active_filter:
                continue
        if search_query.strip():
            q = search_query.strip().lower()
            if q not in p.get("title", "").lower() and q not in p.get("abstract", "").lower():
                continue
        filtered.append(p)

    selected_ids = st.session_state.get("selected_papers", ["p1", "p2"])

    if not filtered:
        st.info("No papers match your search and filter criteria. Try selecting 'All evidence' or clearing search.")
        return

    for paper in filtered:
        render_search_result_card(
            paper,
            is_selected=(paper["id"] in selected_ids),
        )
