"""Decides whether a trial has ended and what the end reason is. I kept this
separate from engine.py so data-team changes to "what counts as completed" live
in exactly one file. For example, if we later add a partial-completion rule or
change the wrong_branch condition, neither engine.py nor trial.py need editing.

All functions here are pure: same inputs always give same output, no I/O, no
clock reads. The engine calls classify_end() after every mutation to check
whether to call _finish(). aggregate_errors() is a convenience used by the
summary screen and tests to total all error types."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sim.domain.models import EndReason, TerminalStep, TrialResult

if TYPE_CHECKING:
    from sim.domain.engine import TrialEngine


def classify_end(engine: "TrialEngine", now: float) -> Optional[EndReason]:
    """Check engine state and return an EndReason if the trial should end now,
    or None to keep going. Timeout is checked first (highest priority), then
    familiarization completion, then condition-specific rules."""
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
        if engine.mode == scenario.correct_mode:
            return "completed"
        return "procedure_end"
    return None


def aggregate_errors(result: TrialResult) -> int:
    """Sum of all error types for a finished trial. Used by summary.py for the
    on-screen recap and available to analysis scripts that want a single error
    count without reimplementing the addition."""
    return (
        result.order_errors
        + result.wrong_mode_actions
        + result.branch_decision_errors
        + result.checklist_selection_error
    )
