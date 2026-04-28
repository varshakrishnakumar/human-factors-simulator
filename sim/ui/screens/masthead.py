"""Top-of-page masthead bar showing participant, condition, and trial progress.
Renders on every screen once a session has started. It reads from trial.py
accessors rather than session_state directly so it stays decoupled from the
state bridge."""
import streamlit as st

from sim.domain.conditions import CONDITIONS
from sim.trial import current_trial_number, in_familiarization, total_trials
from sim.ui.widgets import esc


def render() -> None:
    participant = st.session_state.participant_id or "—"
    if in_familiarization():
        trial_value = "0 (Sandbox)"
    elif st.session_state.session_started:
        trial_value = f"{current_trial_number()} / {total_trials()}"
    else:
        trial_value = "—"
    condition = (
        CONDITIONS[st.session_state.condition_key].label
        if st.session_state.condition_key
        else "—"
    )
    st.markdown(
        f'<div class="hf-masthead">'
        f'<div>'
        f'<div class="hf-masthead-eyebrow">GNC Recovery Testbed</div>'
        f'<div class="hf-masthead-title">Fault Recovery Experiment</div>'
        f'</div>'
        f'<div class="hf-chip-row">'
        f'<div class="hf-chip"><span class="hf-chip-label">Participant</span>'
        f'<span class="hf-chip-value">{esc(participant)}</span></div>'
        f'<div class="hf-chip"><span class="hf-chip-label">Condition</span>'
        f'<span class="hf-chip-value">{esc(condition)}</span></div>'
        f'<div class="hf-chip"><span class="hf-chip-label">Trial</span>'
        f'<span class="hf-chip-value">{esc(trial_value)}</span></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
