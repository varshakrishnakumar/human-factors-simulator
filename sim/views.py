from typing import Any, Dict, List

import streamlit as st

from sim.components import (
    esc,
    mode_color,
    mode_glow,
    render_notice,
    render_rocket_celebration,
    render_section_header,
    render_trigger_cues,
)
from sim.domain.action_help import ACTION_HELP
from sim.domain.conditions import BACKGROUND_OPTIONS, CONDITIONS
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


# ----- Sidebar -----------------------------------------------------------

def render_sidebar_setup() -> None:
    st.sidebar.header("Setup")
    if st.session_state.session_started:
        st.sidebar.caption("Session in progress. Reload the page to start a new session.")
        st.sidebar.write(f"**Session ID:** `{st.session_state.session_id}`")
        st.sidebar.write(f"**Participant:** {st.session_state.participant_id}")
        st.sidebar.write(f"**Experience:** {st.session_state.experience}")
        st.sidebar.write(f"**Condition:** {CONDITIONS[st.session_state.condition_key].label}")
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
            f"**Assigned condition:** `{CONDITIONS[suggested].label}`"
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
            format_func=lambda k: CONDITIONS[k].label,
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
        "Welcome. Before starting, please read the full briefing below. If any part is "
        "unclear, ask the study coordinator before clicking Start session.",
        "info",
    )

    st.markdown(
        """
        <div class="hf-brief">
        <h3>What this study is about</h3>
        <p>You will operate a simplified spacecraft console and recover the spacecraft
        from three injected faults. We are comparing two checklist styles (linear and
        branching) under two levels of time pressure.</p>

        <h3>How the session is structured</h3>
        <ol>
          <li><strong>Practice trial (Trial 0).</strong> One-button warm-up. No timer, no scoring.</li>
          <li><strong>Three recovery trials.</strong> Each trial injects one fault. A
          sticky timer at the top of the page shows how long you have.
          Trials end automatically when you reach the desired end state <em>or</em> when
          the timer hits zero — you do not need to click a "finish" button.</li>
          <li><strong>Workload survey.</strong> A single NASA-TLX questionnaire about the
          whole session. Full-sentence comments are welcome.</li>
        </ol>

        <h3>How to read the screen</h3>
        <ul>
          <li>The <strong>blue-bordered Console</strong> on the left shows the fault, the
          spacecraft's current mode, the trigger cues that are currently annunciating,
          and all available action buttons.</li>
          <li>The <strong>amber-bordered Checklist</strong> on the right shows the procedure
          you should be following. In linear trials you will see three candidate checklists
          and must pick the one that matches the trigger cues on the Console. In branching
          trials you will see one checklist with decision points — read each step carefully
          and choose the right branch.</li>
          <li>Action buttons are always enabled. Clicking a button out of order, or while
          the spacecraft is in the wrong mode, is logged as an error — so think before
          you click.</li>
        </ul>

        <h3>Display and seating</h3>
        <p>This interface is designed for a desktop or laptop monitor. If any critical
        information is cut off or requires scrolling, raise it with the coordinator so we
        can note it — the timer, mode, and fault should stay pinned at the top of the
        screen at all times.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_notice(
        "When you're ready: enter a Participant ID and Experience level in the sidebar, "
        "then click Start session.",
        "success",
    )


# ----- Console -----------------------------------------------------------

def render_status_bar() -> None:
    """Sticky top strip with the timer, current mode, and fault — always visible."""
    scenario = current_scenario()
    if not scenario or not st.session_state.trial_started:
        return
    if st.session_state.in_familiarization:
        timer_html = '<div class="hf-statusbar-cell"><div class="hf-statusbar-label">PRACTICE</div>'\
                     '<div class="hf-statusbar-value" style="color:var(--hf-green);">No timer</div></div>'
    else:
        rem = int(remaining_time())
        total = max(current_time_limit(), 1)
        frac = max(0.0, min(1.0, rem / total))
        if rem <= 10:
            tcolor = "var(--hf-red)"
        elif rem <= 20:
            tcolor = "var(--hf-amber)"
        else:
            tcolor = "var(--hf-blue)"
        timer_html = (
            f'<div class="hf-statusbar-cell">'
            f'<div class="hf-statusbar-label">Time Remaining</div>'
            f'<div class="hf-statusbar-value" style="color:{tcolor};">{rem}s</div>'
            f'<div class="hf-timer-bar"><div class="hf-timer-bar-fill" style="--timer-color:{tcolor}; width:{frac*100:.1f}%;"></div></div>'
            f'</div>'
        )

    mode = st.session_state.mode or "—"
    mode_html = (
        f'<div class="hf-statusbar-cell">'
        f'<div class="hf-statusbar-label">Mode</div>'
        f'<div class="hf-statusbar-value" '
        f'style="background:{mode_color(mode)}; color:white; padding:0.25rem 0.6rem; border-radius:8px;'
        f' box-shadow:0 0 18px {mode_glow(mode)}; display:inline-block;">{esc(mode)}</div>'
        f'</div>'
    )

    fault_html = (
        f'<div class="hf-statusbar-cell hf-statusbar-fault">'
        f'<div class="hf-statusbar-label">Fault</div>'
        f'<div class="hf-statusbar-value" style="font-size:0.95rem;">{esc(scenario["fault"])}</div>'
        f'</div>'
    )

    st.markdown(
        f'<div class="hf-statusbar">{timer_html}{mode_html}{fault_html}</div>',
        unsafe_allow_html=True,
    )


def render_console() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-console-panel">', unsafe_allow_html=True)

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
                if st.button(
                    action,
                    key=f"btn_{action}",
                    use_container_width=True,
                    help=ACTION_HELP.get(action, ""),
                ):
                    execute_action(action)
                    st.rerun()

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
        "Match the console indications to one of the three checklists below.",
    )

    candidates = linear_candidates()
    for cand in candidates:
        cues_html = " · ".join(
            f'<span style="color:var(--hf-amber); font-family:SFMono-Regular,Menlo,Consolas,monospace;'
            f' font-size:0.72rem; letter-spacing:0.1em;">{esc(c["label"])}: {esc(c["value"])}</span>'
            for c in cand["trigger_cues"]
        )
        st.markdown(
            f'<div class="hf-choice-card">'
            f'<div class="hf-choice-title">Checklist {cand["scenario_id"]} — {esc(cand["title"])}</div>'
            f'<div style="margin-bottom:0.3rem;">{cues_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"See all steps for Checklist {cand['scenario_id']}"):
            steps_html = "".join(
                f'<div class="hf-choice-step">{i:02d}. {esc(s)}</div>'
                for i, s in enumerate(cand["steps"], start=1)
            )
            st.markdown(steps_html, unsafe_allow_html=True)
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


# ----- Familiarization complete -----------------------------------------

def render_familiarization_complete() -> None:
    render_notice(
        "Practice complete. The real trials each have a time limit — click Start "
        "Trial 1 when you're ready to begin.",
        "success",
    )
    if st.button("Start Trial 1", type="primary", use_container_width=True):
        advance_after_trial()
        st.rerun()


# ----- Final survey (post-session) --------------------------------------

def _tlx_slider(
    label: str,
    question: str,
    low_anchor: str,
    high_anchor: str,
    key: str,
) -> int:
    st.markdown(
        f'<div class="hf-tlx-block">'
        f'<div class="hf-tlx-label">{esc(label)}</div>'
        f'<div class="hf-tlx-question">{esc(question)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    value = st.slider(
        label,
        min_value=1,
        max_value=10,
        value=5,
        step=1,
        key=f"tlx_{key}",
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="hf-tlx-anchors">'
        f'<span><strong>1</strong> — {esc(low_anchor)}</span>'
        f'<span class="hf-tlx-current">Your rating: <strong>{value}</strong> / 10</span>'
        f'<span><strong>10</strong> — {esc(high_anchor)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    return value


def render_final_survey() -> None:
    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)
    render_section_header("Workload Survey", "One-time survey covering the whole session")

    render_notice(
        "Reflect on the whole session. The scales are from the NASA Task Load Index "
        "(NASA-TLX). Every slider runs 1 to 10 — the label under each slider tells you "
        "what each end of the scale means. Use the comment boxes to add a sentence or "
        "two of context if you'd like — full sentences are welcome.",
        "info",
    )

    mental = _tlx_slider(
        "Mental demand",
        "How mentally demanding was operating the console?",
        "Very low — easy to think through",
        "Very high — had to concentrate hard",
        "mental",
    )
    mental_comment = st.text_area(
        "Anything you'd like to add about mental demand?",
        key="tlx_mental_comment",
        placeholder="e.g. 'The branching decisions were easy but the time pressure made it hard to think.'",
    )

    temporal = _tlx_slider(
        "Temporal demand",
        "Did you have enough time to do the task well?",
        "Very low — plenty of time, never rushed",
        "Very high — felt extremely rushed",
        "temporal",
    )
    temporal_comment = st.text_area(
        "Anything you'd like to add about time pressure?",
        key="tlx_temporal_comment",
        placeholder="e.g. 'The 45-second limit was tight but I never felt fully overwhelmed.'",
    )

    effort = _tlx_slider(
        "Effort",
        "How hard did you have to work to complete the task?",
        "Very low — effortless",
        "Very high — had to try very hard",
        "effort",
    )
    effort_comment = st.text_area(
        "Anything you'd like to add about effort?",
        key="tlx_effort_comment",
        placeholder="e.g. 'Selecting the right checklist took most of the effort; the execution was straightforward.'",
    )

    frustration = _tlx_slider(
        "Frustration",
        "How frustrated or annoyed did you feel during the task?",
        "Very low — calm and relaxed",
        "Very high — very frustrated",
        "frustration",
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
