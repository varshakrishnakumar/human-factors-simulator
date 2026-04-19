import streamlit as st

from sim.domain.scenarios.registry import linear_candidates
from sim.trial import current_scenario, picked_linear_checklist, select_linear_checklist
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

    if st.session_state.selected_checklist_id is None:
        _render_linear_picker()
    else:
        _render_linear_progress()

    st.markdown('</div>', unsafe_allow_html=True)


def _render_linear_picker() -> None:
    render_section_header(
        "Select checklist",
        "Match the console indications to one of the three checklists below.",
    )
    for cand in linear_candidates():
        cues_html = " · ".join(
            f'<span style="color:var(--hf-amber); font-family:SFMono-Regular,Menlo,Consolas,monospace;'
            f' font-size:0.72rem; letter-spacing:0.1em;">{esc(c.label)}: {esc(c.value)}</span>'
            for c in cand.trigger_cues
        )
        st.markdown(
            f'<div class="hf-choice-card">'
            f'<div class="hf-choice-title">Checklist {cand.scenario_id} — {esc(cand.title)}</div>'
            f'<div style="margin-bottom:0.3rem;">{cues_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"See all steps for Checklist {cand.scenario_id}"):
            steps_html = "".join(
                f'<div class="hf-choice-step">{i:02d}. {esc(s)}</div>'
                for i, s in enumerate(cand.steps, start=1)
            )
            st.markdown(steps_html, unsafe_allow_html=True)
        if st.button(
            f"Use Checklist {cand.scenario_id}",
            key=f"pick_{cand.scenario_id}",
            use_container_width=True,
        ):
            select_linear_checklist(cand.scenario_id)
            st.rerun()


def _render_linear_progress() -> None:
    picked = picked_linear_checklist()
    if picked is None:
        return
    scenario = current_scenario()
    is_correct_pick = picked["scenario_id"] == scenario["scenario_id"]

    render_section_header(
        "Executing",
        f"Checklist {picked['scenario_id']} — {picked['title']}",
    )
    if not is_correct_pick:
        render_notice(
            "Selected checklist does not match the actual fault. Selection is locked in; "
            "the trial will continue with whatever procedure you chose.",
            "warn",
        )

    expected_step = next(
        (s for s in picked["steps"] if s not in st.session_state.completed_actions),
        None,
    )
    for i, step in enumerate(picked["steps"], start=1):
        if step in st.session_state.completed_actions:
            css = "hf-step-done"
        elif step == expected_step:
            css = "hf-step-current"
        else:
            css = "hf-step-upcoming"
        st.markdown(
            f'<div class="{css}">STEP {i:02d} // {esc(step)}</div>',
            unsafe_allow_html=True,
        )
