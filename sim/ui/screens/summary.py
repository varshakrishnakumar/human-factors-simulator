"""End-of-session summary screen shown after the survey is submitted. Displays
per-trial outcome badges (completed/timed out/wrong branch) and total error
counts from all_summaries. The rocket animation fires once on page load."""
from typing import Any, Dict, List

import streamlit as st

from sim.ui.widgets import esc, render_notice, render_rocket_celebration, render_section_header


def render() -> None:
    render_rocket_celebration()
    st.markdown('<div class="hf-console-panel">', unsafe_allow_html=True)
    render_section_header("Session complete", "Thanks for participating")

    summaries: List[Dict[str, Any]] = st.session_state.all_summaries
    if not summaries:
        render_notice("No trial summaries recorded.", "warn")
    else:
        for s in summaries:
            tone, label = {
                "completed": ("success", "Completed"),
                "timeout": ("warn", "Timed out"),
                "wrong_branch": ("danger", "Wrong branch"),
                "procedure_end": ("warn", "Procedure ended without target mode"),
            }.get(s["end_reason"], ("info", s["end_reason"]))
            total_errors = (
                s["order_errors"]
                + s["wrong_mode_actions"]
                + s["branch_decision_errors"]
                + s["checklist_selection_error"]
            )
            st.markdown(
                f'<div class="hf-notice hf-notice-{tone}">'
                f'<strong>Trial {s["trial_number"]} — {esc(s["scenario_title"])}</strong><br/>'
                f'Outcome: <strong>{label}</strong> &nbsp;·&nbsp; '
                f'Time: {s["completion_time_s"]:.1f}s &nbsp;·&nbsp; '
                f'Errors: {total_errors}'
                f'</div>',
                unsafe_allow_html=True,
            )

    render_notice(
        "Your responses have been saved. You can close this window.",
        "info",
    )
    st.markdown('</div>', unsafe_allow_html=True)
