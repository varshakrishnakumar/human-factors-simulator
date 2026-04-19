"""Pure classification: is this trial over, and why?
No Streamlit. No time.time(). Deterministic given engine state."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sim.domain.models import EndReason, TerminalStep, TrialResult

if TYPE_CHECKING:
    from sim.domain.engine import TrialEngine


def classify_end(engine: "TrialEngine", now: float) -> Optional[EndReason]:
    scenario = engine.scenario
    condition = engine.condition

    if not scenario.is_familiarization and engine.elapsed(now) >= condition.time_limit:
        return "timeout"

    if scenario.is_familiarization:
        if "ACK PRACTICE ALERT" in engine.completed_actions:
            return "completed"
        return None

    if condition.checklist_type == "linear":
        picked = engine.picked_linear_checklist()
        if picked is None:
            return None
        all_done = all(s in engine.completed_actions for s in picked.steps)
        end_mode_ok = engine.mode == scenario.correct_mode
        if all_done and end_mode_ok:
            return "completed"
        return None

    # branching
    current = engine.current_branching_step()
    if isinstance(current, TerminalStep):
        return "wrong_branch"
    if engine.branch_step_id is None:
        last = engine.branch_path[-1] if engine.branch_path else None
        if last == 99:
            return "wrong_branch"
        if engine.mode == scenario.correct_mode:
            return "completed"
        return "procedure_end"
    return None


def aggregate_errors(result: TrialResult) -> int:
    return (
        result.order_errors
        + result.wrong_mode_actions
        + result.branch_decision_errors
        + result.checklist_selection_error
    )
