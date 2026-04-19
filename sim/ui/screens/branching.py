import streamlit as st

from sim.trial import current_scenario, submit_branching_decision
from sim.ui.widgets import esc, render_notice, render_practice_checklist, render_section_header


def render() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)

    if st.session_state.in_familiarization:
        render_practice_checklist(scenario)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    bc = scenario["branching_checklist"]
    render_section_header(
        "Branching checklist",
        f"{bc['title']} — follow the flow; decisions route you to the next step.",
    )
    render_notice(
        "Each step tells you either to click a console button or to make a decision. "
        "Decisions branch the procedure — follow the routing.",
        "info",
    )

    current_id = st.session_state.branch_step_id

    for step in bc["steps"]:
        if step.get("type") == "terminal" and step["id"] not in st.session_state.branch_path:
            continue

        sid = step["id"]
        step_done = sid in st.session_state.branch_path
        is_current = sid == current_id
        step_type = step.get("type")
        label = f"STEP {sid:02d}"

        if step_type == "action":
            if step_done:
                css = "hf-step-done"
            elif is_current:
                css = "hf-step-current"
            else:
                css = "hf-step-upcoming"
            note = step.get("note", "")
            note_html = f'<span class="hf-step-note">{esc(note)}</span>' if note else ""
            st.markdown(
                f'<div class="{css}">{label} // {esc(step["text"])}{note_html}</div>',
                unsafe_allow_html=True,
            )

        elif step_type == "decision":
            if step_done:
                css = "hf-step-done"
            elif is_current:
                css = "hf-step-current"
            else:
                css = "hf-step-upcoming"
            options_html = "".join(
                f'<div style="margin-top:0.2rem; color:var(--hf-muted); font-size:0.78rem;'
                f' font-family:-apple-system,BlinkMacSystemFont,sans-serif;">'
                f'• {esc(o["label"])}'
                + (f' — {esc(o["note"])}' if o.get("note") else "")
                + '</div>'
                for o in step["options"]
            )
            st.markdown(
                f'<div class="{css}">{label} // DECISION: {esc(step["prompt"])}{options_html}</div>',
                unsafe_allow_html=True,
            )

            if is_current:
                labels = [o["label"] for o in step["options"]]
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

        elif step_type == "terminal":
            st.markdown(
                f'<div class="hf-step-terminal">{label} // {esc(step["text"])}'
                + (f'<span class="hf-step-note">{esc(step.get("note",""))}</span>' if step.get("note") else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)
