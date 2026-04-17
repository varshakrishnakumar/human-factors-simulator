import random
import time
import uuid
from typing import Any, Dict, List, Optional

import streamlit as st

from sim.config import (
    CONDITIONS,
    FAMILIARIZATION_TIME_LIMIT,
    NUM_REAL_TRIALS,
)
from sim.scenarios import (
    get_familiarization,
    get_scenarios,
    linear_candidates,
    scenario_by_id,
)
from sim.sinks import persist, record_assignment
from sim.state import reset_trial_state


# ----- Accessors ---------------------------------------------------------

def current_scenario() -> Optional[Dict[str, Any]]:
    return st.session_state.scenario


def current_time_limit() -> int:
    if st.session_state.in_familiarization:
        return FAMILIARIZATION_TIME_LIMIT
    key = st.session_state.condition_key
    if not key:
        return 60
    return CONDITIONS[key]["time_limit"]


def elapsed_time() -> float:
    if st.session_state.completion_time is not None:
        return st.session_state.completion_time
    if not st.session_state.start_time:
        return 0.0
    return time.time() - st.session_state.start_time


def remaining_time() -> float:
    return max(0.0, current_time_limit() - elapsed_time())


def checklist_type() -> str:
    key = st.session_state.condition_key
    if not key:
        return "linear"
    return CONDITIONS[key]["checklist_type"]


def current_trial_number() -> int:
    if st.session_state.in_familiarization:
        return 0
    return st.session_state.trial_index + 1


def total_trials() -> int:
    return len(st.session_state.trial_order)


def action_expected_mode(action: str) -> Optional[str]:
    scenario = st.session_state.scenario
    if not scenario:
        return None
    return scenario.get("action_expected_modes", {}).get(action)


# ----- Linear picking ----------------------------------------------------

def picked_linear_checklist() -> Optional[Dict[str, Any]]:
    sid = st.session_state.selected_checklist_id
    if sid is None:
        return None
    for c in linear_candidates():
        if c["scenario_id"] == sid:
            return c
    return None


def current_action_buttons() -> List[str]:
    scenario = st.session_state.scenario
    if not scenario:
        return []
    if st.session_state.in_familiarization:
        return list(scenario["linear_checklist"]["steps"])
    ct = checklist_type()
    if ct == "linear":
        picked = picked_linear_checklist()
        if picked is None:
            return []
        return list(picked["steps"])
    # branching: all action-type steps (skip decisions and terminal)
    bc = scenario["branching_checklist"]
    return [s["text"] for s in bc["steps"] if s.get("type") == "action"]


# ----- Session control --------------------------------------------------

def start_session() -> None:
    st.session_state.session_started = True
    st.session_state.session_id = str(uuid.uuid4())[:8]

    scenarios = get_scenarios()
    n = min(len(scenarios), NUM_REAL_TRIALS)
    st.session_state.trial_order = random.sample(scenarios, n)
    st.session_state.trial_index = 0
    st.session_state.all_summaries = []
    st.session_state.session_finished = False
    st.session_state.session_survey_submitted = False

    record_assignment({
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
        "experience": st.session_state.experience,
        "condition": st.session_state.condition_key,
        "checklist_type": CONDITIONS[st.session_state.condition_key]["checklist_type"],
        "time_limit": CONDITIONS[st.session_state.condition_key]["time_limit"],
        "assignment_mode": st.session_state.condition_assignment_mode,
        "scenario_order": ",".join(str(s["scenario_id"]) for s in st.session_state.trial_order),
        "ts": round(time.time(), 3),
    })

    _start_familiarization()


def _start_familiarization() -> None:
    reset_trial_state()
    st.session_state.scenario = get_familiarization()
    st.session_state.in_familiarization = True
    st.session_state.trial_started = True
    st.session_state.start_time = time.time()
    st.session_state.mode = st.session_state.scenario["initial_mode"]
    # For familiarization, pre-select the practice checklist so buttons appear.
    st.session_state.selected_checklist_id = 0
    _log_event("FAMILIARIZATION START")


def start_real_trial(index: int) -> None:
    reset_trial_state()
    st.session_state.trial_index = index
    st.session_state.in_familiarization = False
    st.session_state.scenario = st.session_state.trial_order[index]
    st.session_state.trial_started = True
    st.session_state.start_time = time.time()
    st.session_state.mode = st.session_state.scenario["initial_mode"]
    _log_event("TRIAL START", {"trial_number": current_trial_number()})


def advance_after_trial() -> None:
    if st.session_state.in_familiarization:
        st.session_state.did_familiarization = True
        start_real_trial(0)
        return

    next_idx = st.session_state.trial_index + 1
    if next_idx >= total_trials():
        st.session_state.session_finished = True
        return
    start_real_trial(next_idx)


# ----- Event log --------------------------------------------------------

def _log_event(action: str, extra: Optional[Dict[str, Any]] = None) -> None:
    if not st.session_state.session_id:
        return
    scenario = st.session_state.scenario or {}
    row = {
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
        "experience": st.session_state.experience,
        "condition": st.session_state.condition_key,
        "checklist_type": (
            "practice" if st.session_state.in_familiarization else checklist_type()
        ),
        "is_familiarization": int(bool(st.session_state.in_familiarization)),
        "trial_number": current_trial_number(),
        "scenario_id": scenario.get("scenario_id"),
        "timestamp_s": round(elapsed_time(), 3),
        "mode": st.session_state.mode,
        "action": action,
    }
    if extra:
        row.update(extra)
    st.session_state.trial_event_rows.append(row)


def maybe_auto_transition() -> None:
    scenario = st.session_state.scenario
    if not scenario or not st.session_state.trial_started or st.session_state.finished:
        return
    trans = scenario.get("auto_transition", {})
    t = trans.get("time")
    new_mode = trans.get("new_mode")
    if t is None or new_mode is None:
        return
    if elapsed_time() >= t and st.session_state.mode != new_mode:
        old = st.session_state.mode
        st.session_state.mode = new_mode
        _log_event("AUTO TRANSITION", {"from_mode": old, "to_mode": new_mode})


def tick_timer() -> None:
    if not st.session_state.trial_started or st.session_state.finished:
        return
    if st.session_state.in_familiarization:
        return
    if remaining_time() <= 0:
        finish_trial(end_reason="timeout")


# ----- Actions ----------------------------------------------------------

def _branching_current_step() -> Optional[Dict[str, Any]]:
    scenario = st.session_state.scenario
    if not scenario:
        return None
    bc = scenario.get("branching_checklist", {})
    step_id = st.session_state.branch_step_id
    if step_id is None:
        return None
    for s in bc.get("steps", []):
        if s["id"] == step_id:
            return s
    return None


def execute_action(action: str) -> None:
    scenario = st.session_state.scenario
    if not scenario or st.session_state.finished:
        return

    ct = checklist_type()
    prev_mode = st.session_state.mode

    expected_mode = action_expected_mode(action)
    wrong_mode = bool(expected_mode and st.session_state.mode != expected_mode)
    if wrong_mode:
        st.session_state.wrong_mode_actions += 1

    if not st.session_state.in_familiarization and ct == "linear":
        picked = picked_linear_checklist()
        if picked:
            expected_step = next(
                (s for s in picked["steps"] if s not in st.session_state.completed_actions),
                None,
            )
            if expected_step and action != expected_step:
                st.session_state.order_errors += 1
                _log_event("ORDER ERROR", {"attempted": action, "expected": expected_step})

    if not st.session_state.in_familiarization and ct == "branching":
        bs = _branching_current_step()
        if bs and bs.get("type") == "action":
            if action == bs["text"]:
                st.session_state.branch_path.append(bs["id"])
                st.session_state.branch_step_id = bs.get("next")
            else:
                st.session_state.order_errors += 1
                _log_event(
                    "ORDER ERROR",
                    {
                        "attempted": action,
                        "expected_step_id": bs["id"],
                        "expected": bs["text"],
                    },
                )

    if action not in st.session_state.completed_actions:
        st.session_state.completed_actions.append(action)

    if action == "SELECT AUTO MODE":
        st.session_state.mode = "AUTO"

    _log_event(action, {
        "wrong_mode": wrong_mode,
        "from_mode": prev_mode,
        "to_mode": st.session_state.mode,
    })

    _maybe_auto_finish()


def submit_branching_decision(option_index: int) -> None:
    bs = _branching_current_step()
    if not bs or bs.get("type") != "decision" or st.session_state.finished:
        return
    option = bs["options"][option_index]
    correct = bool(option.get("correct", False))
    if not correct:
        st.session_state.branch_decision_errors += 1
    st.session_state.branch_path.append(bs["id"])
    st.session_state.branch_step_id = option.get("next")
    _log_event("DECISION", {
        "step_id": bs["id"],
        "choice": option["label"],
        "correct": correct,
    })
    _maybe_auto_finish()


def select_linear_checklist(scenario_id: int) -> None:
    scenario = st.session_state.scenario
    if not scenario:
        return
    correct = scenario_id == scenario["scenario_id"]
    st.session_state.selected_checklist_id = scenario_id
    st.session_state.checklist_selection_error = not correct
    _log_event("CHECKLIST SELECTED", {
        "selected_id": scenario_id,
        "correct_id": scenario["scenario_id"],
        "correct": correct,
    })


def _maybe_auto_finish() -> None:
    scenario = st.session_state.scenario
    if not scenario:
        return
    ct = checklist_type()

    if st.session_state.in_familiarization:
        if "ACK PRACTICE ALERT" in st.session_state.completed_actions:
            finish_trial(end_reason="completed")
        return

    if ct == "linear":
        picked = picked_linear_checklist()
        if picked is None:
            return
        all_done = all(s in st.session_state.completed_actions for s in picked["steps"])
        end_mode_ok = st.session_state.mode == scenario["correct_mode"]
        if all_done and end_mode_ok:
            finish_trial(end_reason="completed")
        return

    if ct == "branching":
        bs = _branching_current_step()
        if st.session_state.branch_step_id is None:
            last = st.session_state.branch_path[-1] if st.session_state.branch_path else None
            if last == 99:
                finish_trial(end_reason="wrong_branch")
                return
            if st.session_state.mode == scenario["correct_mode"]:
                finish_trial(end_reason="completed")
            else:
                finish_trial(end_reason="procedure_end")
            return
        if bs and bs.get("type") == "terminal":
            finish_trial(end_reason="wrong_branch")


def finish_trial(end_reason: str = "completed") -> None:
    if st.session_state.finished:
        return
    scenario = st.session_state.scenario
    st.session_state.completion_time = elapsed_time()
    st.session_state.end_reason = end_reason
    st.session_state.finished = True

    _log_event("TRIAL FINISH", {
        "end_reason": end_reason,
        "completion_time": round(st.session_state.completion_time, 3),
    })

    if not st.session_state.in_familiarization:
        summary = {
            "session_id": st.session_state.session_id,
            "participant_id": st.session_state.participant_id,
            "experience": st.session_state.experience,
            "condition": st.session_state.condition_key,
            "checklist_type": checklist_type(),
            "time_limit": current_time_limit(),
            "trial_number": current_trial_number(),
            "scenario_id": scenario["scenario_id"],
            "scenario_title": scenario["title"],
            "fault": scenario["fault"],
            "completion_time_s": round(st.session_state.completion_time, 3),
            "end_reason": end_reason,
            "completed": end_reason == "completed",
            "timed_out": end_reason == "timeout",
            "wrong_mode_actions": st.session_state.wrong_mode_actions,
            "order_errors": st.session_state.order_errors,
            "branch_decision_errors": st.session_state.branch_decision_errors,
            "checklist_selection_error": int(st.session_state.checklist_selection_error),
            "selected_checklist_id": st.session_state.selected_checklist_id,
        }
        st.session_state.all_summaries.append(summary)

    sink = persist("events", list(st.session_state.trial_event_rows))
    st.session_state.data_sink = sink


def submit_session_survey(payload: Dict[str, Any]) -> None:
    rows = []
    for summary in st.session_state.all_summaries:
        row = dict(summary)
        row.update(payload)
        rows.append(row)
    persist("summaries", rows)
    st.session_state.session_survey_submitted = True
