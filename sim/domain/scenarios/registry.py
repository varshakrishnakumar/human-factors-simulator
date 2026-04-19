"""The scenario registry — the only place that knows which scenarios exist.
To add a new scenario: create a file in this folder that defines a
`SCENARIO = Scenario(...)` module-level constant, import it here, and append
it to `_REAL`. That's it — the trial ordering, linear checklist picker, and
branching flow will all pick it up automatically."""
from typing import Tuple

from sim.domain.models import LinearCandidate, Scenario

from sim.domain.scenarios.comm import SCENARIO as COMM
from sim.domain.scenarios.familiarization import SCENARIO as FAMILIARIZATION
from sim.domain.scenarios.nav import SCENARIO as NAV
from sim.domain.scenarios.thermal import SCENARIO as THERMAL

_REAL: Tuple[Scenario, ...] = (NAV, THERMAL, COMM)


def get_all() -> Tuple[Scenario, ...]:
    """All real (non-familiarization) scenarios. trial.py uses this to build
    the randomised trial_order at session start."""
    return _REAL


def get_familiarization() -> Scenario:
    """The practice scenario used for Trial 0. Always the same one regardless
    of condition."""
    return FAMILIARIZATION


def get_by_id(scenario_id: int) -> Scenario:
    """Look up a scenario by integer id. Checks familiarization first so the
    engine can retrieve practice scenarios by id too. Raises KeyError for
    unknown ids — callers should never see this in production since ids come
    from trial_order which is seeded from get_all()."""
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
