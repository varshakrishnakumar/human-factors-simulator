"""Scenario registry. Adding a new scenario: import its SCENARIO module-level
constant and add it to _REAL below."""
from typing import Tuple

from sim.domain.models import LinearCandidate, Scenario

from sim.domain.scenarios.comm import SCENARIO as COMM
from sim.domain.scenarios.familiarization import SCENARIO as FAMILIARIZATION
from sim.domain.scenarios.nav import SCENARIO as NAV
from sim.domain.scenarios.thermal import SCENARIO as THERMAL

_REAL: Tuple[Scenario, ...] = (NAV, THERMAL, COMM)


def get_all() -> Tuple[Scenario, ...]:
    return _REAL


def get_familiarization() -> Scenario:
    return FAMILIARIZATION


def get_by_id(scenario_id: int) -> Scenario:
    if scenario_id == FAMILIARIZATION.id:
        return FAMILIARIZATION
    for s in _REAL:
        if s.id == scenario_id:
            return s
    raise KeyError(f"No scenario with id {scenario_id}")


def linear_candidates() -> Tuple[LinearCandidate, ...]:
    """The three linear checklists offered to the subject in linear conditions."""
    return tuple(
        LinearCandidate(
            scenario_id=s.id,
            title=s.linear_checklist.title,
            steps=s.linear_checklist.steps,
            trigger_cues=s.trigger_cues,
        )
        for s in _REAL
    )
