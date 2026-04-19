"""Compatibility shim. Bridges old dict-based callers to the new domain
registry while the refactor is in progress. Deleted at the end of step 7."""
from typing import Any, Dict, List

from sim.domain.models import (
    ActionStep, DecisionStep, LinearCandidate, Scenario, TerminalStep,
)
from sim.domain.scenarios import registry as _registry


def _step_to_dict(step) -> Dict[str, Any]:
    if isinstance(step, ActionStep):
        out: Dict[str, Any] = {"id": step.id, "type": "action", "text": step.text, "next": step.next}
        if step.note:
            out["note"] = step.note
        return out
    if isinstance(step, DecisionStep):
        return {
            "id": step.id,
            "type": "decision",
            "prompt": step.prompt,
            "options": [
                {"label": o.label, "next": o.next, "correct": o.correct,
                 **({"note": o.note} if o.note else {})}
                for o in step.options
            ],
        }
    if isinstance(step, TerminalStep):
        out = {"id": step.id, "type": "terminal", "text": step.text, "next": None}
        if step.note:
            out["note"] = step.note
        return out
    raise TypeError(f"Unknown branching step: {type(step).__name__}")


def _scenario_to_dict(s: Scenario) -> Dict[str, Any]:
    return {
        "scenario_id": s.id,
        "title": s.title,
        "fault": s.fault,
        "initial_mode": s.initial_mode,
        "auto_transition": {"time": s.auto_transition.time, "new_mode": s.auto_transition.new_mode},
        "correct_mode": s.correct_mode,
        "trigger_cues": [{"label": c.label, "value": c.value} for c in s.trigger_cues],
        "linear_checklist": {
            "title": s.linear_checklist.title,
            "steps": list(s.linear_checklist.steps),
        },
        "branching_checklist": {
            "title": s.branching_checklist.title,
            "steps": [_step_to_dict(st) for st in s.branching_checklist.steps],
        },
        "action_expected_modes": dict(s.action_expected_modes),
        "is_familiarization": s.is_familiarization,
    }


def get_scenarios() -> List[Dict[str, Any]]:
    return [_scenario_to_dict(s) for s in _registry.get_all()]


def get_familiarization() -> Dict[str, Any]:
    return _scenario_to_dict(_registry.get_familiarization())


def scenario_by_id(scenario_id: int) -> Dict[str, Any]:
    return _scenario_to_dict(_registry.get_by_id(scenario_id))


def linear_candidates() -> List[Dict[str, Any]]:
    return [
        {
            "scenario_id": c.scenario_id,
            "title": c.title,
            "steps": list(c.steps),
            "trigger_cues": [{"label": t.label, "value": t.value} for t in c.trigger_cues],
        }
        for c in _registry.linear_candidates()
    ]
