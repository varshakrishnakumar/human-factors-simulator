"""Pure TrialEngine. No streamlit. No time.time(). Caller passes `now` for all
time-dependent operations so tests can drive the clock."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sim.domain.models import (
    ActionStep, BranchingStep, Condition, DecisionStep, EndReason,
    LinearCandidate, LinearChecklist, Scenario, TerminalStep, TrialContext,
    TrialEvent, TrialResult,
)
from sim.domain.scenarios.registry import linear_candidates
from sim.domain import scoring


class TrialEngine:
    def __init__(
        self,
        scenario: Scenario,
        condition: Condition,
        context: TrialContext,
        start_time: float,
    ) -> None:
        self.scenario = scenario
        self.condition = condition
        self.context = context
        self.start_time = start_time

        self.mode: Optional[str] = scenario.initial_mode
        self.completed_actions: List[str] = []
        self.wrong_mode_actions = 0
        self.order_errors = 0
        self.selected_checklist_id: Optional[int] = (
            scenario.id if scenario.is_familiarization else None
        )
        self.checklist_selection_error = False
        self.branch_step_id: Optional[int] = (
            1 if not scenario.is_familiarization else None
        )
        self.branch_path: List[int] = []
        self.branch_decision_errors = 0
        self.completion_time: Optional[float] = None
        self._end_reason: Optional[EndReason] = None
        self._finished = False
        self._events: List[TrialEvent] = []

        self._log("FAMILIARIZATION START" if scenario.is_familiarization else "TRIAL START",
                  {"trial_number": context.trial_number} if not scenario.is_familiarization else None)

    # ----- Time ---------------------------------------------------------
    def elapsed(self, now: float) -> float:
        if self.completion_time is not None:
            return self.completion_time
        return max(0.0, now - self.start_time)

    def remaining(self, now: float) -> float:
        return max(0.0, self.condition.time_limit - self.elapsed(now))

    # ----- State accessors ---------------------------------------------
    def is_finished(self) -> bool:
        return self._finished

    def end_reason(self) -> Optional[EndReason]:
        return self._end_reason

    def picked_linear_checklist(self) -> Optional[LinearChecklist]:
        if self.selected_checklist_id is None:
            return None
        # If the user picked THIS scenario's checklist, always use self.scenario's
        # linear_checklist — avoids relying on the global registry in unit tests
        # where the fabricated scenario may share an id with a real one.
        if self.selected_checklist_id == self.scenario.id:
            return self.scenario.linear_checklist
        # Otherwise the user picked a different scenario's checklist; look it up
        # in the registry. (Real runtime: scenario=NAV, user picks THERMAL, etc.)
        for cand in linear_candidates():
            if cand.scenario_id == self.selected_checklist_id:
                return LinearChecklist(title=cand.title, steps=cand.steps)
        return None

    def current_branching_step(self) -> Optional[BranchingStep]:
        if self.branch_step_id is None:
            return None
        for s in self.scenario.branching_checklist.steps:
            if s.id == self.branch_step_id:
                return s
        return None

    def current_action_buttons(self) -> Tuple[str, ...]:
        if self.scenario.is_familiarization:
            return self.scenario.linear_checklist.steps
        if self.condition.checklist_type == "linear":
            picked = self.picked_linear_checklist()
            if picked is None:
                return ()
            return picked.steps
        # branching — every action-type step across the scenario's branching flow
        return tuple(
            s.text for s in self.scenario.branching_checklist.steps
            if isinstance(s, ActionStep)
        )

    def event_log(self) -> Tuple[TrialEvent, ...]:
        return tuple(self._events)

    # ----- Mutations ---------------------------------------------------
    def _log(self, action: str, extra: Optional[Dict[str, Any]] = None, now: Optional[float] = None) -> None:
        ts = self.elapsed(now if now is not None else self.start_time)
        self._events.append(TrialEvent(
            timestamp_s=round(ts, 3),
            mode=self.mode,
            action=action,
            extra=dict(extra) if extra else {},
        ))

    def _action_expected_mode(self, action: str) -> Optional[str]:
        return self.scenario.action_expected_modes.get(action)

    def tick(self, now: float) -> None:
        if self._finished:
            return
        # Auto-transition
        at = self.scenario.auto_transition
        if self.elapsed(now) >= at.time and self.mode != at.new_mode:
            old = self.mode
            self.mode = at.new_mode
            self._log("AUTO TRANSITION", {"from_mode": old, "to_mode": at.new_mode}, now=now)
        # Finish?
        reason = scoring.classify_end(self, now)
        if reason is not None:
            self._finish(reason, now)

    def execute_action(self, action: str, now: float) -> None:
        if self._finished or self.scenario is None:
            return
        prev_mode = self.mode

        expected_mode = self._action_expected_mode(action)
        wrong_mode = bool(expected_mode and self.mode != expected_mode)
        if wrong_mode:
            self.wrong_mode_actions += 1

        if not self.scenario.is_familiarization and self.condition.checklist_type == "linear":
            picked = self.picked_linear_checklist()
            if picked is not None:
                expected_step = next(
                    (s for s in picked.steps if s not in self.completed_actions),
                    None,
                )
                if expected_step is not None and action != expected_step:
                    self.order_errors += 1
                    self._log("ORDER ERROR", {"attempted": action, "expected": expected_step}, now=now)

        if not self.scenario.is_familiarization and self.condition.checklist_type == "branching":
            bs = self.current_branching_step()
            if isinstance(bs, ActionStep):
                if action == bs.text:
                    self.branch_path.append(bs.id)
                    self.branch_step_id = bs.next
                else:
                    self.order_errors += 1
                    self._log(
                        "ORDER ERROR",
                        {"attempted": action, "expected_step_id": bs.id, "expected": bs.text},
                        now=now,
                    )

        if action not in self.completed_actions:
            self.completed_actions.append(action)

        if action == "SELECT AUTO MODE":
            self.mode = "AUTO"

        self._log(action, {
            "wrong_mode": wrong_mode,
            "from_mode": prev_mode,
            "to_mode": self.mode,
        }, now=now)

        reason = scoring.classify_end(self, now)
        if reason is not None:
            self._finish(reason, now)

    def submit_decision(self, option_index: int, now: float) -> None:
        if self._finished:
            return
        bs = self.current_branching_step()
        if not isinstance(bs, DecisionStep):
            return
        option = bs.options[option_index]
        correct = bool(option.correct)
        if not correct:
            self.branch_decision_errors += 1
        self.branch_path.append(bs.id)
        self.branch_step_id = option.next
        self._log("DECISION", {"step_id": bs.id, "choice": option.label, "correct": correct}, now=now)
        reason = scoring.classify_end(self, now)
        if reason is not None:
            self._finish(reason, now)

    def select_linear_checklist(self, scenario_id: int, now: float) -> None:
        if self._finished or self.scenario.is_familiarization:
            return
        correct = scenario_id == self.scenario.id
        self.selected_checklist_id = scenario_id
        self.checklist_selection_error = not correct
        self._log(
            "CHECKLIST SELECTED",
            {"selected_id": scenario_id, "correct_id": self.scenario.id, "correct": correct},
            now=now,
        )

    def _finish(self, reason: EndReason, now: float) -> None:
        self.completion_time = self.elapsed(now)
        self._end_reason = reason
        self._finished = True
        self._log("TRIAL FINISH", {
            "end_reason": reason,
            "completion_time": round(self.completion_time, 3),
        }, now=now)

    # ----- Result -----------------------------------------------------
    def result(self) -> TrialResult:
        if not self._finished:
            raise RuntimeError("result() called before engine finished")
        return TrialResult(
            session_id=self.context.session_id,
            participant_id=self.context.participant_id,
            experience=self.context.experience,
            condition=self.condition.key,
            checklist_type=self.condition.checklist_type,
            time_limit=self.condition.time_limit,
            trial_number=self.context.trial_number,
            scenario_id=self.scenario.id,
            scenario_title=self.scenario.title,
            fault=self.scenario.fault,
            completion_time_s=round(self.completion_time or 0.0, 3),
            end_reason=self._end_reason or "completed",
            completed=self._end_reason == "completed",
            timed_out=self._end_reason == "timeout",
            wrong_mode_actions=self.wrong_mode_actions,
            order_errors=self.order_errors,
            branch_decision_errors=self.branch_decision_errors,
            checklist_selection_error=int(self.checklist_selection_error),
            selected_checklist_id=self.selected_checklist_id,
        )
