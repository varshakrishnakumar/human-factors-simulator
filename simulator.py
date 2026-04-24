"""Entry point — Streamlit runs this file on every rerun. main() orchestrates
the per-rerun flow: initialise state, inject styles, render sidebar and
masthead, tick the engine clock, then route to the right screen based on where
the session is in the lifecycle (intro → familiarization → trials → survey →
summary). All the actual logic lives in sim/; this file just glues the screens
together in the right order."""
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

from sim.state import init_state, session
from sim.ui.styles import inject_styles
from sim.trial import (
    advance_after_trial,
    checklist_type,
    finished,
    maybe_auto_transition,
    trial_started,
)
from sim.ui.screens import (
    branching, console, familiarization_done, intro, linear,
    masthead, sidebar, status_bar, summary, survey,
)


def _auto_refresh_if_running() -> None:
    """Enable 1-second auto-refresh only while a real (non-familiarization)
    trial is actively running. We skip familiarization because it has no timer
    and the constant rerun would be unnecessary. We also skip after finished()
    to avoid hammering Streamlit once the engine has already persisted."""
    if st_autorefresh is None:
        return
    if not trial_started():
        return
    if finished():
        return
    if session().in_familiarization:
        return
    st_autorefresh(interval=1000, key="trial_timer_autorefresh")


def main() -> None:
    """One call per Streamlit rerun. Sets up the page, ticks the engine,
    and routes to the correct screen. The order matters: init_state() and
    inject_styles() must come first; maybe_auto_transition() must run before
    the finished() check so a timeout triggered on this rerun is handled
    immediately rather than one rerun later."""
    st.set_page_config(page_title="Fault Recovery Experiment", layout="wide")
    init_state()
    inject_styles()

    sidebar.render()
    masthead.render()

    if not session().session_started:
        intro.render()
        st.stop()

    _auto_refresh_if_running()

    maybe_auto_transition()

    if finished() and not session().session_finished:
        # Familiarization: give the subject a moment to start real trials manually.
        # Real trials: auto-advance to the next trial (or the final survey).
        if session().in_familiarization:
            familiarization_done.render()
            return
        advance_after_trial()
        st.rerun()

    if session().session_finished:
        if not session().session_survey_submitted:
            survey.render()
        else:
            summary.render()
        return

    status_bar.render()

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        console.render()
    with right:
        if checklist_type() == "linear":
            linear.render()
        else:
            branching.render()


main()
