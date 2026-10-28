"""Custom styles and theme definitions for MedPaperPulse-AI / MedLit Explorer.
Faithfully mirrors the editorial clinical observatory design from Manus AI.
"""

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..700;1,9..40,400..700&family=Instrument+Serif:ital@0;1&display=swap');

:root {
    --ink: #2b2d42;
    --muted: #8c8b96;
    --line: #e9e5e1;
    --coral: #f26f61;
    --coral-light: #fff0eb;
    --coral-dark: #c76055;
    --lavender: #c9bdf3;
    --lavender-light: #f3efff;
    --sky: #b9d8f4;
    --sky-light: #edf5fc;
    --mint: #b9e4d2;
    --mint-light: #ebf8f2;
    --peach: #f6ccb8;
    --peach-light: #fdf3ed;
    --paper: #fffdfa;
    --surface: #ffffff;
    --bg-warm: #f8f6f3;
}

/* Global Font and Base Styling */
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--ink) !important;
    background-color: var(--bg-warm) !important;
}

/* Headings */
h1, h2, h3, .serif-heading {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-weight: 400 !important;
    color: var(--ink) !important;
}

h1 {
    font-size: 2.8rem !important;
    line-height: 1.15 !important;
}

h2 {
    font-size: 2.1rem !important;
    line-height: 1.2 !important;
}

h3 {
    font-size: 1.45rem !important;
    line-height: 1.3 !important;
}

/* Section labels & eyebrows */
.section-label, .eyebrow {
    display: inline-block;
    color: #9d9aa6;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}

.section-label.coral { color: var(--coral); }
.section-label.sky { color: #3d88c8; }
.section-label.lilac { color: #7f68c9; }
.section-label.mint { color: #2e8a64; }
.section-label.peach { color: #c46d42; }

/* Brand Mark */
.brand-mark {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.05em;
    color: #2b2d42;
    margin-bottom: 1.5rem;
}
.brand-mark span.dot {
    color: var(--coral);
}
.brand-badge {
    background: #2b2d42;
    color: #ffffff;
    font-size: 0.65rem;
    padding: 3px 7px;
    border-radius: 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Paper Card Grid & Individual Card */
.paper-card {
    background: #ffffff;
    border: 1px solid rgba(229, 225, 221, 0.85);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 16px;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(43, 45, 66, 0.03);
    position: relative;
}

.paper-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(43, 45, 66, 0.08);
    border-color: #d8d3ce;
}

.paper-card.lilac { border-top: 3.5px solid var(--lavender); }
.paper-card.peach { border-top: 3.5px solid var(--peach); }
.paper-card.mint  { border-top: 3.5px solid var(--mint); }
.paper-card.sky   { border-top: 3.5px solid var(--sky); }

.paper-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}

.badge-source {
    background: #f4f1ee;
    color: #635f6f;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
}

.badge-type {
    background: #fff;
    color: #7b7786;
    border: 1px solid #e9e5e1;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 2px 7px;
    border-radius: 6px;
}

.paper-title {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.08rem !important;
    font-weight: 600;
    color: #2b2d42;
    line-height: 1.35;
    margin-bottom: 8px;
}

.paper-abstract {
    font-size: 0.86rem;
    color: #6d6a78;
    line-height: 1.5;
    margin-bottom: 14px;
}

.paper-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 0.75rem;
    color: #9a97a3;
    margin-bottom: 12px;
    border-top: 1px dashed #efebe7;
    padding-top: 10px;
}

.paper-card-bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.74rem;
}

.trace-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #fdf3ed;
    color: #b75647;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
}

.id-chip {
    color: #8c8896;
    font-family: monospace;
    font-size: 0.72rem;
}

/* PICO Badges Grid */
.pico-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 18px 0 24px 0;
}

@media (max-width: 900px) {
    .pico-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 500px) {
    .pico-grid { grid-template-columns: 1fr; }
}

.pico-card {
    background: #ffffff;
    border: 1px solid #ece7e3;
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    transition: transform 0.15s ease;
}

.pico-card:hover {
    transform: translateY(-2px);
}

.pico-card.pop {
    background: linear-gradient(180deg, #faf7ff 0%, #ffffff 100%);
    border-top: 3px solid var(--lavender);
}

.pico-card.blue {
    background: linear-gradient(180deg, #f5f9fe 0%, #ffffff 100%);
    border-top: 3px solid var(--sky);
}

.pico-card.mint {
    background: linear-gradient(180deg, #f4fbf8 0%, #ffffff 100%);
    border-top: 3px solid var(--mint);
}

.pico-card.peach {
    background: linear-gradient(180deg, #fef7f2 0%, #ffffff 100%);
    border-top: 3px solid var(--peach);
}

.pico-card span.pico-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9c99a6;
}

.pico-card b {
    font-size: 0.95rem;
    font-weight: 600;
    color: #2b2d42;
    line-height: 1.3;
}

.pico-card small {
    font-size: 0.75rem;
    color: #8c8996;
}

/* Comparison Matrix Table */
.comparison-container {
    background: #ffffff;
    border: 1px solid #e9e5e1;
    border-radius: 14px;
    overflow: hidden;
    margin: 20px 0;
    box-shadow: 0 4px 14px rgba(43, 45, 66, 0.03);
}

.comp-header {
    display: grid;
    grid-template-columns: 1.2fr 2fr 2fr;
    background: #faf7f4;
    border-bottom: 2px solid #e5dfd9;
    padding: 14px 18px;
    font-weight: 600;
}

.comp-row {
    display: grid;
    grid-template-columns: 1.2fr 2fr 2fr;
    padding: 16px 18px;
    border-bottom: 1px solid #f0ece8;
    align-items: center;
    font-size: 0.88rem;
    line-height: 1.45;
}

.comp-row:last-child {
    border-bottom: none;
}

.comp-metric {
    font-weight: 600;
    color: #555261;
}

.conflict-badge {
    display: inline-block;
    background: #feece8;
    color: #c75647;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 5px;
    margin-left: 8px;
}

/* Citation Markers and Sentences */
.sentence-box {
    margin-bottom: 12px;
    line-height: 1.6;
    font-size: 0.92rem;
}

.cite-tag {
    display: inline-block;
    background: #fff0eb;
    color: var(--coral);
    border: 1px solid #fbd2c9;
    font-weight: 700;
    font-size: 0.75rem;
    padding: 1px 6px;
    border-radius: 6px;
    margin-right: 5px;
    cursor: pointer;
}

.cite-pill {
    background: #f26f61;
    color: #fff !important;
    padding: 2px 7px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
    margin: 0 3px;
}

/* Stat Cards */
.stat-card-box {
    background: #ffffff;
    border: 1px solid #ebe6e2;
    border-radius: 12px;
    padding: 18px;
    text-align: left;
    box-shadow: 0 2px 8px rgba(43,45,66,0.03);
}

.stat-val {
    font-size: 2rem;
    font-weight: 700;
    color: #2b2d42;
    line-height: 1.1;
    margin-bottom: 4px;
}

.stat-lbl {
    font-size: 0.78rem;
    color: #7a7786;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}

.stat-det {
    font-size: 0.74rem;
    color: #55bd87;
    font-weight: 500;
}

/* Insight Strip / Banner */
.insight-banner {
    background: linear-gradient(90deg, #fffcf9 0%, #fff6f2 100%);
    border: 1px solid #f6ded5;
    border-radius: 12px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 20px 0;
}

.insight-icon {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: var(--coral);
    color: #ffffff;
    font-weight: 700;
}

/* Disclaimer footer */
.disclaimer-foot {
    margin-top: 40px;
    padding-top: 18px;
    border-top: 1px solid #ece8e4;
    color: #a4a0ac;
    font-size: 0.76rem;
    display: flex;
    align-items: center;
    gap: 7px;
}

/* Sidebar Custom Styling */
[data-testid="stSidebar"] {
    background: rgba(255, 253, 250, 0.95) !important;
    border-right: 1px solid rgba(222, 218, 213, 0.8) !important;
}

/* Button overrides for that crisp editorial look */
.stButton > button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    border: 1px solid #e1dcd7 !important;
    transition: all 0.15s ease !important;
}

.stButton > button:hover {
    border-color: var(--coral) !important;
    color: var(--coral) !important;
}

.stButton > button[kind="primary"] {
    background: var(--coral) !important;
    border-color: var(--coral) !important;
    color: #ffffff !important;
}
</style>
"""


def apply_custom_styles():
    """Injects custom CSS styles into Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
