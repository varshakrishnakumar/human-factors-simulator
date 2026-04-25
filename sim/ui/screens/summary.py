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
                "self_terminated": ("info", "Ended by subject"),
            }.get(s["end_reason"], ("info", s["end_reason"]))
            total_errors = (
                s["order_errors"]
                + s["wrong_mode_actions"]
                + s["branch_decision_errors"]
                + s["checklist_selection_error"]
            )

            wrong_mode_names = s.get("wrong_mode_action_names") or []
            order_attempts = s.get("order_error_attempts") or []

            breakdown_parts = []
            if s["wrong_mode_actions"]:
                breakdown_parts.append(
                    f"Wrong mode: {s['wrong_mode_actions']}"
                )
            if s["order_errors"]:
                breakdown_parts.append(f"Order: {s['order_errors']}")
            if s["branch_decision_errors"]:
                breakdown_parts.append(f"Decision: {s['branch_decision_errors']}")
            if s["checklist_selection_error"]:
                breakdown_parts.append("Wrong checklist picked")
            breakdown_html = (
                f"<br/><span style='opacity:0.85; font-size:0.88em;'>"
                f"{esc(' · '.join(breakdown_parts))}</span>"
                if breakdown_parts
                else ""
            )

            details_html = ""
            if wrong_mode_names:
                # Dedupe but preserve order so the subject sees the click order.
                seen = []
                for n in wrong_mode_names:
                    if n not in seen:
                        seen.append(n)
                details_html += (
                    "<div style='margin-top:0.45rem; font-size:0.85em; opacity:0.9;'>"
                    "<strong>Wrong-mode actions</strong> — pressed before the spacecraft "
                    "had transitioned to the mode the procedure expected:<ul style='margin:0.25rem 0 0 1.1rem;'>"
                    + "".join(f"<li>{esc(n)}</li>" for n in seen)
                    + "</ul></div>"
                )
            if order_attempts:
                seen = []
                for n in order_attempts:
                    if n not in seen:
                        seen.append(n)
                details_html += (
                    "<div style='margin-top:0.4rem; font-size:0.85em; opacity:0.9;'>"
                    "<strong>Order errors</strong> — pressed out of sequence or while a decision was pending:"
                    "<ul style='margin:0.25rem 0 0 1.1rem;'>"
                    + "".join(f"<li>{esc(n)}</li>" for n in seen)
                    + "</ul></div>"
                )

            st.markdown(
                f'<div class="hf-notice hf-notice-{tone}">'
                f'<strong>Trial {s["trial_number"]} — {esc(s["scenario_title"])}</strong><br/>'
                f'Outcome: <strong>{label}</strong> &nbsp;·&nbsp; '
                f'Time: {s["completion_time_s"]:.1f}s &nbsp;·&nbsp; '
                f'Errors: {total_errors}'
                f'{breakdown_html}'
                f'{details_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

    render_notice(
        "Your responses have been saved. You can close this window.",
        "info",
    )
    st.markdown('</div>', unsafe_allow_html=True)
