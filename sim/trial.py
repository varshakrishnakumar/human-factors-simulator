"""Public API the UI calls for everything trial-related. I kept the function
names the same as before the refactor so none of the screen files needed
touching when I split views.py. Under the hood each function grabs the
TrialEngine from session_state (key `trial_engine`), delegates to it, and
writes any results back. The engine itself lives in domain/engine.py and knows
nothing about Streamlit — this file is the seam between them."""
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    import streamlit as st
except Exception:
    class _MissingStreamlit:
        """Fallback so pure bridge tests can import this module without Streamlit."""
        session_state: Dict[str, Any] = {}

        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("Streamlit is required to run the simulator UI")

    st = _MissingStreamlit()

from sim.domain.conditions import CONDITIONS, FAMILIARIZATION_TIME_LIMIT, NUM_REAL_TRIALS
from sim.domain.engine import TrialEngine
from sim.domain.models import Condition, LinearChecklist, Scenario, TriggerCue, TrialContext, TrialEvent, TrialResult
from sim.domain.scenarios.registry import get_all as _get_scenarios, get_by_id, get_familiarization
from sim.io.sinks import persist, record_assignment
try:
    from sim.state import reset_trial_state
except ModuleNotFoundError as exc:
    if exc.name != "streamlit":
        raise

    def reset_trial_state() -> None:
        st.session_state["trial_engine"] = None

_ENGINE_KEY = "trial_engine"


# ----- Engine load/save --------------------------------------------

def _engine() -> Optional[TrialEngine]:
    return st.session_state.get(_ENGINE_KEY)


def _set_engine(engine: Optional[TrialEngine]) -> None:
    st.session_state[_ENGINE_KEY] = engine


# ----- Accessors called by UI --------------------------------------

def current_scenario() -> Optional[Scenario]:
    """The active Scenario dataclass, or None if no engine is running yet."""
    e = _engine()
    return e.scenario if e else None


def current_time_limit() -> int:
    """The time limit (seconds) for the current trial. Familiarization uses a
    generous fixed limit defined in conditions.py rather than the condition's
    limit, since practice is unscored."""
    e = _engine()
    if e is None:
        return 60
    if e.scenario.is_familiarization:
        return FAMILIARIZATION_TIME_LIMIT
    return e.condition.time_limit


def elapsed_time() -> float:
    """Seconds elapsed since the current trial started, frozen at completion
    time once the engine finishes."""
    e = _engine()
    return e.elapsed(time.time()) if e else 0.0


def remaining_time() -> float:
    """Seconds left on the countdown. Familiarization computes remaining time
    from the fixed FAMILIARIZATION_TIME_LIMIT; real trials use the engine's own
    remaining() which references the condition's time_limit."""
    e = _engine()
    if e is None:
        return 0.0
    if e.scenario.is_familiarization:
        return max(0.0, FAMILIARIZATION_TIME_LIMIT - e.elapsed(time.time()))
    return e.remaining(time.time())


def checklist_type() -> str:
    """'linear' or 'branching' — pulled from the current condition. Defaults to
    'linear' when no engine is loaded so the routing in simulator.py stays safe
    before a session starts."""
    e = _engine()
    return e.condition.checklist_type if e else "linear"


def current_trial_number() -> int:
    """1-based trial number for display in the masthead. Returns 0 during
    familiarization since the practice run is Trial 0 by convention."""
    e = _engine()
    if e is None:
        return 0
    return 0 if e.scenario.is_familiarization else e.context.trial_number


def total_trials() -> int:
    """Total number of real trials in this session (the length of the randomised
    trial_order list). The masthead shows `current / total`."""
    return len(st.session_state.get("trial_order", []))


def action_expected_mode(action: str) -> Optional[str]:
    """Which spacecraft mode the scenario expects before this action is
    executed. Used by console.py to show a mode hint; the engine records a
    wrong_mode_action when the mode doesn't match at execution time."""
    e = _engine()
    return e.scenario.action_expected_modes.get(action) if e else None


def picked_linear_checklist() -> Optional[LinearChecklist]:
    """Which linear checklist the subject picked for this trial. Delegates to
    the engine's own picked_linear_checklist() — see domain/engine.py for the
    short-circuit that avoids a registry lookup when the subject picked
    correctly."""
    e = _engine()
    return e.picked_linear_checklist() if e else None


def current_action_buttons() -> List[str]:
    """The ordered list of action button labels to display on the console.
    Changes based on condition type: for linear it's the picked checklist's
    steps; for branching it's every action-type step across the procedure."""
    e = _engine()
    return list(e.current_action_buttons()) if e else []


# ----- New engine accessor functions for UI screens ---------------

def current_mode() -> Optional[str]:
    e = _engine()
    return e.mode if e else None


def selected_checklist_id() -> Optional[int]:
    e = _engine()
    return e.selected_checklist_id if e else None


def completed_actions() -> List[str]:
    e = _engine()
    return list(e.completed_actions) if e else []


def branch_step_id() -> Optional[int]:
    e = _engine()
    return e.branch_step_id if e else None


def branch_path() -> List[int]:
    e = _engine()
    return list(e.branch_path) if e else []


def at_decision_step() -> bool:
    """True iff the branching engine is sitting on a DecisionStep waiting for
    the subject to choose. Used by console.py to disable action buttons while
    a decision is pending — pressing them at that point is a procedural error,
    and disabling makes that obvious instead of silently logging it."""
    e = _engine()
    if not e:
        return False
    from sim.domain.models import DecisionStep
    return isinstance(e.current_branching_step(), DecisionStep)


def current_trigger_cues() -> Tuple[TriggerCue, ...]:
    """The live cue panel for the current trial. During a running trial this
    reflects the engine's mutated cue state (recovery actions update individual
    cues per scenario.action_cue_effects). Outside of a running trial we fall
    back to the scenario's static initial cues so screens that render this
    before/after a trial don't break."""
    e = _engine()
    if e is not None:
        return e.current_cues()
    scenario = current_scenario()
    return scenario.trigger_cues if scenario else ()


def in_familiarization() -> bool:
    return bool(st.session_state.get("in_familiarization", False))


# ----- Flags ------------------------------------------------------

def trial_started() -> bool:
    return _engine() is not None


def finished() -> bool:
    e = _engine()
    return bool(e and e.is_finished())


# ----- Session control --------------------------------------------

def start_session() -> None:
    """Kick off a new session: generate a session_id, randomise the trial
    order, record the assignment to Sheets/CSV, then immediately start
    familiarization. Everything downstream — trial indexing, summary
    collection — assumes this has been called exactly once per page load."""
    st.session_state.session_started = True
    st.session_state.session_id = str(uuid.uuid4())[:8]
    scenarios = list(_get_scenarios())
    n = min(len(scenarios), NUM_REAL_TRIALS)
    st.session_state.trial_order = random.sample([s.id for s in scenarios], n)
    st.session_state.trial_index = 0
    st.session_state.all_summaries = []
    # Drop per-trial scalar fallbacks from any previous session so the summary
    # screen doesn't pick them up after a fresh start_session.
    for key in [k for k in st.session_state.keys()
                if isinstance(k, str) and k.startswith("summary_trial_")]:
        del st.session_state[key]
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
    """Create a fresh TrialEngine for real trial at `index` in the session's
    trial_order list and install it into session_state. Clears the previous
    engine and any leftover widget keys first so there's no state bleed between
    trials."""
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
    """Move to the next phase after the current engine finishes. After
    familiarization this immediately starts real Trial 1; after real trials it
    either starts the next trial or marks the session finished so simulator.py
    routes to the survey screen."""
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
    """Forward an action button click to the engine, then persist if the
    engine just finished. Called by console.py on every button press."""
    e = _engine()
    if not e:
        return
    e.execute_action(action, now=time.time())
    if e.is_finished():
        _finalize_trial(e)


def submit_branching_decision(option_index: int) -> None:
    """Forward a branching decision submission to the engine, then persist if
    the engine finished. Called by branching.py when the subject clicks
    'Submit decision'."""
    e = _engine()
    if not e:
        return
    e.submit_decision(option_index, now=time.time())
    if e.is_finished():
        _finalize_trial(e)


def select_linear_checklist(scenario_id: int) -> None:
    """Record the subject's checklist selection in the engine (no auto-finish
    here — the trial finishes only when all steps are done). Called by
    linear.py when the subject clicks 'Use Checklist N'."""
    e = _engine()
    if not e:
        return
    e.select_linear_checklist(scenario_id, now=time.time())


def end_trial_now() -> None:
    """Subject-initiated trial end ('I'm done' button). Records end_reason
    'self_terminated' and triggers persistence. Distinct from natural
    'completed' so the analyst can tell who self-declared vs. who actually
    satisfied the completion rules."""
    e = _engine()
    if not e:
        return
    e.end_trial(now=time.time())
    if e.is_finished():
        _finalize_trial(e)


def reset_linear_checklist() -> None:
    """Abandon the current linear-checklist pick so the picker reappears.
    Called by linear.py when a subject on a wrong-pick clicks 'Reselect
    checklist'. The original wrong pick stays recorded as an error in the
    summary — see engine.reset_checklist_selection for the rationale."""
    e = _engine()
    if not e:
        return
    e.reset_checklist_selection(now=time.time())


def maybe_auto_transition() -> None:
    """Tick the engine's clock on every rerun so auto-transitions and timeouts
    are caught even when the subject isn't clicking buttons. Called at the top
    of simulator.py's main() on every rerun."""
    e = _engine()
    if e:
        e.tick(time.time())
        if e.is_finished():
            _finalize_trial(e)


# ----- Persistence -----------------------------------------------

def _finalize_trial(engine: TrialEngine) -> None:
    """Persist events + summary once per finished engine. Idempotent:
    guarded by per-table flags so repeat calls (from maybe_auto_transition on
    subsequent reruns while the engine is still the current one) are no-ops
    after each table has been written.

    Each real trial's summary is written DIRECTLY to the 'summaries' sheet on
    finish — no in-memory buffering until the survey submits. The previous
    design buffered every trial in `st.session_state.all_summaries` and only
    flushed at survey-submit time, which lost data whenever Streamlit Cloud
    reset the list-valued session_state field between trials (a fragility we
    actually observed in the field — only the final trial survived).

    NASA-TLX workload ratings now live in their own session-level
    'session_workload' sheet, keyed by session_id. Analysts JOIN summaries to
    workload on session_id to get a (trial × workload) view. This is cleaner
    than the old TLX-merge: it gives one row per trial regardless of whether
    the subject ever opens the survey, and one row per session for workload."""
    if getattr(engine, "_finalized", False):
        return
    # Latch before any network I/O. Streamlit can overlap reruns during a slow
    # Sheets append; setting this after persist() leaves a window where the same
    # finished engine can append the same summary twice.
    engine._finalized = True

    if not getattr(engine, "_events_finalized", False):
        engine._events_finalized = True
        rows = [_serialize_event(ev, engine) for ev in engine.event_log()]
        sink = persist("events", rows)
        st.session_state.data_sink = sink

    if engine.scenario.is_familiarization:
        return

    if not getattr(engine, "_summary_finalized", False):
        engine._summary_finalized = True
        import dataclasses
        summary = dataclasses.asdict(engine.result())
        # Surface the exact actions that triggered wrong-mode counts so the
        # summary screen can explain to the subject WHICH presses were flagged.
        # Without this they see a number with no narrative.
        summary["wrong_mode_action_names"] = [
            ev.action for ev in engine.event_log()
            if ev.extra.get("wrong_mode")
        ]
        summary["order_error_attempts"] = [
            ev.extra.get("attempted") for ev in engine.event_log()
            if ev.action == "ORDER ERROR" and ev.extra.get("attempted")
        ]
        _remember_summary(summary)
        # Persist the row to the canonical 'summaries' sheet immediately —
        # this is the durable record, independent of session_state survival.
        st.session_state.summary_sink = persist("summaries", [_summary_for_sheet(summary)])


def _remember_summary(summary: Dict[str, Any]) -> None:
    """Keep an in-session copy for the final summary screen.

    Streamlit has occasionally reset list-typed session_state fields between
    trials, so each trial also gets its own scalar key. The list is rebuilt or
    repaired opportunistically here instead of assuming it is always present.
    """
    trial_number = summary.get("trial_number")
    if trial_number is not None:
        st.session_state[f"summary_trial_{trial_number}"] = summary

    summaries = st.session_state.get("all_summaries")
    if not isinstance(summaries, list):
        summaries = []
        st.session_state["all_summaries"] = summaries

    for i, existing in enumerate(summaries):
        if isinstance(existing, dict) and existing.get("trial_number") == trial_number:
            summaries[i] = summary
            break
    else:
        summaries.append(summary)


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


def _summary_for_sheet(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten any list-valued fields in a summary dict into '; '-separated
    strings so the row reads cleanly in Google Sheets / CSV. The in-memory
    summary keeps the lists; only the persisted view is flattened."""
    out: Dict[str, Any] = {}
    for k, v in summary.items():
        if isinstance(v, list):
            out[k] = "; ".join(str(x) for x in v if x is not None)
        else:
            out[k] = v
    return out


def submit_session_survey(payload: Dict[str, Any]) -> None:
    """Persist the NASA-TLX workload ratings + open-text comments as one
    session-level row to the 'session_workload' sheet, keyed by session_id and
    participant_id. Analysts JOIN with the 'summaries' sheet on session_id to
    get a per-trial view enriched with workload ratings.

    Per-trial summaries themselves are persisted immediately on trial finish
    by `_finalize_trial`, so this function no longer needs to flush a batch of
    trial rows — that was the source of the 'only the last trial saved'
    failure mode."""
    session_id = st.session_state.get("session_id", "") or ""
    participant_id = st.session_state.get("participant_id", "") or ""
    experience = st.session_state.get("experience", "") or ""
    condition_key = st.session_state.get("condition_key", "") or ""
    workload_row: Dict[str, Any] = {
        "session_id": session_id,
        "participant_id": participant_id,
        "experience": experience,
        "condition": condition_key,
    }
    workload_row.update(payload)
    persist("session_workload", [workload_row])
    st.session_state.session_survey_submitted = True
