import streamlit as st

from sim.domain.survey import COMMENT_KEYS, QUESTIONS
from sim.trial import submit_session_survey
from sim.ui.widgets import esc, render_notice, render_section_header


def _tlx_slider(question_obj) -> int:
    st.markdown(
        f'<div class="hf-tlx-block">'
        f'<div class="hf-tlx-label">{esc(question_obj.label)}</div>'
        f'<div class="hf-tlx-question">{esc(question_obj.question)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    value = st.slider(
        question_obj.label,
        min_value=question_obj.min,
        max_value=question_obj.max,
        value=question_obj.default,
        step=1,
        key=f"tlx_{question_obj.key}",
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="hf-tlx-anchors">'
        f'<span><strong>{question_obj.min}</strong> — {esc(question_obj.low_anchor)}</span>'
        f'<span class="hf-tlx-current">Your rating: <strong>{value}</strong> / {question_obj.max}</span>'
        f'<span><strong>{question_obj.max}</strong> — {esc(question_obj.high_anchor)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    return value


def render() -> None:
    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)
    render_section_header("Workload Survey", "One-time survey covering the whole session")
    render_notice(
        "Reflect on the whole session. The scales are from the NASA Task Load Index "
        "(NASA-TLX). Every slider runs 1 to 10 — the label under each slider tells you "
        "what each end of the scale means. Use the comment boxes to add a sentence or "
        "two of context if you'd like — full sentences are welcome.",
        "info",
    )

    values: dict = {}
    for q in QUESTIONS:
        values[q.key] = _tlx_slider(q)
        # Per-question comment. Comment keys follow the pattern tlx_<suffix>_comment.
        suffix = q.key.replace("nasa_tlx_", "")
        comment_key = f"tlx_{suffix}_comment"
        values[comment_key] = st.text_area(
            f"Anything you'd like to add about {q.label.lower()}?",
            key=comment_key,
        )
    values["general_comment"] = st.text_area(
        "General comments — anything else worth sharing about the experience?",
        key="general_comment",
    )

    if st.button("Submit survey", type="primary", use_container_width=True):
        submit_session_survey(values)
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
