"""Right-column checklist panel for branching-condition trials. Walks the full
step list and renders each step type (action, decision, terminal) differently.
Decision steps show a radio + submit button only when they're the current step.
Terminal steps are hidden until the subject reaches them (wrong-branch path).
Also handles familiarization via render_practice_checklist."""
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

        # is_current wins over step_done so a re-routed step (e.g. decision sends
        # you back to an earlier step) renders as current instead of green/done.
        # The "▶" marker is a redundant cue beyond the border-color change so
        # subjects can't miss where the cursor is.
        marker = "▶ " if is_current else ""
        if isinstance(step, ActionStep):
            if is_current:
                css = "hf-step-current"
            elif step_done:
                css = "hf-step-done"
            else:
                css = "hf-step-upcoming"
            note_html = f'<span class="hf-step-note">{esc(step.note)}</span>' if step.note else ""
            expected_mode = scenario.action_expected_modes.get(step.text)
            mode_html = (
                f'<span class="hf-step-mode">Mode {esc(expected_mode)}</span>'
                if expected_mode else ""
            )
            st.markdown(
                f'<div class="{css}">{marker}{label} // {esc(step.text)}{mode_html}{note_html}</div>',
                unsafe_allow_html=True,
            )

        elif isinstance(step, DecisionStep):
            if is_current:
                css = "hf-step-current"
            elif step_done:
                css = "hf-step-done"
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
                f'<div class="{css}">{marker}{label} // DECISION: {esc(step.prompt)}{options_html}</div>',
                unsafe_allow_html=True,
            )

            if is_current:
                labels = [o.label for o in step.options]
                # Key by visit count (path.count(sid) = how many times this
                # decision has been submitted before). Each new visit gets a
                # fresh widget so a stale "No" can't be re-submitted by accident.
                visits = path.count(sid)
                key = f"branch_decision_{sid}_v{visits}"
                choice = st.radio(
                    "Your choice", labels,
                    key=key,
                    index=None,
                    label_visibility="collapsed",
                )
                submit_clicked = st.button(
                    "Submit decision",
                    key=f"submit_decision_{sid}_v{visits}",
                    use_container_width=True,
                    disabled=choice is None,
                )
                if submit_clicked and choice is not None:
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
        # Note: BranchingStep is Union[ActionStep, DecisionStep, TerminalStep].
        # If a new step type is added to the union, extend the dispatch here.

    st.markdown('</div>', unsafe_allow_html=True)
