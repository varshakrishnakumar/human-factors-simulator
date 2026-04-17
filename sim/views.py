from typing import Any, Dict, List

import streamlit as st

from sim.components import (
    esc,
    render_action_help,
    render_fault,
    render_live_timer,
    render_mode_badge,
    render_notice,
    render_rocket_celebration,
    render_section_header,
    render_trigger_cues,
)
from sim.config import ACTION_HELP, BACKGROUND_OPTIONS, CONDITIONS
from sim.scenarios import linear_candidates
from sim.sinks import balanced_condition
from sim.trial import (
    advance_after_trial,
    checklist_type,
    current_action_buttons,
    current_scenario,
    current_time_limit,
    current_trial_number,
    execute_action,
    picked_linear_checklist,
    remaining_time,
    select_linear_checklist,
    start_session,
    submit_branching_decision,
    submit_session_survey,
    total_trials,
)


# ----- Top-of-page -------------------------------------------------------

def render_study_header() -> None:
    participant = st.session_state.participant_id or "—"
    if st.session_state.in_familiarization:
        trial_value = "Practice"
    elif st.session_state.session_started:
        trial_value = f"{current_trial_number()} / {total_trials()}"
    else:
        trial_value = "—"
    condition = (
        CONDITIONS[st.session_state.condition_key]["label"]
        if st.session_state.condition_key
        else "—"
    )

    st.markdown(
        f'<div class="hf-masthead">'
        f'<div class="hf-masthead-eyebrow">GNC Recovery Testbed</div>'
        f'<div class="hf-masthead-title">Fault Recovery Experiment</div>'
        f'<div class="hf-chip-row">'
        f'<div class="hf-chip"><div class="hf-chip-label">Participant</div>'
        f'<div class="hf-chip-value">{esc(participant)}</div></div>'
        f'<div class="hf-chip"><div class="hf-chip-label">Condition</div>'
        f'<div class="hf-chip-value">{esc(condition)}</div></div>'
        f'<div class="hf-chip"><div class="hf-chip-label">Trial</div>'
        f'<div class="hf-chip-value">{esc(trial_value)}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ----- Sidebar -----------------------------------------------------------

def render_sidebar_setup() -> None:
    st.sidebar.header("Setup")
    if st.session_state.session_started:
        st.sidebar.caption("Session in progress. Reload the page to start a new session.")
        st.sidebar.write(f"**Session ID:** `{st.session_state.session_id}`")
        st.sidebar.write(f"**Participant:** {st.session_state.participant_id}")
        st.sidebar.write(f"**Experience:** {st.session_state.experience}")
        st.sidebar.write(f"**Condition:** {CONDITIONS[st.session_state.condition_key]['label']}")
        return

    st.session_state.participant_id = st.sidebar.text_input(
        "Participant ID",
        value=st.session_state.participant_id,
    )
    st.session_state.experience = st.sidebar.selectbox(
        "Relevant experience",
        BACKGROUND_OPTIONS,
        index=BACKGROUND_OPTIONS.index(st.session_state.experience),
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
            f"**Assigned condition:** `{CONDITIONS[suggested]['label']}`"
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
            format_func=lambda k: CONDITIONS[k]["label"],
        )

    st.sidebar.markdown("---")
    if st.sidebar.button("Start session", type="primary", use_container_width=True):
        if not st.session_state.participant_id.strip():
            st.sidebar.error("Enter a participant ID first.")
        else:
            start_session()
            st.rerun()


# ----- Intro -------------------------------------------------------------

def render_intro_instructions() -> None:
    render_notice(
        "Enter a participant ID and experience level in the sidebar, then click "
        "Start session. You'll begin with a short practice run before three recovery trials. "
        "A final workload survey follows the last trial.",
        "info",
    )


# ----- Console -----------------------------------------------------------

def render_console() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-console-panel">', unsafe_allow_html=True)

    render_live_timer(remaining_time(), current_time_limit())
    render_mode_badge(st.session_state.mode)
    render_fault(scenario["fault"])

    render_section_header("Indications", "Trigger cues observed on-console")
    render_trigger_cues(scenario["trigger_cues"])

    render_section_header("Actions", "Click to execute. Buttons stay enabled — think before clicking.")

    ct = checklist_type()
    buttons = current_action_buttons()

    if not buttons:
        if ct == "linear" and not st.session_state.in_familiarization:
            render_notice(
                "Select a checklist on the right to enable the action buttons.",
                "warn",
            )
    else:
        cols = st.columns(2)
        for i, action in enumerate(buttons):
            with cols[i % 2]:
                if st.button(action, key=f"btn_{action}", use_container_width=True):
                    execute_action(action)
                    st.rerun()
                render_action_help(ACTION_HELP.get(action, ""))

    st.markdown('</div>', unsafe_allow_html=True)


# ----- Linear checklist --------------------------------------------------

def render_linear_checklist() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)

    if st.session_state.in_familiarization:
        _render_practice_checklist(scenario)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if st.session_state.selected_checklist_id is None:
        _render_linear_picker()
    else:
        _render_linear_progress()

    st.markdown('</div>', unsafe_allow_html=True)


def _render_practice_checklist(scenario: Dict[str, Any]) -> None:
    render_section_header("Practice", "Warm up before the real trials")
    render_notice(
        "This is a practice run. There is one step: click ACK PRACTICE ALERT on the "
        "console to acknowledge. No timer, no scoring.",
        "info",
    )
    step = scenario["linear_checklist"]["steps"][0]
    done = step in st.session_state.completed_actions
    css = "hf-step-done" if done else "hf-step-current"
    st.markdown(
        f'<div class="{css}">STEP 01 // {esc(step)}</div>',
        unsafe_allow_html=True,
    )


def _render_linear_picker() -> None:
    render_section_header(
        "Select checklist",
        "Which checklist matches the indications on the console?",
    )
    render_notice(
        "Three candidate procedures are shown. Compare the console indications to each "
        "checklist, then commit to one. Once selected, the console action buttons will activate.",
        "info",
    )

    candidates = linear_candidates()
    for cand in candidates:
        cues_html = "".join(
            f'<span style="color:var(--hf-amber); font-family:SFMono-Regular,Menlo,Consolas,monospace;'
            f' font-size:0.72rem; letter-spacing:0.1em; margin-right:0.6rem;">'
            f'{esc(c["label"])}: {esc(c["value"])}</span>'
            for c in cand["trigger_cues"]
        )
        steps_html = "".join(
            f'<div class="hf-choice-step">{i:02d}. {esc(s)}</div>'
            for i, s in enumerate(cand["steps"], start=1)
        )
        st.markdown(
            f'<div class="hf-choice-card">'
            f'<div class="hf-choice-title">Checklist {cand["scenario_id"]} — {esc(cand["title"])}</div>'
            f'<div style="margin-bottom:0.45rem;">{cues_html}</div>'
            f'{steps_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            f"Use Checklist {cand['scenario_id']}",
            key=f"pick_{cand['scenario_id']}",
            use_container_width=True,
        ):
            select_linear_checklist(cand["scenario_id"])
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


# ----- Branching checklist ----------------------------------------------

def render_branching_checklist() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)

    if st.session_state.in_familiarization:
        _render_practice_checklist(scenario)
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


# ----- Per-trial completion banner --------------------------------------

def render_trial_complete() -> None:
    scenario = current_scenario()
    reason = st.session_state.end_reason or "completed"
    completion_s = st.session_state.completion_time or 0

    if st.session_state.in_familiarization:
        render_notice(
            "Practice complete. When you're ready, start the first real trial.",
            "success",
        )
        if st.button("Start Trial 1", type="primary", use_container_width=True):
            advance_after_trial()
            st.rerun()
        return

    label_by_reason = {
        "completed": ("Trial complete", "success"),
        "timeout": ("Time expired", "warn"),
        "wrong_branch": ("Procedure ended — wrong branch taken", "danger"),
        "procedure_end": ("Procedure ended — desired mode not reached", "warn"),
    }
    label, tone = label_by_reason.get(reason, ("Trial ended", "info"))
    render_notice(
        f"{label} · {scenario['title']} · {completion_s:.1f}s elapsed",
        tone,
    )

    is_last = current_trial_number() >= total_trials()
    button_label = "Continue to workload survey" if is_last else f"Start Trial {current_trial_number() + 1}"
    if st.button(button_label, type="primary", use_container_width=True):
        advance_after_trial()
        st.rerun()


# ----- Final survey (post-session) --------------------------------------

def render_final_survey() -> None:
    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)
    render_section_header("Workload Survey", "One-time survey covering the whole session")

    render_notice(
        "Now that the trials are finished, please reflect on the whole session. "
        "The questions below are from the NASA Task Load Index (NASA-TLX). Use the "
        "sliders to rate how hard the task felt overall. Feel free to add a sentence "
        "or two of context in the comment boxes — full sentences are welcome.",
        "info",
    )

    st.markdown("**Mental demand — How mentally demanding was the task?**")
    mental = st.slider(
        "Mental demand",
        1, 10, 5,
        help="1 = very low (easy to think through), 10 = very high (had to concentrate hard).",
        label_visibility="collapsed",
    )
    mental_comment = st.text_area(
        "Anything you'd like to add about mental demand?",
        key="tlx_mental_comment",
        placeholder="e.g. 'The branching decisions were easy but the time pressure made it hard to think.'",
    )

    st.markdown("**Temporal demand — Did you have enough time?**")
    temporal = st.slider(
        "Temporal demand",
        1, 10, 5,
        help="1 = plenty of time, 10 = felt extremely rushed.",
        label_visibility="collapsed",
    )
    temporal_comment = st.text_area(
        "Anything you'd like to add about time pressure?",
        key="tlx_temporal_comment",
        placeholder="e.g. 'The 45-second limit was tight but I never felt fully overwhelmed.'",
    )

    st.markdown("**Effort — How hard did you have to work to operate the console?**")
    effort = st.slider(
        "Effort",
        1, 10, 5,
        help="1 = effortless, 10 = had to try very hard.",
        label_visibility="collapsed",
    )
    effort_comment = st.text_area(
        "Anything you'd like to add about effort?",
        key="tlx_effort_comment",
        placeholder="e.g. 'Selecting the right checklist took most of the effort; the execution was straightforward.'",
    )

    st.markdown("**Frustration — How frustrated or annoyed did you feel?**")
    frustration = st.slider(
        "Frustration",
        1, 10, 5,
        help="1 = calm and relaxed, 10 = very frustrated.",
        label_visibility="collapsed",
    )
    frustration_comment = st.text_area(
        "Anything you'd like to add about frustration?",
        key="tlx_frustration_comment",
        placeholder="e.g. 'The timer made me anxious but the interface never got in the way.'",
    )

    general_comment = st.text_area(
        "General comments — anything else worth sharing about the experience?",
        key="general_comment",
        placeholder="Open-ended feedback about the interface, checklist style, difficulty, etc.",
    )

    if st.button("Submit survey", type="primary", use_container_width=True):
        submit_session_survey({
            "nasa_tlx_mental": mental,
            "nasa_tlx_temporal": temporal,
            "nasa_tlx_effort": effort,
            "nasa_tlx_frustration": frustration,
            "tlx_mental_comment": mental_comment,
            "tlx_temporal_comment": temporal_comment,
            "tlx_effort_comment": effort_comment,
            "tlx_frustration_comment": frustration_comment,
            "general_comment": general_comment,
        })
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ----- Session summary --------------------------------------------------

def render_session_summary() -> None:
    render_rocket_celebration()
    st.markdown('<div class="hf-console-panel">', unsafe_allow_html=True)
    render_section_header("Session complete", "Summary across all trials")

    summaries: List[Dict[str, Any]] = st.session_state.all_summaries
    if not summaries:
        render_notice("No trial summaries recorded.", "warn")
    else:
        for s in summaries:
            end_label = {
                "completed": "✓ Completed",
                "timeout": "⏱ Timed out",
                "wrong_branch": "✗ Wrong branch",
                "procedure_end": "⚠ Procedure ended (mode mismatch)",
            }.get(s["end_reason"], s["end_reason"])
            st.markdown(
                f'<div class="hf-notice hf-notice-info">'
                f'<strong>Trial {s["trial_number"]} — {esc(s["scenario_title"])}</strong><br/>'
                f'{end_label} · {s["completion_time_s"]:.1f}s · '
                f'order_errors={s["order_errors"]} · wrong_mode={s["wrong_mode_actions"]} · '
                f'decision_errors={s["branch_decision_errors"]} · '
                f'pick_error={s["checklist_selection_error"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

    render_notice(
        f"Data saved to: {st.session_state.data_sink or 'local CSV'}",
        "info",
    )
    st.markdown('</div>', unsafe_allow_html=True)
