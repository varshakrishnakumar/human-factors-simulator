"""Bridges Streamlit session_state <-> TrialEngine. The engine is pure;
this file is the only place that touches st.session_state for trial flow."""
import random
import time
import uuid
from typing import Any, Dict, List, Optional

import streamlit as st

from sim.domain.conditions import CONDITIONS, FAMILIARIZATION_TIME_LIMIT, NUM_REAL_TRIALS
from sim.domain.engine import TrialEngine
from sim.domain.models import Condition, Scenario, TrialContext, TrialEvent, TrialResult
from sim.domain.scenarios.registry import get_all as _get_scenarios, get_by_id, get_familiarization
from sim.io.sinks import persist, record_assignment
from sim.state import reset_trial_state

_ENGINE_KEY = "trial_engine"


# ----- Engine load/save --------------------------------------------

def _engine() -> Optional[TrialEngine]:
    return st.session_state.get(_ENGINE_KEY)


def _set_engine(engine: Optional[TrialEngine]) -> None:
    st.session_state[_ENGINE_KEY] = engine
    _mirror_to_session_state(engine)


def _mirror_to_session_state(engine: Optional[TrialEngine]) -> None:
    """TEMPORARY compat: mirror engine state to the legacy flat session_state
    keys that sim/views.py (and the pre-Task-7 screens) still read directly.
    Removed in Task 7 when screens cut over to engine/state accessors."""
    if engine is None:
        st.session_state.trial_started = False
        st.session_state.finished = False
        st.session_state.mode = None
        st.session_state.scenario = None
        st.session_state.completed_actions = []
        st.session_state.selected_checklist_id = None
        st.session_state.checklist_selection_error = False
        st.session_state.branch_step_id = None
        st.session_state.branch_path = []
        st.session_state.wrong_mode_actions = 0
        st.session_state.order_errors = 0
        st.session_state.branch_decision_errors = 0
        st.session_state.start_time = None
        st.session_state.completion_time = None
        st.session_state.end_reason = None
        st.session_state.trial_event_rows = []
        return
    st.session_state.trial_started = True
    st.session_state.finished = engine.is_finished()
    st.session_state.mode = engine.mode
    st.session_state.scenario = _scenario_to_dict(engine.scenario)
    st.session_state.completed_actions = list(engine.completed_actions)
    st.session_state.selected_checklist_id = engine.selected_checklist_id
    st.session_state.checklist_selection_error = engine.checklist_selection_error
    st.session_state.branch_step_id = engine.branch_step_id
    st.session_state.branch_path = list(engine.branch_path)
    st.session_state.wrong_mode_actions = engine.wrong_mode_actions
    st.session_state.order_errors = engine.order_errors
    st.session_state.branch_decision_errors = engine.branch_decision_errors
    st.session_state.start_time = engine.start_time
    st.session_state.completion_time = engine.completion_time
    st.session_state.end_reason = engine.end_reason()
    # trial_event_rows left empty under refactor — views.py doesn't read them


# ----- Accessors called by UI --------------------------------------

def current_scenario() -> Optional[Dict[str, Any]]:
    e = _engine()
    return _scenario_to_dict(e.scenario) if e else None


def current_time_limit() -> int:
    e = _engine()
    if e is None:
        return 60
    if e.scenario.is_familiarization:
        return FAMILIARIZATION_TIME_LIMIT
    return e.condition.time_limit


def elapsed_time() -> float:
    e = _engine()
    return e.elapsed(time.time()) if e else 0.0


def remaining_time() -> float:
    e = _engine()
    if e is None:
        return 0.0
    if e.scenario.is_familiarization:
        return max(0.0, FAMILIARIZATION_TIME_LIMIT - e.elapsed(time.time()))
    return e.remaining(time.time())


def checklist_type() -> str:
    e = _engine()
    return e.condition.checklist_type if e else "linear"


def current_trial_number() -> int:
    e = _engine()
    if e is None:
        return 0
    return 0 if e.scenario.is_familiarization else e.context.trial_number


def total_trials() -> int:
    return len(st.session_state.get("trial_order", []))


def action_expected_mode(action: str) -> Optional[str]:
    e = _engine()
    return e.scenario.action_expected_modes.get(action) if e else None


def picked_linear_checklist() -> Optional[Dict[str, Any]]:
    e = _engine()
    if e is None:
        return None
    picked = e.picked_linear_checklist()
    if picked is None:
        return None
    return {"scenario_id": e.selected_checklist_id, "title": picked.title, "steps": list(picked.steps)}


def current_action_buttons() -> List[str]:
    e = _engine()
    return list(e.current_action_buttons()) if e else []


# ----- Flags ------------------------------------------------------

def trial_started() -> bool:
    return _engine() is not None


def finished() -> bool:
    e = _engine()
    return bool(e and e.is_finished())


# ----- Session control --------------------------------------------

def start_session() -> None:
    st.session_state.session_started = True
    st.session_state.session_id = str(uuid.uuid4())[:8]
    scenarios = list(_get_scenarios())
    n = min(len(scenarios), NUM_REAL_TRIALS)
    st.session_state.trial_order = random.sample([s.id for s in scenarios], n)
    st.session_state.trial_index = 0
    st.session_state.all_summaries = []
    st.session_state.session_finished = False
    st.session_state.session_survey_submitted = False

    cond = CONDITIONS[st.session_state.condition_key]
    record_assignment({
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
        "experience": st.session_state.experience,
        "condition": cond.key,
        "checklist_type": cond.checklist_type,
        "time_limit": cond.time_limit,
        "assignment_mode": st.session_state.condition_assignment_mode,
        "scenario_order": ",".join(str(sid) for sid in st.session_state.trial_order),
        "ts": round(time.time(), 3),
    })
    _start_familiarization()


def _start_familiarization() -> None:
    reset_trial_state()
    st.session_state.in_familiarization = True
    fam = get_familiarization()
    ctx = TrialContext(
        session_id=st.session_state.session_id,
        participant_id=st.session_state.participant_id,
        experience=st.session_state.experience,
        trial_number=0,
    )
    cond = CONDITIONS[st.session_state.condition_key]
    _set_engine(TrialEngine(fam, cond, ctx, start_time=time.time()))


def start_real_trial(index: int) -> None:
    reset_trial_state()
    st.session_state.trial_index = index
    st.session_state.in_familiarization = False
    scenario_id = st.session_state.trial_order[index]
    scenario = get_by_id(scenario_id)
    ctx = TrialContext(
        session_id=st.session_state.session_id,
        participant_id=st.session_state.participant_id,
        experience=st.session_state.experience,
        trial_number=index + 1,
    )
    cond = CONDITIONS[st.session_state.condition_key]
    _set_engine(TrialEngine(scenario, cond, ctx, start_time=time.time()))


def advance_after_trial() -> None:
    e = _engine()
    if e and e.scenario.is_familiarization:
        st.session_state.did_familiarization = True
        start_real_trial(0)
        return
    next_idx = st.session_state.trial_index + 1
    if next_idx >= total_trials():
        st.session_state.session_finished = True
        return
    start_real_trial(next_idx)


# ----- Delegated mutations ----------------------------------------

def execute_action(action: str) -> None:
    e = _engine()
    if not e:
        return
    e.execute_action(action, now=time.time())
    _mirror_to_session_state(e)
    if e.is_finished():
        _finalize_trial(e)


def submit_branching_decision(option_index: int) -> None:
    e = _engine()
    if not e:
        return
    e.submit_decision(option_index, now=time.time())
    _mirror_to_session_state(e)
    if e.is_finished():
        _finalize_trial(e)


def select_linear_checklist(scenario_id: int) -> None:
    e = _engine()
    if not e:
        return
    e.select_linear_checklist(scenario_id, now=time.time())
    _mirror_to_session_state(e)


def maybe_auto_transition() -> None:
    e = _engine()
    if e:
        e.tick(time.time())
        _mirror_to_session_state(e)
        if e.is_finished():
            _finalize_trial(e)


def tick_timer() -> None:
    # tick() already handles timeout
    maybe_auto_transition()


# ----- Persistence -----------------------------------------------

def _finalize_trial(engine: TrialEngine) -> None:
    """Persist events + summary once per finished engine. Idempotent:
    guarded by `engine._finalized` so repeat calls (from maybe_auto_transition
    on subsequent reruns while the engine is still the current one) are no-ops."""
    if getattr(engine, "_finalized", False):
        return
    engine._finalized = True  # set BEFORE persist so a crash-and-retry doesn't double-write
    rows = [_serialize_event(ev, engine) for ev in engine.event_log()]
    sink = persist("events", rows)
    st.session_state.data_sink = sink
    if not engine.scenario.is_familiarization:
        import dataclasses
        st.session_state.all_summaries.append(dataclasses.asdict(engine.result()))


def _serialize_event(ev: TrialEvent, engine: TrialEngine) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "session_id": engine.context.session_id,
        "participant_id": engine.context.participant_id,
        "experience": engine.context.experience,
        "condition": engine.condition.key,
        "checklist_type": "practice" if engine.scenario.is_familiarization else engine.condition.checklist_type,
        "is_familiarization": int(bool(engine.scenario.is_familiarization)),
        "trial_number": 0 if engine.scenario.is_familiarization else engine.context.trial_number,
        "scenario_id": engine.scenario.id,
        "timestamp_s": ev.timestamp_s,
        "mode": ev.mode,
        "action": ev.action,
    }
    row.update(ev.extra)
    return row


def submit_session_survey(payload: Dict[str, Any]) -> None:
    rows = []
    for summary in st.session_state.all_summaries:
        row = dict(summary)
        row.update(payload)
        rows.append(row)
    persist("summaries", rows)
    st.session_state.session_survey_submitted = True


# ----- Compat shim: dict view of scenario for existing views.py ---

def _scenario_to_dict(s: Scenario) -> Dict[str, Any]:
    from sim.scenarios import _scenario_to_dict as _to_dict  # reuse shim
    return _to_dict(s)
