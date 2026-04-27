"""Left-column console panel: trigger cues and action buttons. Renders during
every trial (familiarization and real). The action buttons come from
trial.current_action_buttons() — in linear conditions they only appear after
the subject has picked a checklist, so the panel shows a prompt until then."""
import streamlit as st

from sim.domain.action_help import ACTION_HELP
from sim.trial import (
    at_decision_step,
    checklist_type,
    current_action_buttons,
    current_scenario,
    current_trigger_cues,
    end_trial_now,
    execute_action,
    finished,
    in_familiarization,
)
from sim.ui.widgets import render_notice, render_section_header, render_trigger_cues


def render() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-console-panel">', unsafe_allow_html=True)

    render_section_header("Indications", "Trigger cues observed on-console")
    render_trigger_cues(current_trigger_cues())

    render_section_header("Actions", "Click to execute. Buttons stay enabled — think before clicking.")

    ct = checklist_type()
    buttons = current_action_buttons()

    decision_pending = ct == "branching" and at_decision_step()

    if not buttons:
        if ct == "linear" and not in_familiarization():
            render_notice(
                "Select a checklist on the right to enable the action buttons.",
                "info",
            )
    else:
        if decision_pending:
            render_notice(
                "▶ Decision pending — choose an option in the right panel before "
                "pressing any console button.",
                "info",
            )
        cols = st.columns(2)
        for i, action in enumerate(buttons):
            with cols[i % 2]:
                if st.button(
                    action,
                    key=f"btn_{action}",
                    use_container_width=True,
                    help=ACTION_HELP.get(action, ""),
                    disabled=decision_pending,
                ):
                    execute_action(action)
                    st.rerun()

    # Subject-initiated end-of-trial. Hidden during familiarization (practice
    # has its own flow) and once the trial has already finished. Two-step:
    # tick the confirm checkbox, then click the button — keeps a careless
    # click from terminating a trial mid-procedure.
    if not in_familiarization() and not finished():
        st.markdown('<div style="margin-top:1rem; opacity:0.85;">', unsafe_allow_html=True)
        confirm = st.checkbox(
            "I'm done with this trial",
            key="end_trial_confirm",
            help="Tick this and then press End trial to declare yourself done before the timer runs out. "
                 "The trial is recorded with end_reason='self_terminated'.",
        )
        if st.button(
            "End trial",
            key="end_trial_btn",
            disabled=not confirm,
            use_container_width=True,
        ):
            end_trial_now()
            st.session_state["end_trial_confirm"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
