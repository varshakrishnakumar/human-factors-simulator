import streamlit as st

from sim.trial import advance_after_trial
from sim.ui.widgets import render_notice


def render() -> None:
    render_notice(
        "Practice complete. The real trials each have a time limit — click Start "
        "Trial 1 when you're ready to begin.",
        "success",
    )
    if st.button("Start Trial 1", type="primary", use_container_width=True):
        advance_after_trial()
        st.rerun()
