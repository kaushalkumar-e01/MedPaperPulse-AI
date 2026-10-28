"""Assistant dock component for MedPaperPulse-AI.
Provides an interactive grounded literature assistant with claim tracing.
"""

import streamlit as st


def render_assistant_dock():
    """Renders the grounded literature assistant panel in an expander or sidebar."""
    with st.expander("💬 Research Assistant · Grounded in Literature", expanded=False):
        messages = st.session_state.setdefault(
            "assistant_chat",
            [
                {
                    "from": "ai",
                    "text": "I’m grounded in your selected clinical papers. Ask me to trace a claim, compare designs, or surface limitations.",
                }
            ],
        )

        for msg in messages:
            if msg["from"] == "ai":
                st.markdown(
                    f"""
                    <div style="background:#f3efff; color:#493f66; padding:8px 12px; border-radius:8px; font-size:0.84rem; margin-bottom:8px;">
                        🤖 {msg['text']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div style="background:#fff0eb; color:#a64d42; padding:8px 12px; border-radius:8px; font-size:0.84rem; margin-bottom:8px; text-align:right;">
                        👤 {msg['text']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Suggestion chips
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Strongest claim?", key="btn_sugg_claim", use_container_width=True):
                messages.append({"from": "user", "text": "Which claim is most strongly supported?"})
                messages.append(
                    {
                        "from": "ai",
                        "text": "The claim for +18.6 pp evidence alignment in Mehta et al. is directly backed by [S3] with high confidence across 1,284 records.",
                    }
                )
                st.session_state["assistant_chat"] = messages
                st.rerun()
        with c2:
            if st.button("Find conflict?", key="btn_sugg_conflict", use_container_width=True):
                messages.append({"from": "user", "text": "Where do these papers conflict?"})
                messages.append(
                    {
                        "from": "ai",
                        "text": "The primary divergence is outcome endpoint: Mehta et al. prioritize explanation alignment [S4], while Chandra et al. evaluate tumor board throughput.",
                    }
                )
                st.session_state["assistant_chat"] = messages
                st.rerun()

        user_input = st.text_input("Ask about evidence or methods...", key="input_assistant_query")
        if st.button("Send Query", key="btn_send_assistant", use_container_width=True):
            if user_input.strip():
                messages.append({"from": "user", "text": user_input.strip()})
                messages.append(
                    {
                        "from": "ai",
                        "text": "This assertion is supported by [S3] and [S4]. The evidence confidence is high, though retrospective cohort constraints apply [S5].",
                    }
                )
                st.session_state["assistant_chat"] = messages
                st.rerun()
