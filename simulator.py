import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

from sim.state import init_state
from sim.styles import inject_styles
from sim.trial import (
    advance_after_trial,
    checklist_type,
    maybe_auto_transition,
    tick_timer,
)
from sim.views import (
    render_branching_checklist,
    render_console,
    render_familiarization_complete,
    render_final_survey,
    render_intro_instructions,
    render_linear_checklist,
    render_session_summary,
    render_sidebar_setup,
    render_status_bar,
    render_study_header,
)


def _auto_refresh_if_running() -> None:
    if st_autorefresh is None:
        return
    if not st.session_state.trial_started:
        return
    if st.session_state.finished:
        return
    if st.session_state.in_familiarization:
        return
    st_autorefresh(interval=1000, key="trial_timer_autorefresh")


def main() -> None:
    st.set_page_config(page_title="Fault Recovery Experiment", layout="wide")
    init_state()
    inject_styles()

    render_sidebar_setup()
    render_study_header()

    if not st.session_state.session_started:
        render_intro_instructions()
        st.stop()

    _auto_refresh_if_running()

    maybe_auto_transition()
    tick_timer()

    if st.session_state.finished and not st.session_state.session_finished:
        # Familiarization: give the subject a moment to start real trials manually.
        # Real trials: auto-advance to the next trial (or the final survey).
        if st.session_state.in_familiarization:
            render_familiarization_complete()
            return
        advance_after_trial()
        st.rerun()

    if st.session_state.session_finished:
        if not st.session_state.session_survey_submitted:
            render_final_survey()
        else:
            render_session_summary()
        return

    render_status_bar()

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        render_console()
    with right:
        if checklist_type() == "linear":
            render_linear_checklist()
        else:
            render_branching_checklist()


main()
