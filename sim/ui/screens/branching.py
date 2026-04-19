import streamlit as st

from sim.domain.models import ActionStep, DecisionStep, TerminalStep
from sim.trial import (
    branch_path,
    branch_step_id,
    current_scenario,
    in_familiarization,
    submit_branching_decision,
)
from sim.ui.widgets import esc, render_notice, render_practice_checklist, render_section_header


def render() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)

    if in_familiarization():
        render_practice_checklist(scenario)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    bc = scenario.branching_checklist
    render_section_header(
        "Branching checklist",
        f"{bc.title} — follow the flow; decisions route you to the next step.",
    )
    render_notice(
        "Each step tells you either to click a console button or to make a decision. "
        "Decisions branch the procedure — follow the routing.",
        "info",
    )

    current_id = branch_step_id()
    path = branch_path()

    for step in bc.steps:
        if isinstance(step, TerminalStep) and step.id not in path:
            continue

        sid = step.id
        step_done = sid in path
        is_current = sid == current_id
        label = f"STEP {sid:02d}"

        if isinstance(step, ActionStep):
            if step_done:
                css = "hf-step-done"
            elif is_current:
                css = "hf-step-current"
            else:
                css = "hf-step-upcoming"
            note_html = f'<span class="hf-step-note">{esc(step.note)}</span>' if step.note else ""
            st.markdown(
                f'<div class="{css}">{label} // {esc(step.text)}{note_html}</div>',
                unsafe_allow_html=True,
            )

        elif isinstance(step, DecisionStep):
            if step_done:
                css = "hf-step-done"
            elif is_current:
                css = "hf-step-current"
            else:
                css = "hf-step-upcoming"
            options_html = "".join(
                f'<div style="margin-top:0.2rem; color:var(--hf-muted); font-size:0.78rem;'
                f' font-family:-apple-system,BlinkMacSystemFont,sans-serif;">'
                f'• {esc(o.label)}'
                + (f' — {esc(o.note)}' if o.note else "")
                + '</div>'
                for o in step.options
            )
            st.markdown(
                f'<div class="{css}">{label} // DECISION: {esc(step.prompt)}{options_html}</div>',
                unsafe_allow_html=True,
            )

            if is_current:
                labels = [o.label for o in step.options]
                key = f"branch_decision_{sid}"
                choice = st.radio("Your choice", labels, key=key, label_visibility="collapsed")
                if st.button(
                    "Submit decision",
                    key=f"submit_decision_{sid}",
                    use_container_width=True,
                ):
                    idx = labels.index(choice)
                    submit_branching_decision(idx)
                    st.rerun()

        elif isinstance(step, TerminalStep):
            st.markdown(
                f'<div class="hf-step-terminal">{label} // {esc(step.text)}'
                + (f'<span class="hf-step-note">{esc(step.note)}</span>' if step.note else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)
