import streamlit as st

from sim.domain.action_help import ACTION_HELP
from sim.trial import checklist_type, current_action_buttons, current_scenario, execute_action, in_familiarization
from sim.ui.widgets import render_notice, render_section_header, render_trigger_cues


def render() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-console-panel">', unsafe_allow_html=True)

    render_section_header("Indications", "Trigger cues observed on-console")
    render_trigger_cues(scenario.trigger_cues)

    render_section_header("Actions", "Click to execute. Buttons stay enabled — think before clicking.")

    ct = checklist_type()
    buttons = current_action_buttons()

    if not buttons:
        if ct == "linear" and not in_familiarization():
            render_notice(
                "Select a checklist on the right to enable the action buttons.",
                "warn",
            )
    else:
        cols = st.columns(2)
        for i, action in enumerate(buttons):
            with cols[i % 2]:
                if st.button(
                    action,
                    key=f"btn_{action}",
                    use_container_width=True,
                    help=ACTION_HELP.get(action, ""),
                ):
                    execute_action(action)
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
