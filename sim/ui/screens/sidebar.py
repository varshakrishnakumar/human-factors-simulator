"""Sidebar setup panel. Handles participant ID entry, experience selection,
condition assignment (auto-balanced or manual), and the Start session button.
The auto-balanced path calls sinks.balanced_condition() which reads from Sheets
— if Sheets is down it gracefully falls back to the first condition key."""
import streamlit as st

from sim.domain.conditions import BACKGROUND_OPTIONS, CONDITIONS
from sim.io.sinks import balanced_condition
from sim.trial import start_session


def render() -> None:
    st.sidebar.header("Setup")
    if st.session_state.session_started:
        st.sidebar.caption("Session in progress. Reload the page to start a new session.")
        st.sidebar.write(f"**Session ID:** `{st.session_state.session_id}`")
        st.sidebar.write(f"**Participant:** {st.session_state.participant_id}")
        st.sidebar.write(f"**Experience:** {st.session_state.experience}")
        st.sidebar.write(f"**Condition:** {CONDITIONS[st.session_state.condition_key].label}")
        return

    st.session_state.participant_id = st.sidebar.text_input(
        "Participant ID",
        value=st.session_state.participant_id,
    )
    st.session_state.experience = st.sidebar.selectbox(
        "Relevant experience",
        BACKGROUND_OPTIONS,
        index=list(BACKGROUND_OPTIONS).index(st.session_state.experience),
        help="Used to balance assignments across conditions.",
    )

    mode_options = ["auto", "manual"]
    st.session_state.condition_assignment_mode = st.sidebar.radio(
        "Condition assignment",
        mode_options,
        index=mode_options.index(st.session_state.condition_assignment_mode),
        format_func=lambda x: {"auto": "Auto-balanced", "manual": "Manual"}[x],
        help="Auto-balanced reads prior assignments from Google Sheets.",
        horizontal=True,
    )

    condition_keys = list(CONDITIONS.keys())
    if st.session_state.condition_assignment_mode == "auto":
        suggested = balanced_condition(st.session_state.experience, condition_keys)
        st.sidebar.markdown(
            f"**Assigned condition:** `{CONDITIONS[suggested].label}`"
        )
        st.session_state.condition_key = suggested
    else:
        current = st.session_state.condition_key or condition_keys[0]
        if current not in condition_keys:
            current = condition_keys[0]
        st.session_state.condition_key = st.sidebar.selectbox(
            "Condition",
            condition_keys,
            index=condition_keys.index(current),
            format_func=lambda k: CONDITIONS[k].label,
        )

    st.sidebar.markdown("---")
    if st.sidebar.button("Start session", type="primary", use_container_width=True):
        if not st.session_state.participant_id.strip():
            st.sidebar.error("Enter a participant ID first.")
        else:
            start_session()
            st.rerun()
