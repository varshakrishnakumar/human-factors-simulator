# Refactor Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the human-factors-simulator codebase into domain/ui/io layers, extract a pure `TrialEngine`, introduce typed dataclasses, split `views.py` per screen, add a unit-test safety net, and a smoke test — without changing any user-visible behavior or output schema.

**Architecture:** Layered. `sim/domain/` is pure Python (no Streamlit import). `sim/ui/` is Streamlit-only, one file per screen. `sim/io/` wraps persistence. `sim/state.py` is the only bridge that imports both Streamlit and the domain.

**Tech Stack:** Python 3.10+, Streamlit, pandas, gspread, stdlib `dataclasses`. New dev dep: `pytest`.

**Spec reference:** `docs/superpowers/specs/2026-04-18-refactor-framework-design.md`

**Branch:** `refactor/cleanup-2026-04` (already checked out)

**Output schemas are frozen.** Column names and semantics in `assignments`, `events`, `summaries` must not change. Every task that touches an output code path must preserve this.

---

## File inventory (target)

| Path | Purpose | Created / Modified |
|---|---|---|
| `sim/domain/__init__.py` | Package marker | Create |
| `sim/domain/models.py` | All dataclasses | Create |
| `sim/domain/action_help.py` | Global ACTION_HELP dict | Create |
| `sim/domain/conditions.py` | `CONDITIONS`, constants, pure `balanced_condition` | Create |
| `sim/domain/survey.py` | NASA-TLX `QUESTIONS`, `COMMENT_KEYS` | Create |
| `sim/domain/scenarios/__init__.py` | Package marker | Create |
| `sim/domain/scenarios/familiarization.py` | Practice `SCENARIO` | Create |
| `sim/domain/scenarios/nav.py` | NAV `SCENARIO` | Create |
| `sim/domain/scenarios/thermal.py` | THERMAL `SCENARIO` | Create |
| `sim/domain/scenarios/comm.py` | COMM `SCENARIO` | Create |
| `sim/domain/scenarios/registry.py` | `get_all`, `get_by_id`, `get_familiarization`, `linear_candidates` | Create |
| `sim/domain/engine.py` | `TrialEngine` — pure trial lifecycle | Create |
| `sim/domain/scoring.py` | `classify_end`, `aggregate_errors` | Create |
| `sim/ui/__init__.py` | Package marker | Create |
| `sim/ui/styles.py` | Relocated from `sim/styles.py` | Move |
| `sim/ui/widgets.py` | Relocated from `sim/components.py` + additions | Move+Modify |
| `sim/ui/screens/__init__.py` | Package marker | Create |
| `sim/ui/screens/intro.py` | `render_intro_instructions` | Create |
| `sim/ui/screens/sidebar.py` | `render_sidebar_setup` | Create |
| `sim/ui/screens/masthead.py` | `render_study_header` | Create |
| `sim/ui/screens/status_bar.py` | `render_status_bar` | Create |
| `sim/ui/screens/console.py` | `render_console` | Create |
| `sim/ui/screens/linear.py` | Linear picker + progress | Create |
| `sim/ui/screens/branching.py` | Branching checklist + decisions | Create |
| `sim/ui/screens/familiarization_done.py` | `render_familiarization_complete` | Create |
| `sim/ui/screens/survey.py` | `render_final_survey` | Create |
| `sim/ui/screens/summary.py` | `render_session_summary` | Create |
| `sim/io/__init__.py` | Package marker | Create |
| `sim/io/sinks.py` | Relocated from `sim/sinks.py`, trimmed | Move+Modify |
| `sim/io/_sheets.py` | gspread plumbing extracted | Create |
| `sim/state.py` | Phase-scoped dataclasses + bridge | Rewrite |
| `sim/trial.py` | Shrinks to bridge calls | Rewrite |
| `sim/scenarios.py` | Shim, then deleted in Task 7 | Modify → Delete |
| `sim/config.py` | Shrunk in Task 3, deleted in Task 5 | Modify → Delete |
| `sim/components.py` | Moved to `sim/ui/widgets.py` in Task 6 | git mv |
| `sim/styles.py` | Moved to `sim/ui/styles.py` in Task 6 | git mv |
| `sim/sinks.py` | Moved/split into `sim/io/` in Task 5 | Split → Delete original |
| `sim/views.py` | Split into `sim/ui/screens/` in Task 6 | Split → Delete original |
| `simulator.py` | Imports updated | Modify |
| `requirements-dev.txt` | New | Create |
| `tests/__init__.py` | Package marker | Create |
| `tests/conftest.py` | Shared fixtures | Create |
| `tests/test_registry.py` | Registry tests | Create |
| `tests/test_conditions.py` | `balanced_condition` tests | Create |
| `tests/test_engine.py` | Engine unit tests | Create |
| `tests/test_scoring.py` | Scoring unit tests | Create |
| `tests/test_smoke.py` | Import + end-to-end playthrough | Create |
| `pytest.ini` | pytest config | Create |

---

## Task 1: Introduce tests/ scaffold

**Goal:** Add pytest to the project with a minimal passing test so step 2 onward can write assertions.

**Files:**
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/test_scaffold.py`

- [ ] **Step 1.1: Create `requirements-dev.txt`**

```
pytest>=8
```

- [ ] **Step 1.2: Install it**

Run: `pip install -r requirements-dev.txt`
Expected: installs `pytest` and its deps; no errors.

- [ ] **Step 1.3: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 1.4: Create `tests/__init__.py`**

Empty file — makes `tests/` a package so imports are predictable.

- [ ] **Step 1.5: Create `tests/test_scaffold.py`**

```python
def test_scaffold_runs():
    assert True
```

- [ ] **Step 1.6: Run pytest to verify**

Run: `pytest -v`
Expected: `tests/test_scaffold.py::test_scaffold_runs PASSED` and 1 passed.

- [ ] **Step 1.7: Commit**

```bash
git add requirements-dev.txt pytest.ini tests/__init__.py tests/test_scaffold.py
git commit -m "chore: add pytest scaffold with trivial passing test"
```

---

## Task 2: Extract domain models + populate scenario registry

**Goal:** Introduce the typed dataclasses from the spec and convert today's NAV/THERMAL/COMM/FAMILIARIZATION dicts into `Scenario` instances. `sim/scenarios.py` becomes a shim so `sim/trial.py` and `sim/views.py` keep working.

**Files:**
- Create: `sim/domain/__init__.py`
- Create: `sim/domain/models.py`
- Create: `sim/domain/scenarios/__init__.py`
- Create: `sim/domain/scenarios/familiarization.py`
- Create: `sim/domain/scenarios/nav.py`
- Create: `sim/domain/scenarios/thermal.py`
- Create: `sim/domain/scenarios/comm.py`
- Create: `sim/domain/scenarios/registry.py`
- Create: `tests/test_registry.py`
- Modify: `sim/scenarios.py` (become shim)

- [ ] **Step 2.1: Create `sim/domain/__init__.py` (empty)**

- [ ] **Step 2.2: Create `sim/domain/models.py`**

```python
"""Typed domain shapes. No Streamlit import — must be Python-only."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union


@dataclass(frozen=True)
class TriggerCue:
    label: str
    value: str


@dataclass(frozen=True)
class LinearChecklist:
    title: str
    steps: Tuple[str, ...]


@dataclass(frozen=True)
class ActionStep:
    id: int
    text: str
    next: Optional[int]
    note: str = ""
    type: Literal["action"] = "action"


@dataclass(frozen=True)
class DecisionOption:
    label: str
    next: Optional[int]
    correct: bool
    note: str = ""


@dataclass(frozen=True)
class DecisionStep:
    id: int
    prompt: str
    options: Tuple[DecisionOption, ...]
    type: Literal["decision"] = "decision"


@dataclass(frozen=True)
class TerminalStep:
    id: int
    text: str
    note: str = ""
    type: Literal["terminal"] = "terminal"


BranchingStep = Union[ActionStep, DecisionStep, TerminalStep]


@dataclass(frozen=True)
class BranchingChecklist:
    title: str
    steps: Tuple[BranchingStep, ...]


@dataclass(frozen=True)
class AutoTransition:
    time: float
    new_mode: str


@dataclass(frozen=True)
class Scenario:
    id: int
    title: str
    fault: str
    initial_mode: str
    auto_transition: AutoTransition
    correct_mode: str
    trigger_cues: Tuple[TriggerCue, ...]
    linear_checklist: LinearChecklist
    branching_checklist: BranchingChecklist
    action_expected_modes: Dict[str, str]
    is_familiarization: bool = False


@dataclass(frozen=True)
class LinearCandidate:
    scenario_id: int
    title: str
    steps: Tuple[str, ...]
    trigger_cues: Tuple[TriggerCue, ...]


@dataclass(frozen=True)
class Condition:
    key: str
    checklist_type: Literal["linear", "branching"]
    time_limit: int
    label: str


@dataclass(frozen=True)
class TrialContext:
    session_id: str
    participant_id: str
    experience: str
    trial_number: int


@dataclass(frozen=True)
class SurveyQuestion:
    key: str
    label: str
    question: str
    low_anchor: str
    high_anchor: str
    min: int = 1
    max: int = 10
    default: int = 5


@dataclass
class TrialEvent:
    timestamp_s: float
    mode: Optional[str]
    action: str
    extra: Dict[str, Any] = field(default_factory=dict)


EndReason = Literal["completed", "timeout", "wrong_branch", "procedure_end"]


@dataclass
class TrialResult:
    session_id: str
    participant_id: str
    experience: str
    condition: str
    checklist_type: str
    time_limit: int
    trial_number: int
    scenario_id: int
    scenario_title: str
    fault: str
    completion_time_s: float
    end_reason: str
    completed: bool
    timed_out: bool
    wrong_mode_actions: int
    order_errors: int
    branch_decision_errors: int
    checklist_selection_error: int
    selected_checklist_id: Optional[int]
```

- [ ] **Step 2.3: Create `sim/domain/scenarios/__init__.py` (empty)**

- [ ] **Step 2.4: Create `sim/domain/scenarios/familiarization.py`**

Match today's `FAMILIARIZATION` in `sim/scenarios.py` exactly.

```python
from sim.domain.models import (
    ActionStep, AutoTransition, BranchingChecklist,
    LinearChecklist, Scenario, TriggerCue,
)

SCENARIO = Scenario(
    id=0,
    title="Familiarization",
    fault="Practice alert (no real fault)",
    initial_mode="AUTO",
    auto_transition=AutoTransition(time=99999, new_mode="AUTO"),
    correct_mode="AUTO",
    trigger_cues=(
        TriggerCue(label="MODE", value="AUTO"),
        TriggerCue(label="STATUS", value="PRACTICE"),
    ),
    linear_checklist=LinearChecklist(
        title="Practice",
        steps=("ACK PRACTICE ALERT",),
    ),
    branching_checklist=BranchingChecklist(
        title="Practice",
        steps=(
            ActionStep(id=1, text="ACK PRACTICE ALERT", next=None),
        ),
    ),
    action_expected_modes={},
    is_familiarization=True,
)
```

- [ ] **Step 2.5: Create `sim/domain/scenarios/nav.py`**

Port today's `NAV` dict. Use the same id/fields.

```python
from sim.domain.models import (
    ActionStep, AutoTransition, BranchingChecklist, DecisionOption,
    DecisionStep, LinearChecklist, Scenario, TerminalStep, TriggerCue,
)

SCENARIO = Scenario(
    id=1,
    title="Navigation Fault Recovery",
    fault="Loss of navigation data",
    initial_mode="AUTO",
    auto_transition=AutoTransition(time=5, new_mode="HOLD"),
    correct_mode="AUTO",
    trigger_cues=(
        TriggerCue(label="MODE", value="HOLD"),
        TriggerCue(label="STAR TRACKER", value="FAILED"),
        TriggerCue(label="NAV DATA", value="INVALID"),
    ),
    linear_checklist=LinearChecklist(
        title="Navigation Fault Recovery",
        steps=(
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN GNC STATUS PANEL",
            "RESET NAVIGATION FILTER",
            "REINITIALIZE STAR TRACKER",
            "CONFIRM NAVIGATION DATA RESTORED",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ),
    ),
    branching_checklist=BranchingChecklist(
        title="Navigation Fault Recovery",
        steps=(
            ActionStep(id=1, text="ACK ALARM", next=2, note="Acknowledge the caution before proceeding."),
            ActionStep(id=2, text="OPEN GNC STATUS PANEL", next=3, note="Then check the star-tracker indicator on the GNC panel."),
            DecisionStep(
                id=3,
                prompt="Is the star tracker reporting FAILED?",
                options=(
                    DecisionOption(label="Yes — star tracker failed", next=4, correct=True, note="If YES, proceed to STEP 4."),
                    DecisionOption(label="No — star tracker nominal", next=99, correct=False, note="If NO, this checklist does not apply."),
                ),
            ),
            ActionStep(id=4, text="RESET NAVIGATION FILTER", next=5, note="Reset the navigation filter while spacecraft stays in HOLD."),
            ActionStep(id=5, text="REINITIALIZE STAR TRACKER", next=6, note="Reinitialize the star tracker to recover nav data."),
            DecisionStep(
                id=6,
                prompt="Is NAV DATA now valid?",
                options=(
                    DecisionOption(label="Yes — nav data valid", next=7, correct=True, note="If YES, proceed to STEP 7."),
                    DecisionOption(label="No — still invalid", next=4, correct=False, note="If NO, return to STEP 4 and retry."),
                ),
            ),
            ActionStep(id=7, text="SELECT AUTO MODE", next=8),
            ActionStep(id=8, text="VERIFY ATTITUDE STABLE", next=9),
            ActionStep(id=9, text="REPORT PROCEDURE COMPLETE", next=None),
            TerminalStep(id=99, text="WRONG BRANCH — STOP", note="Incorrect diagnosis path. Trial ends."),
        ),
    ),
    action_expected_modes={
        "RESET NAVIGATION FILTER": "HOLD",
        "REINITIALIZE STAR TRACKER": "HOLD",
        "CONFIRM NAVIGATION DATA RESTORED": "HOLD",
        "SELECT AUTO MODE": "HOLD",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    },
)
```

- [ ] **Step 2.6: Create `sim/domain/scenarios/thermal.py`**

```python
from sim.domain.models import (
    ActionStep, AutoTransition, BranchingChecklist, DecisionOption,
    DecisionStep, LinearChecklist, Scenario, TerminalStep, TriggerCue,
)

SCENARIO = Scenario(
    id=2,
    title="Thermal Loop Recovery",
    fault="Radiator bypass valve stuck, thermal loop out of spec",
    initial_mode="AUTO",
    auto_transition=AutoTransition(time=5, new_mode="SAFE"),
    correct_mode="AUTO",
    trigger_cues=(
        TriggerCue(label="MODE", value="SAFE"),
        TriggerCue(label="THERMAL LOOP", value="OVERTEMP"),
        TriggerCue(label="RADIATOR", value="VALVE FAULT"),
    ),
    linear_checklist=LinearChecklist(
        title="Thermal Loop Recovery",
        steps=(
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN THERMAL STATUS PANEL",
            "CYCLE RADIATOR BYPASS VALVE",
            "ENGAGE BACKUP HEATER",
            "CONFIRM THERMAL LOOP STABLE",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ),
    ),
    branching_checklist=BranchingChecklist(
        title="Thermal Loop Recovery",
        steps=(
            ActionStep(id=1, text="ACK ALARM", next=2, note="Acknowledge the thermal caution before proceeding."),
            ActionStep(id=2, text="OPEN THERMAL STATUS PANEL", next=3, note="Then check the radiator bypass valve indicator."),
            DecisionStep(
                id=3,
                prompt="Is the radiator bypass valve reporting a FAULT?",
                options=(
                    DecisionOption(label="Yes — valve fault", next=4, correct=True, note="If YES, proceed to STEP 4."),
                    DecisionOption(label="No — valve nominal", next=99, correct=False, note="If NO, this checklist does not apply."),
                ),
            ),
            ActionStep(id=4, text="CYCLE RADIATOR BYPASS VALVE", next=5, note="Cycle the valve while in SAFE mode."),
            ActionStep(id=5, text="ENGAGE BACKUP HEATER", next=6, note="Bring the redundant heater online."),
            DecisionStep(
                id=6,
                prompt="Is the thermal loop back within spec?",
                options=(
                    DecisionOption(label="Yes — loop stable", next=7, correct=True, note="If YES, proceed to STEP 7."),
                    DecisionOption(label="No — still out of spec", next=4, correct=False, note="If NO, return to STEP 4 and retry."),
                ),
            ),
            ActionStep(id=7, text="SELECT AUTO MODE", next=8),
            ActionStep(id=8, text="VERIFY ATTITUDE STABLE", next=9),
            ActionStep(id=9, text="REPORT PROCEDURE COMPLETE", next=None),
            TerminalStep(id=99, text="WRONG BRANCH — STOP", note="Incorrect diagnosis path. Trial ends."),
        ),
    ),
    action_expected_modes={
        "CYCLE RADIATOR BYPASS VALVE": "SAFE",
        "ENGAGE BACKUP HEATER": "SAFE",
        "CONFIRM THERMAL LOOP STABLE": "SAFE",
        "SELECT AUTO MODE": "SAFE",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    },
)
```

- [ ] **Step 2.7: Create `sim/domain/scenarios/comm.py`**

```python
from sim.domain.models import (
    ActionStep, AutoTransition, BranchingChecklist, DecisionOption,
    DecisionStep, LinearChecklist, Scenario, TerminalStep, TriggerCue,
)

SCENARIO = Scenario(
    id=3,
    title="Communications Loss Recovery",
    fault="Primary downlink failure, ground link lost",
    initial_mode="AUTO",
    auto_transition=AutoTransition(time=5, new_mode="HOLD"),
    correct_mode="AUTO",
    trigger_cues=(
        TriggerCue(label="MODE", value="HOLD"),
        TriggerCue(label="DOWNLINK", value="LOST"),
        TriggerCue(label="RF TRANSCEIVER", value="DEGRADED"),
    ),
    linear_checklist=LinearChecklist(
        title="Communications Loss Recovery",
        steps=(
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN COMM STATUS PANEL",
            "SWITCH TO BACKUP DOWNLINK",
            "REINITIALIZE RF TRANSCEIVER",
            "CONFIRM GROUND LINK RESTORED",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ),
    ),
    branching_checklist=BranchingChecklist(
        title="Communications Loss Recovery",
        steps=(
            ActionStep(id=1, text="ACK ALARM", next=2, note="Acknowledge the comm caution before proceeding."),
            ActionStep(id=2, text="OPEN COMM STATUS PANEL", next=3, note="Then check the downlink status indicator."),
            DecisionStep(
                id=3,
                prompt="Is the primary downlink reporting LOST?",
                options=(
                    DecisionOption(label="Yes — downlink lost", next=4, correct=True, note="If YES, proceed to STEP 4."),
                    DecisionOption(label="No — downlink nominal", next=99, correct=False, note="If NO, this checklist does not apply."),
                ),
            ),
            ActionStep(id=4, text="SWITCH TO BACKUP DOWNLINK", next=5, note="Hand over to the redundant downlink."),
            ActionStep(id=5, text="REINITIALIZE RF TRANSCEIVER", next=6, note="Reinitialize the RF transceiver to re-acquire ground."),
            DecisionStep(
                id=6,
                prompt="Is the ground link active and stable?",
                options=(
                    DecisionOption(label="Yes — ground link restored", next=7, correct=True, note="If YES, proceed to STEP 7."),
                    DecisionOption(label="No — still lost", next=4, correct=False, note="If NO, return to STEP 4 and retry."),
                ),
            ),
            ActionStep(id=7, text="SELECT AUTO MODE", next=8),
            ActionStep(id=8, text="VERIFY ATTITUDE STABLE", next=9),
            ActionStep(id=9, text="REPORT PROCEDURE COMPLETE", next=None),
            TerminalStep(id=99, text="WRONG BRANCH — STOP", note="Incorrect diagnosis path. Trial ends."),
        ),
    ),
    action_expected_modes={
        "SWITCH TO BACKUP DOWNLINK": "HOLD",
        "REINITIALIZE RF TRANSCEIVER": "HOLD",
        "CONFIRM GROUND LINK RESTORED": "HOLD",
        "SELECT AUTO MODE": "HOLD",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    },
)
```

- [ ] **Step 2.8: Create `sim/domain/scenarios/registry.py`**

```python
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
```

- [ ] **Step 2.9: Write `tests/test_registry.py` — failing test for `get_all()` count**

```python
from sim.domain.scenarios import registry


def test_get_all_returns_three_real_scenarios():
    assert len(registry.get_all()) == 3


def test_get_by_id_raises_on_unknown():
    import pytest
    with pytest.raises(KeyError):
        registry.get_by_id(999)


def test_get_by_id_round_trips():
    for s in registry.get_all():
        assert registry.get_by_id(s.id) is s


def test_get_familiarization():
    assert registry.get_familiarization().is_familiarization is True
    assert registry.get_familiarization().id == 0


def test_linear_candidates_match_real_scenarios():
    cands = registry.linear_candidates()
    assert len(cands) == 3
    ids_from_cands = sorted(c.scenario_id for c in cands)
    ids_from_scenarios = sorted(s.id for s in registry.get_all())
    assert ids_from_cands == ids_from_scenarios
```

- [ ] **Step 2.10: Run registry tests**

Run: `pytest tests/test_registry.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 2.11: Rewrite `sim/scenarios.py` as a compatibility shim**

The existing code in `sim/trial.py` and `sim/views.py` uses the old dict-access API (`scenario["scenario_id"]`, `scenario["linear_checklist"]["steps"]`, etc.). We need backwards compatibility until later steps. Keep the old public functions but source from the registry; emit dict-shaped views.

Replace the entire file contents:

```python
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
```

- [ ] **Step 2.12: Verify the app still runs**

Run: `streamlit run simulator.py`
Expected: app boots without errors. Click through a linear trial end-to-end in a browser. Close the server.

- [ ] **Step 2.13: Run all tests**

Run: `pytest -v`
Expected: 6 tests pass (1 scaffold + 5 registry).

- [ ] **Step 2.14: Commit**

```bash
git add sim/domain sim/scenarios.py tests/test_registry.py
git commit -m "refactor: extract Scenario dataclasses and registry; shim sim/scenarios.py"
```

---

## Task 3: Extract conditions, survey, action_help

**Goal:** Move the static config (conditions, survey questions, action help) into `sim/domain/`. `sim/config.py` shrinks to just `LOG_DIR` and `GOOGLE_SCOPES`.

**Files:**
- Create: `sim/domain/conditions.py`
- Create: `sim/domain/survey.py`
- Create: `sim/domain/action_help.py`
- Create: `tests/test_conditions.py`
- Modify: `sim/config.py` (remove moved constants)
- Modify: `sim/trial.py`, `sim/views.py`, `sim/sinks.py` imports

- [ ] **Step 3.1: Create `sim/domain/conditions.py`**

```python
"""Condition catalog + pure balanced_condition. No I/O."""
from typing import Dict, List, Optional, Tuple

from sim.domain.models import Condition

CONDITIONS: Dict[str, Condition] = {
    "linear_high": Condition(
        key="linear_high",
        checklist_type="linear",
        time_limit=45,
        label="Linear · High time pressure",
    ),
    "linear_low": Condition(
        key="linear_low",
        checklist_type="linear",
        time_limit=90,
        label="Linear · Low time pressure",
    ),
    "branching_high": Condition(
        key="branching_high",
        checklist_type="branching",
        time_limit=45,
        label="Branching · High time pressure",
    ),
    "branching_low": Condition(
        key="branching_low",
        checklist_type="branching",
        time_limit=90,
        label="Branching · Low time pressure",
    ),
}

BACKGROUND_OPTIONS: Tuple[str, ...] = (
    "None",
    "Some aviation",
    "Some spacecraft ops",
    "Professional",
)

NUM_REAL_TRIALS: int = 3
FAMILIARIZATION_TIME_LIMIT: int = 600


def balanced_condition(
    experience: str,
    counts: Dict[Tuple[str, str], int],
    condition_keys: List[str],
) -> str:
    """Pick the condition with the fewest prior assignments for this experience.
    Tie-breaker: lowest overall count for the condition; final tie-breaker: list order.
    Falls back to the first condition when no data is available."""
    if not condition_keys:
        return ""
    best_key: Optional[str] = None
    best_score: Optional[Tuple[int, int]] = None
    totals: Dict[str, int] = {
        c: sum(n for (cond, _), n in counts.items() if cond == c)
        for c in condition_keys
    }
    for c in condition_keys:
        per_exp = counts.get((c, experience), 0)
        score = (per_exp, totals[c])
        if best_score is None or score < best_score:
            best_score = score
            best_key = c
    return best_key or condition_keys[0]
```

- [ ] **Step 3.2: Create `sim/domain/survey.py`**

```python
"""NASA-TLX questions as data. Render loop in sim/ui/screens/survey.py iterates
over QUESTIONS; changing wording is a data edit here, not a UI edit."""
from typing import Tuple

from sim.domain.models import SurveyQuestion

QUESTIONS: Tuple[SurveyQuestion, ...] = (
    SurveyQuestion(
        key="nasa_tlx_mental",
        label="Mental demand",
        question="How mentally demanding was operating the console?",
        low_anchor="Very low — easy to think through",
        high_anchor="Very high — had to concentrate hard",
    ),
    SurveyQuestion(
        key="nasa_tlx_temporal",
        label="Temporal demand",
        question="Did you have enough time to do the task well?",
        low_anchor="Very low — plenty of time, never rushed",
        high_anchor="Very high — felt extremely rushed",
    ),
    SurveyQuestion(
        key="nasa_tlx_effort",
        label="Effort",
        question="How hard did you have to work to complete the task?",
        low_anchor="Very low — effortless",
        high_anchor="Very high — had to try very hard",
    ),
    SurveyQuestion(
        key="nasa_tlx_frustration",
        label="Frustration",
        question="How frustrated or annoyed did you feel during the task?",
        low_anchor="Very low — calm and relaxed",
        high_anchor="Very high — very frustrated",
    ),
)

COMMENT_KEYS: Tuple[str, ...] = (
    "tlx_mental_comment",
    "tlx_temporal_comment",
    "tlx_effort_comment",
    "tlx_frustration_comment",
    "general_comment",
)
```

- [ ] **Step 3.3: Create `sim/domain/action_help.py`**

Port `ACTION_HELP` from `sim/config.py:41-60`:

```python
"""Global action-help lookup. Keeps cross-scenario actions in one place."""
from typing import Dict

ACTION_HELP: Dict[str, str] = {
    "ACK ALARM": "Acknowledge the annunciated caution or warning.",
    "SILENCE CAUTION TONE": "Silence the audible tone after acknowledging the alarm.",
    "SELECT AUTO MODE": "Command the spacecraft back into AUTO mode.",
    "VERIFY ATTITUDE STABLE": "Confirm attitude is stable after recovery.",
    "REPORT PROCEDURE COMPLETE": "Report that the recovery procedure is complete.",
    "OPEN GNC STATUS PANEL": "Open the guidance, navigation, and control status panel.",
    "RESET NAVIGATION FILTER": "Reset the navigation filter.",
    "REINITIALIZE STAR TRACKER": "Reinitialize the star tracker to recover nav data.",
    "CONFIRM NAVIGATION DATA RESTORED": "Confirm the navigation solution is valid again.",
    "OPEN THERMAL STATUS PANEL": "Open the thermal control subsystem status panel.",
    "CYCLE RADIATOR BYPASS VALVE": "Cycle the stuck radiator bypass valve.",
    "ENGAGE BACKUP HEATER": "Bring the redundant heater online.",
    "CONFIRM THERMAL LOOP STABLE": "Confirm the thermal loop is back within spec.",
    "OPEN COMM STATUS PANEL": "Open the communications status panel.",
    "SWITCH TO BACKUP DOWNLINK": "Hand over to the redundant downlink path.",
    "REINITIALIZE RF TRANSCEIVER": "Reinitialize the RF transceiver.",
    "CONFIRM GROUND LINK RESTORED": "Confirm the ground link is active and stable.",
    "ACK PRACTICE ALERT": "Acknowledge the practice alert to complete the warm-up.",
}
```

- [ ] **Step 3.4: Write `tests/test_conditions.py` — failing tests**

```python
from sim.domain.conditions import balanced_condition


def test_empty_counts_returns_first_key():
    assert balanced_condition("None", {}, ["a", "b", "c"]) == "a"


def test_picks_min_per_experience():
    counts = {("a", "None"): 2, ("b", "None"): 0, ("c", "None"): 1}
    assert balanced_condition("None", counts, ["a", "b", "c"]) == "b"


def test_tie_broken_by_overall_count():
    counts = {
        ("a", "None"): 0, ("b", "None"): 0, ("c", "None"): 0,
        ("a", "Professional"): 5, ("b", "Professional"): 1,
    }
    # All three tie on ("_", "None") = 0. Overall counts: a=5, b=1, c=0.
    assert balanced_condition("None", counts, ["a", "b", "c"]) == "c"


def test_tie_final_fallback_is_list_order():
    counts = {("a", "None"): 0, ("b", "None"): 0}
    assert balanced_condition("None", counts, ["a", "b"]) == "a"


def test_unknown_experience_treated_as_zero():
    counts = {("a", "Known"): 5, ("b", "Known"): 10}
    # "Novel" experience not in counts → both conditions score 0 on first key,
    # tie-broken by overall count. Totals: a=5, b=10. Winner: a.
    assert balanced_condition("Novel", counts, ["a", "b"]) == "a"


def test_empty_condition_keys_returns_empty():
    assert balanced_condition("None", {}, []) == ""
```

- [ ] **Step 3.5: Run the new tests**

Run: `pytest tests/test_conditions.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 3.6: Update `sim/config.py` — keep only I/O constants**

Replace the file contents with:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
```

(Removes `CONDITIONS`, `BACKGROUND_OPTIONS`, `ACTION_HELP`, `NUM_REAL_TRIALS`, `FAMILIARIZATION_TIME_LIMIT` — they now live in domain.)

- [ ] **Step 3.7: Update `sim/trial.py` imports**

Change the import at the top:

```python
from sim.config import (
    CONDITIONS,
    FAMILIARIZATION_TIME_LIMIT,
    NUM_REAL_TRIALS,
)
```

To:

```python
from sim.domain.conditions import (
    CONDITIONS,
    FAMILIARIZATION_TIME_LIMIT,
    NUM_REAL_TRIALS,
)
```

The existing code uses `CONDITIONS[key]["checklist_type"]` — dict-access on a `Condition` dataclass will fail. Add a small compat layer in `sim/trial.py` or change access sites. Simpler: temporarily expose a dict view via `sim/trial.py` private helper. Add these at the top of `sim/trial.py` just after imports:

```python
# TEMPORARY: dict-style access over the new Condition dataclasses, removed
# once the engine refactor (Task 4) replaces these call sites.
_CONDITIONS_DICT = {
    k: {"checklist_type": c.checklist_type, "time_limit": c.time_limit, "label": c.label}
    for k, c in CONDITIONS.items()
}
```

Then replace every `CONDITIONS[...]["..."]` read in the file with `_CONDITIONS_DICT[...]["..."]`. Specifically:

- Line 35 (`CONDITIONS[key]["time_limit"]`) → `_CONDITIONS_DICT[key]["time_limit"]`
- Line 54 (`CONDITIONS[key]["checklist_type"]`) → `_CONDITIONS_DICT[key]["checklist_type"]`
- Line 122 (`CONDITIONS[st.session_state.condition_key]["checklist_type"]`) → `_CONDITIONS_DICT[...]["checklist_type"]`
- Line 123 (`CONDITIONS[...]["time_limit"]`) → `_CONDITIONS_DICT[...]["time_limit"]`

- [ ] **Step 3.8: Update `sim/views.py` imports**

Change:

```python
from sim.config import ACTION_HELP, BACKGROUND_OPTIONS, CONDITIONS
```

To:

```python
from sim.domain.action_help import ACTION_HELP
from sim.domain.conditions import BACKGROUND_OPTIONS, CONDITIONS
```

And in `sim/views.py`, every `CONDITIONS[key]["label"]` read becomes `CONDITIONS[key].label`. Affected lines: 46, 79, 118. `BACKGROUND_OPTIONS.index(...)` still works since it's a tuple (was a list, now tuple — `.index()` exists on both).

- [ ] **Step 3.9: Update `sim/sinks.py` — no changes yet**

`sinks.py` imports `GOOGLE_SCOPES` and `LOG_DIR` from `sim.config`; those still exist. Leave `sinks.py` alone in this task.

- [ ] **Step 3.10: Run the app manually**

Run: `streamlit run simulator.py`
Expected: app boots, sidebar shows conditions with correct labels, action buttons have tooltips. Click through a linear trial.

- [ ] **Step 3.11: Run all tests**

Run: `pytest -v`
Expected: 12 tests pass (1 scaffold + 5 registry + 6 conditions).

- [ ] **Step 3.12: Commit**

```bash
git add sim/config.py sim/domain/conditions.py sim/domain/survey.py sim/domain/action_help.py sim/trial.py sim/views.py tests/test_conditions.py
git commit -m "refactor: move conditions/survey/action_help into sim/domain"
```

---

## Task 4: Extract TrialEngine + scoring

**Goal:** Lift the trial-lifecycle logic out of `sim/trial.py` into a pure `sim/domain/engine.py` + `sim/domain/scoring.py`. `sim/trial.py` becomes the state bridge — it calls engine methods via a loaded/saved snapshot. Unit tests cover the engine.

This is the biggest and most important task. Take your time. Several sub-tasks.

**Files:**
- Create: `sim/domain/engine.py`
- Create: `sim/domain/scoring.py`
- Modify: `sim/trial.py` (becomes a bridge)
- Create: `tests/conftest.py`
- Create: `tests/test_scoring.py`
- Create: `tests/test_engine.py`

### 4.a — Engine scaffold + constructor

- [ ] **Step 4.1: Create `sim/domain/scoring.py` — initial skeleton**

```python
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
```

- [ ] **Step 4.2: Create `sim/domain/engine.py` — class skeleton**

```python
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
```

- [ ] **Step 4.3: Create `tests/conftest.py`**

```python
"""Shared fixtures for engine/scoring tests. Build minimal scenarios inline
instead of importing the real ones — keeps tests readable and isolated."""
from typing import Iterable

import pytest

from sim.domain.models import (
    ActionStep, AutoTransition, BranchingChecklist, Condition, DecisionOption,
    DecisionStep, LinearChecklist, Scenario, TerminalStep, TrialContext,
    TriggerCue,
)


@pytest.fixture
def ctx() -> TrialContext:
    return TrialContext(
        session_id="s1",
        participant_id="p1",
        experience="None",
        trial_number=1,
    )


@pytest.fixture
def condition_linear() -> Condition:
    return Condition(key="linear_high", checklist_type="linear", time_limit=60, label="L-H")


@pytest.fixture
def condition_branching() -> Condition:
    return Condition(key="branching_high", checklist_type="branching", time_limit=60, label="B-H")


@pytest.fixture
def linear_scenario() -> Scenario:
    return Scenario(
        id=1,
        title="Test Linear",
        fault="Test fault",
        initial_mode="AUTO",
        auto_transition=AutoTransition(time=99999, new_mode="AUTO"),
        correct_mode="AUTO",
        trigger_cues=(TriggerCue("MODE", "AUTO"),),
        linear_checklist=LinearChecklist(title="L", steps=("A", "B", "C")),
        branching_checklist=BranchingChecklist(title="B", steps=()),
        action_expected_modes={"B": "HOLD"},
    )


@pytest.fixture
def branching_scenario() -> Scenario:
    return Scenario(
        id=2,
        title="Test Branching",
        fault="Test fault",
        initial_mode="AUTO",
        auto_transition=AutoTransition(time=99999, new_mode="AUTO"),
        correct_mode="AUTO",
        trigger_cues=(TriggerCue("MODE", "AUTO"),),
        linear_checklist=LinearChecklist(title="L", steps=()),
        branching_checklist=BranchingChecklist(title="B", steps=(
            ActionStep(id=1, text="ACK", next=2),
            DecisionStep(id=2, prompt="Is X?", options=(
                DecisionOption(label="yes", next=3, correct=True),
                DecisionOption(label="no", next=99, correct=False),
            )),
            ActionStep(id=3, text="FIX", next=4),
            ActionStep(id=4, text="REPORT COMPLETE", next=None),
            TerminalStep(id=99, text="WRONG"),
        )),
        action_expected_modes={},
    )


@pytest.fixture
def familiarization_scenario() -> Scenario:
    return Scenario(
        id=0,
        title="Practice",
        fault="Practice",
        initial_mode="AUTO",
        auto_transition=AutoTransition(time=99999, new_mode="AUTO"),
        correct_mode="AUTO",
        trigger_cues=(),
        linear_checklist=LinearChecklist(title="P", steps=("ACK PRACTICE ALERT",)),
        branching_checklist=BranchingChecklist(title="P", steps=()),
        action_expected_modes={},
        is_familiarization=True,
    )
```

### 4.b — Test-driving the engine

For each test sub-step, write the test first, run it to see it fail (if the test is checking behavior not yet in the engine), then verify the skeleton in step 4.2 already makes it pass. Most of our engine logic is written up front in 4.2 because the current code is our spec; these tests lock it down. If a test fails, debug the engine. Do not change expectations.

- [ ] **Step 4.4: `test_engine.py` — familiarization completion**

Create `tests/test_engine.py`:

```python
from sim.domain.engine import TrialEngine


def test_familiarization_completes_on_practice_action(ctx, condition_linear, familiarization_scenario):
    engine = TrialEngine(familiarization_scenario, condition_linear, ctx, start_time=0.0)
    engine.execute_action("ACK PRACTICE ALERT", now=1.0)
    assert engine.is_finished()
    assert engine.end_reason() == "completed"
```

Run: `pytest tests/test_engine.py::test_familiarization_completes_on_practice_action -v`
Expected: PASS.

- [ ] **Step 4.5: Linear correct order**

Append to `test_engine.py`:

```python
def test_linear_correct_order(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("A", now=1.0)
    # "B" expects mode=HOLD; we're still in AUTO, so wrong_mode will fire.
    # Put mode into HOLD first via auto-transition isn't applicable here (99999s).
    # Instead, verify order is respected and wrong_mode_actions counts only the
    # expected-mode mismatch. The scenario.correct_mode is AUTO so completion
    # requires ending in AUTO, which we are.
    engine.execute_action("B", now=2.0)
    engine.execute_action("C", now=3.0)
    assert engine.is_finished()
    assert engine.end_reason() == "completed"
    assert engine.order_errors == 0
    # B expects HOLD, we were AUTO, so one wrong-mode:
    assert engine.wrong_mode_actions == 1
```

Run: `pytest tests/test_engine.py::test_linear_correct_order -v`
Expected: PASS.

- [ ] **Step 4.6: Linear order error**

```python
def test_linear_order_error_increments(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    # Skip "A", try "B" first
    engine.execute_action("B", now=1.0)
    assert engine.order_errors == 1
    # "B" still records (no enforcement)
    assert "B" in engine.completed_actions
```

Run and verify PASS.

- [ ] **Step 4.7: Linear wrong checklist picked**

```python
def test_linear_wrong_checklist_sets_error_flag(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(scenario_id=999, now=0.1)
    assert engine.checklist_selection_error is True
    assert engine.selected_checklist_id == 999
    assert not engine.is_finished()
```

Run and verify PASS.

- [ ] **Step 4.8: Branching correct path**

```python
def test_branching_correct_path_completes(ctx, condition_branching, branching_scenario):
    engine = TrialEngine(branching_scenario, condition_branching, ctx, start_time=0.0)
    engine.execute_action("ACK", now=1.0)
    # After step 1, branch_step_id == 2 (decision)
    engine.submit_decision(0, now=2.0)  # "yes" → next=3
    engine.execute_action("FIX", now=3.0)
    engine.execute_action("REPORT COMPLETE", now=4.0)
    assert engine.is_finished()
    assert engine.end_reason() == "completed"
    assert engine.branch_path == [1, 2, 3, 4]
    assert engine.branch_decision_errors == 0
```

Run and verify PASS.

- [ ] **Step 4.9: Branching wrong decision → terminal**

```python
def test_branching_wrong_decision_hits_terminal(ctx, condition_branching, branching_scenario):
    engine = TrialEngine(branching_scenario, condition_branching, ctx, start_time=0.0)
    engine.execute_action("ACK", now=1.0)
    engine.submit_decision(1, now=2.0)  # "no" → next=99 (terminal)
    # After submit, classify_end sees current step as TerminalStep → wrong_branch
    assert engine.is_finished()
    assert engine.end_reason() == "wrong_branch"
    assert engine.branch_decision_errors == 1
```

Run and verify PASS.

- [ ] **Step 4.9b: Branching retry loop (wrong decision with `next` pointing back)**

Append to `test_engine.py`:

```python
def test_branching_wrong_decision_can_loop_back(ctx, condition_branching):
    """When a wrong-but-non-terminal decision routes back to an earlier step,
    branch_decision_errors increments AND the path resumes — engine does NOT finish."""
    from sim.domain.models import (
        ActionStep, AutoTransition, BranchingChecklist, DecisionOption,
        DecisionStep, LinearChecklist, Scenario, TriggerCue,
    )
    scenario = Scenario(
        id=10, title="Retry", fault="F", initial_mode="AUTO",
        auto_transition=AutoTransition(time=99999, new_mode="AUTO"),
        correct_mode="AUTO",
        trigger_cues=(TriggerCue("a", "b"),),
        linear_checklist=LinearChecklist(title="L", steps=()),
        branching_checklist=BranchingChecklist(title="B", steps=(
            ActionStep(id=1, text="A1", next=2),
            DecisionStep(id=2, prompt="Done?", options=(
                DecisionOption(label="yes", next=3, correct=True),
                DecisionOption(label="no, retry", next=1, correct=False),
            )),
            ActionStep(id=3, text="REPORT", next=None),
        )),
        action_expected_modes={},
    )
    engine = TrialEngine(scenario, condition_branching, ctx, start_time=0.0)
    engine.execute_action("A1", now=1.0)
    # At decision step — pick wrong option, which loops back to step 1
    engine.submit_decision(1, now=2.0)
    assert not engine.is_finished()
    assert engine.branch_decision_errors == 1
    assert engine.branch_step_id == 1  # routed back
    assert engine.branch_path[-1] == 2  # decision step recorded in path
    # Second attempt: execute A1 again, pick correct option
    engine.execute_action("A1", now=3.0)
    engine.submit_decision(0, now=4.0)
    engine.execute_action("REPORT", now=5.0)
    assert engine.is_finished()
    assert engine.end_reason() == "completed"
    assert engine.branch_decision_errors == 1  # not re-incremented on correct pass
```

Run: `pytest tests/test_engine.py::test_branching_wrong_decision_can_loop_back -v`
Expected: PASS.

- [ ] **Step 4.10: Timeout**

```python
def test_timeout(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.tick(now=condition_linear.time_limit + 1)
    assert engine.is_finished()
    assert engine.end_reason() == "timeout"
```

Run and verify PASS.

- [ ] **Step 4.11: Auto-transition logs event**

```python
def test_auto_transition_changes_mode_and_logs(ctx, condition_linear):
    from sim.domain.models import (
        AutoTransition, BranchingChecklist, LinearChecklist, Scenario, TriggerCue,
    )
    scenario = Scenario(
        id=1, title="T", fault="T", initial_mode="AUTO",
        auto_transition=AutoTransition(time=5, new_mode="HOLD"),
        correct_mode="AUTO",
        trigger_cues=(TriggerCue("a", "b"),),
        linear_checklist=LinearChecklist(title="L", steps=("A",)),
        branching_checklist=BranchingChecklist(title="B", steps=()),
        action_expected_modes={},
    )
    engine = TrialEngine(scenario, condition_linear, ctx, start_time=0.0)
    engine.tick(now=6.0)
    assert engine.mode == "HOLD"
    events = [e.action for e in engine.event_log()]
    assert "AUTO TRANSITION" in events
```

Run and verify PASS.

- [ ] **Step 4.12: Output schema lock — TrialResult keys**

```python
def test_result_keys_match_frozen_schema(ctx, condition_linear, familiarization_scenario):
    import dataclasses
    engine = TrialEngine(familiarization_scenario, condition_linear, ctx, start_time=0.0)
    engine.execute_action("ACK PRACTICE ALERT", now=1.0)
    result = engine.result()
    expected = {
        "session_id", "participant_id", "experience", "condition",
        "checklist_type", "time_limit", "trial_number", "scenario_id",
        "scenario_title", "fault", "completion_time_s", "end_reason",
        "completed", "timed_out", "wrong_mode_actions", "order_errors",
        "branch_decision_errors", "checklist_selection_error",
        "selected_checklist_id",
    }
    assert set(dataclasses.asdict(result).keys()) == expected
```

Run and verify PASS.

- [ ] **Step 4.13: `test_scoring.py` — aggregate_errors**

```python
from sim.domain.models import TrialResult
from sim.domain.scoring import aggregate_errors


def _make_result(**overrides):
    base = dict(
        session_id="s", participant_id="p", experience="None",
        condition="c", checklist_type="linear", time_limit=60,
        trial_number=1, scenario_id=1, scenario_title="t", fault="f",
        completion_time_s=1.0, end_reason="completed", completed=True,
        timed_out=False, wrong_mode_actions=0, order_errors=0,
        branch_decision_errors=0, checklist_selection_error=0,
        selected_checklist_id=1,
    )
    base.update(overrides)
    return TrialResult(**base)


def test_aggregate_errors_sums_all_four():
    r = _make_result(
        order_errors=1, wrong_mode_actions=2,
        branch_decision_errors=3, checklist_selection_error=1,
    )
    assert aggregate_errors(r) == 7
```

Run: `pytest tests/test_scoring.py -v`
Expected: PASS.

- [ ] **Step 4.14: Run the full suite**

Run: `pytest -v`
Expected: all engine + scoring + conditions + registry + scaffold tests pass (~20 tests).

### 4.c — Rewire `sim/trial.py` to use the engine

- [ ] **Step 4.15: Rewrite `sim/trial.py` as a state bridge**

Replace `sim/trial.py` entirely with:

```python
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
from sim.sinks import persist, record_assignment
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
```

Remaining callers (`sim/views.py`, `simulator.py`) still see the old function names and mostly dict-shaped scenario — shim handled by the compat layer in `sim/scenarios.py`.

- [ ] **Step 4.16: Update `sim/state.py`'s `_DEFAULTS`**

`sim/state.py` still has `"scenario": None`, `"mode": None`, `"trial_started": False`, etc. — these are unused by the new bridge. Leave them in place for now (harmless) so we don't break screens that still read them. They'll be purged in Task 7.

But: `_TRIAL_RESET_KEYS` deletes `"completed_actions"`, `"mode"`, `"scenario"`, etc. Those are also unused by bridge but still in state.py. Leave them — harmless.

No change in this step.

- [ ] **Step 4.17: Fix sidebar in `sim/views.py`**

`sim/views.py:79` reads `CONDITIONS[st.session_state.condition_key]['label']` (already fixed in Task 3 to use `.label`). Check.

Confirm `sim/views.py` compiles (run `python -c "from sim import views"` — expect no import error).

- [ ] **Step 4.18: Manual smoke test**

Run: `streamlit run simulator.py`
Expected: session starts; familiarization runs (one-button click completes practice); advances to Trial 1; linear pick works; linear trial completes; branching trial completes; summary shows results. Session survey submits.

- [ ] **Step 4.19: Run all tests**

Run: `pytest -v`
Expected: all pass.

- [ ] **Step 4.20: Commit**

```bash
git add sim/domain/engine.py sim/domain/scoring.py sim/trial.py tests/conftest.py tests/test_engine.py tests/test_scoring.py
git commit -m "refactor: extract pure TrialEngine + scoring; sim/trial.py becomes a bridge"
```

---

## Task 5: Relocate IO layer

**Goal:** Move `sim/sinks.py` to `sim/io/sinks.py`, split gspread plumbing into `sim/io/_sheets.py`. Delete `sim/config.py` (its remaining two constants move into `sim/io/_sheets.py`).

**Files:**
- Create: `sim/io/__init__.py`
- Create: `sim/io/_sheets.py`
- Create: `sim/io/sinks.py`
- Delete: `sim/sinks.py`
- Delete: `sim/config.py`
- Modify: `sim/trial.py` imports

- [ ] **Step 5.1: Create `sim/io/__init__.py`** (empty)

- [ ] **Step 5.2: Create `sim/io/_sheets.py`**

```python
"""Google Sheets plumbing. Keep this file free of simulator-domain knowledge."""
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheet_client():
    if gspread is None or Credentials is None:
        return None
    try:
        has_secret = "gcp_service_account" in st.secrets
    except Exception:
        return None
    if not has_secret:
        return None
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=GOOGLE_SCOPES
        )
        return gspread.authorize(creds)
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    client = get_sheet_client()
    if client is None:
        return None
    try:
        spreadsheet_id = st.secrets.get("google_sheets", {}).get("spreadsheet_id")
    except Exception:
        return None
    if not spreadsheet_id:
        return None
    try:
        return client.open_by_key(spreadsheet_id)
    except Exception:
        return None


def get_worksheet(name: str, rows: int = 1000, cols: int = 40):
    spreadsheet = get_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        return spreadsheet.worksheet(name)
    except Exception:
        try:
            return spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)
        except Exception:
            return None


def append_sheet(name: str, rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return True
    ws = get_worksheet(name)
    if ws is None:
        return False
    try:
        row_headers = list(rows[0].keys())
        existing = ws.row_values(1)
        if not existing:
            headers = row_headers
            ws.append_row(headers)
        else:
            headers = existing[:]
            for h in row_headers:
                if h not in headers:
                    headers.append(h)
            if headers != existing:
                ws.update([headers], "A1")
        values = [[r.get(c, "") for c in headers] for r in rows]
        ws.append_rows(values, value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False
```

- [ ] **Step 5.3: Create `sim/io/sinks.py`**

```python
"""Persistence surface. Hides backend choice (Sheets-first, local CSV fallback).
Hides identity of `balanced_condition` pure vs I/O."""
from typing import Any, Dict, List, Tuple

import pandas as pd

from sim.domain.conditions import balanced_condition as _pure_balanced_condition
from sim.io._sheets import LOG_DIR, append_sheet, get_worksheet


def _append_local(name: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{name}.csv"
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header)
    return str(path)


def persist(name: str, rows: List[Dict[str, Any]]) -> str:
    if append_sheet(name, rows):
        return "google_sheets"
    return _append_local(name, rows)


def record_assignment(assignment: Dict[str, Any]) -> str:
    return persist("assignments", [assignment])


def read_assignment_counts() -> Dict[Tuple[str, str], int]:
    ws = get_worksheet("assignments")
    if ws is None:
        return {}
    try:
        records = ws.get_all_records()
    except Exception:
        return {}
    counts: Dict[Tuple[str, str], int] = {}
    for r in records:
        key = (str(r.get("condition", "")), str(r.get("experience", "")))
        counts[key] = counts.get(key, 0) + 1
    return counts


def balanced_condition(experience: str, condition_keys: List[str]) -> str:
    """I/O wrapper — reads counts from Sheets, delegates to pure domain func."""
    counts = read_assignment_counts()
    return _pure_balanced_condition(experience, counts, condition_keys)
```

- [ ] **Step 5.4: Update imports — `sim/trial.py`**

Change:

```python
from sim.sinks import persist, record_assignment
```

To:

```python
from sim.io.sinks import persist, record_assignment
```

- [ ] **Step 5.5: Update imports — `sim/views.py`**

Change:

```python
from sim.sinks import balanced_condition
```

To:

```python
from sim.io.sinks import balanced_condition
```

- [ ] **Step 5.6: Delete `sim/sinks.py`**

Run: `git rm sim/sinks.py`

- [ ] **Step 5.7: Delete `sim/config.py`**

`sim/config.py` now only has `LOG_DIR`, `GOOGLE_SCOPES`, `BASE_DIR` — all moved into `sim/io/_sheets.py`.

Run: `git rm sim/config.py`

- [ ] **Step 5.8: Verify no remaining imports**

Run: `grep -R "from sim.config" sim/` and `grep -R "from sim.sinks" sim/`
Expected: no output (no remaining references).

- [ ] **Step 5.9: Manual smoke test**

Run: `streamlit run simulator.py` — click through a session.

- [ ] **Step 5.10: Run all tests**

Run: `pytest -v`
Expected: all pass.

- [ ] **Step 5.11: Commit**

```bash
git add -A
git commit -m "refactor: relocate sinks to sim/io/, split gspread plumbing into _sheets.py"
```

---

## Task 6: Split views.py into ui/screens/

**Goal:** Break the 654-line `sim/views.py` into one file per screen. Move `components.py` to `sim/ui/widgets.py`, `styles.py` to `sim/ui/styles.py`.

**Files:**
- Create: `sim/ui/__init__.py`, `sim/ui/screens/__init__.py`
- Create: `sim/ui/styles.py`, `sim/ui/widgets.py`
- Create: 10 screen files under `sim/ui/screens/`
- Delete: `sim/views.py`, `sim/components.py`, `sim/styles.py`
- Modify: `simulator.py` imports

- [ ] **Step 6.1: Create `sim/ui/__init__.py` and `sim/ui/screens/__init__.py`** (both empty)

- [ ] **Step 6.2: Move `sim/styles.py` → `sim/ui/styles.py`**

```bash
git mv sim/styles.py sim/ui/styles.py
```

Contents unchanged. (`inject_styles()` remains.)

- [ ] **Step 6.3: Move `sim/components.py` → `sim/ui/widgets.py`**

```bash
git mv sim/components.py sim/ui/widgets.py
```

Contents unchanged. (The file is already pure render helpers.)

- [ ] **Step 6.4: Create `sim/ui/screens/intro.py`**

Copy the body of `render_intro_instructions` from `sim/views.py:132-187`:

```python
import streamlit as st

from sim.ui.widgets import render_notice


def render() -> None:
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
```

- [ ] **Step 6.5: Create `sim/ui/screens/sidebar.py`**

Copy `render_sidebar_setup` from `sim/views.py:72-127`:

```python
import streamlit as st

from sim.domain.conditions import BACKGROUND_OPTIONS, CONDITIONS
from sim.io.sinks import balanced_condition
from sim.trial import start_session


def render() -> None:
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
        index=list(BACKGROUND_OPTIONS).index(st.session_state.experience),
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
```

- [ ] **Step 6.6: Create `sim/ui/screens/masthead.py`**

Copy `render_study_header` from `sim/views.py:37-67`:

```python
import streamlit as st

from sim.domain.conditions import CONDITIONS
from sim.trial import current_trial_number, total_trials
from sim.ui.widgets import esc


def render() -> None:
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
```

- [ ] **Step 6.7: Create `sim/ui/screens/status_bar.py`**

```python
import streamlit as st

from sim.trial import current_scenario, current_time_limit, remaining_time, trial_started
from sim.ui.widgets import esc, mode_color, mode_glow


def render() -> None:
    scenario = current_scenario()
    if not scenario or not trial_started():
        return
    if st.session_state.in_familiarization:
        timer_html = ('<div class="hf-statusbar-cell"><div class="hf-statusbar-label">PRACTICE</div>'
                      '<div class="hf-statusbar-value" style="color:var(--hf-green);">No timer</div></div>')
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
```

Note: still reads `st.session_state.mode` and `st.session_state.in_familiarization` directly because Task 4 left those flags in place. Task 7 will convert `st.session_state.mode` → the engine's mode (e.g. via `sim.trial.current_mode()`).

- [ ] **Step 6.8: Create `sim/ui/screens/console.py`**

```python
import streamlit as st

from sim.domain.action_help import ACTION_HELP
from sim.trial import checklist_type, current_action_buttons, current_scenario, execute_action
from sim.ui.widgets import render_notice, render_section_header, render_trigger_cues


def render() -> None:
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
```

- [ ] **Step 6.9: Create `sim/ui/screens/linear.py`**

```python
from typing import Any, Dict

import streamlit as st

from sim.domain.scenarios.registry import linear_candidates
from sim.trial import current_scenario, picked_linear_checklist, select_linear_checklist
from sim.ui.widgets import esc, render_notice, render_section_header


def render() -> None:
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
    for cand in linear_candidates():
        cues_html = " · ".join(
            f'<span style="color:var(--hf-amber); font-family:SFMono-Regular,Menlo,Consolas,monospace;'
            f' font-size:0.72rem; letter-spacing:0.1em;">{esc(c.label)}: {esc(c.value)}</span>'
            for c in cand.trigger_cues
        )
        st.markdown(
            f'<div class="hf-choice-card">'
            f'<div class="hf-choice-title">Checklist {cand.scenario_id} — {esc(cand.title)}</div>'
            f'<div style="margin-bottom:0.3rem;">{cues_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"See all steps for Checklist {cand.scenario_id}"):
            steps_html = "".join(
                f'<div class="hf-choice-step">{i:02d}. {esc(s)}</div>'
                for i, s in enumerate(cand.steps, start=1)
            )
            st.markdown(steps_html, unsafe_allow_html=True)
        if st.button(
            f"Use Checklist {cand.scenario_id}",
            key=f"pick_{cand.scenario_id}",
            use_container_width=True,
        ):
            select_linear_checklist(cand.scenario_id)
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
```

Note: `linear_candidates()` is imported from the registry (returns `LinearCandidate` dataclasses, so `.label`/`.value`/`.scenario_id` attribute access). The `picked` dict still comes from the Task 4 shim; Task 7 converts these to dataclass access. `st.session_state.selected_checklist_id` and `st.session_state.completed_actions` are still the legacy session-state flags at this point; Task 7 replaces them with engine accessors.

- [ ] **Step 6.10: Create `sim/ui/screens/branching.py`**

```python
import streamlit as st

from sim.trial import current_scenario, submit_branching_decision
from sim.ui.widgets import esc, render_notice, render_section_header


def render() -> None:
    scenario = current_scenario()
    if not scenario:
        return

    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)

    if st.session_state.in_familiarization:
        # Practice uses the linear practice renderer — branching screen should not
        # be invoked during familiarization. Fall through safely.
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
```

Note: current code's `render_branching_checklist` called `_render_practice_checklist` during familiarization. Branching screen shouldn't run in familiarization because `simulator.py` only dispatches to it when `checklist_type() == "branching"`, and the familiarization scenario always uses the linear layout with the shim. We therefore short-circuit on `in_familiarization` rather than duplicate the practice renderer. Sanity-check in manual smoke test.

- [ ] **Step 6.11: Create `sim/ui/screens/familiarization_done.py`**

Port `render_familiarization_complete` from `sim/views.py:482-490`:

```python
import streamlit as st

from sim.trial import advance_after_trial
from sim.ui.widgets import render_notice


def render() -> None:
    render_notice(
        "Practice complete. The real trials each have a time limit — click Start "
        "Trial 1 when you're ready to begin.",
        "success",
    )
    if st.button("Start Trial 1", type="primary", use_container_width=True):
        advance_after_trial()
        st.rerun()
```

- [ ] **Step 6.12: Create `sim/ui/screens/survey.py`**

Refactor `render_final_survey` (`sim/views.py:529-613`) to iterate `QUESTIONS` and `COMMENT_KEYS`:

```python
import streamlit as st

from sim.domain.survey import COMMENT_KEYS, QUESTIONS
from sim.trial import submit_session_survey
from sim.ui.widgets import esc, render_notice, render_section_header


def _tlx_slider(question_obj) -> int:
    st.markdown(
        f'<div class="hf-tlx-block">'
        f'<div class="hf-tlx-label">{esc(question_obj.label)}</div>'
        f'<div class="hf-tlx-question">{esc(question_obj.question)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    value = st.slider(
        question_obj.label,
        min_value=question_obj.min,
        max_value=question_obj.max,
        value=question_obj.default,
        step=1,
        key=f"tlx_{question_obj.key}",
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="hf-tlx-anchors">'
        f'<span><strong>{question_obj.min}</strong> — {esc(question_obj.low_anchor)}</span>'
        f'<span class="hf-tlx-current">Your rating: <strong>{value}</strong> / {question_obj.max}</span>'
        f'<span><strong>{question_obj.max}</strong> — {esc(question_obj.high_anchor)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    return value


def render() -> None:
    st.markdown('<div class="hf-checklist-panel">', unsafe_allow_html=True)
    render_section_header("Workload Survey", "One-time survey covering the whole session")
    render_notice(
        "Reflect on the whole session. The scales are from the NASA Task Load Index "
        "(NASA-TLX). Every slider runs 1 to 10 — the label under each slider tells you "
        "what each end of the scale means. Use the comment boxes to add a sentence or "
        "two of context if you'd like — full sentences are welcome.",
        "info",
    )

    values: dict = {}
    for q in QUESTIONS:
        values[q.key] = _tlx_slider(q)
        # Per-question comment. Comment keys follow the pattern tlx_<suffix>_comment.
        suffix = q.key.replace("nasa_tlx_", "")
        comment_key = f"tlx_{suffix}_comment"
        values[comment_key] = st.text_area(
            f"Anything you'd like to add about {q.label.lower()}?",
            key=comment_key,
        )
    values["general_comment"] = st.text_area(
        "General comments — anything else worth sharing about the experience?",
        key="general_comment",
    )

    if st.button("Submit survey", type="primary", use_container_width=True):
        submit_session_survey(values)
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
```

- [ ] **Step 6.13: Create `sim/ui/screens/summary.py`**

```python
from typing import Any, Dict, List

import streamlit as st

from sim.ui.widgets import esc, render_notice, render_rocket_celebration, render_section_header


def render() -> None:
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
```

- [ ] **Step 6.14: Update `simulator.py` imports**

Replace:

```python
from sim.styles import inject_styles
from sim.views import (
    render_branching_checklist, render_console, render_familiarization_complete,
    render_final_survey, render_intro_instructions, render_linear_checklist,
    render_session_summary, render_sidebar_setup, render_status_bar,
    render_study_header,
)
```

With:

```python
from sim.ui.styles import inject_styles
from sim.ui.screens import (
    branching, console, familiarization_done, intro, linear,
    masthead, sidebar, status_bar, summary, survey,
)
```

Update the call sites in `main()`:

- `render_sidebar_setup()` → `sidebar.render()`
- `render_study_header()` → `masthead.render()`
- `render_intro_instructions()` → `intro.render()`
- `render_status_bar()` → `status_bar.render()`
- `render_console()` → `console.render()`
- `render_linear_checklist()` → `linear.render()`
- `render_branching_checklist()` → `branching.render()`
- `render_familiarization_complete()` → `familiarization_done.render()`
- `render_final_survey()` → `survey.render()`
- `render_session_summary()` → `summary.render()`

- [ ] **Step 6.15: Delete `sim/views.py`**

Run: `git rm sim/views.py`

- [ ] **Step 6.16: Manual smoke test**

Run: `streamlit run simulator.py` — click through a full session end-to-end. Check masthead renders, sidebar works, console + checklist both render, status bar updates, survey + summary work.

- [ ] **Step 6.17: Run all tests**

Run: `pytest -v`
Expected: all pass.

- [ ] **Step 6.18: Commit**

```bash
git add -A
git commit -m "refactor: split views.py into sim/ui/screens/; relocate styles and widgets"
```

---

## Task 7: Finalize state bridge

**Goal:** Replace `sim/state.py`'s flat dict with phase-scoped dataclasses. Add `serialize_events` as a pure helper. Remove the compat shims from `sim/scenarios.py` and `sim/trial.py`.

**Files:**
- Rewrite: `sim/state.py`
- Modify: `sim/trial.py` (use new state accessors; drop compat helpers)
- Modify: UI screens (read from new state accessors)
- Delete: `sim/scenarios.py`

- [ ] **Step 7.1: Rewrite `sim/state.py`**

```python
"""Phase-scoped state bridge between Streamlit session_state and domain."""
from dataclasses import asdict, dataclass, field
from typing import List, Literal, Optional, Tuple

import streamlit as st


@dataclass
class IdentityState:
    participant_id: str = ""
    experience: str = "None"
    condition_key: Optional[str] = None
    assignment_mode: Literal["auto", "manual"] = "auto"
    session_id: Optional[str] = None
    session_started: bool = False


@dataclass
class SessionState:
    trial_order: Tuple[int, ...] = ()
    trial_index: int = 0
    did_familiarization: bool = False
    in_familiarization: bool = False
    all_summaries: List[dict] = field(default_factory=list)
    session_finished: bool = False
    session_survey_submitted: bool = False
    data_sink: Optional[str] = None


_IDENTITY_KEYS = {f.name for f in IdentityState.__dataclass_fields__.values()}
_SESSION_KEYS = {f.name for f in SessionState.__dataclass_fields__.values()}


def init_state() -> None:
    """Install default values for every session/identity field if missing.
    Widget-state keys (tlx_*, branch_decision_*, checklist_pick_*) are managed
    by Streamlit itself and not touched here."""
    defaults = {**asdict(IdentityState()), **asdict(SessionState())}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def identity() -> IdentityState:
    return IdentityState(**{k: st.session_state[k] for k in _IDENTITY_KEYS})


def session() -> SessionState:
    return SessionState(**{k: st.session_state[k] for k in _SESSION_KEYS})


def reset_trial_state() -> None:
    """Clear engine + dynamic widget keys. Called at trial transitions."""
    st.session_state["trial_engine"] = None
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and (key.startswith("branch_decision_") or key.startswith("checklist_pick_")):
            del st.session_state[key]
```

- [ ] **Step 7.2: Update `sim/trial.py` — drop the scenario-dict shim and the mirror**

Three changes:

1. Rewrite `current_scenario()` to return the `Scenario` dataclass directly:

```python
def current_scenario():
    e = _engine()
    return e.scenario if e else None
```

2. Delete `_scenario_to_dict` helper at the bottom of the file (it imported from the soon-to-be-deleted `sim/scenarios.py`).

3. Delete `_mirror_to_session_state` function and every call site (inside `_set_engine`, `execute_action`, `submit_branching_decision`, `select_linear_checklist`, `maybe_auto_transition`). These lines become redundant once screens read from engine accessors instead of legacy flat keys.

4. Add accessor functions that screens will use (replacing direct `st.session_state.*` reads):

```python
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


def in_familiarization() -> bool:
    return bool(st.session_state.get("in_familiarization", False))
```

5. Change `picked_linear_checklist()` to return the `LinearChecklist` dataclass directly (instead of the Task-4 dict shape):

```python
def picked_linear_checklist():
    e = _engine()
    return e.picked_linear_checklist() if e else None
```

- [ ] **Step 7.3: Update UI screens — dataclass field access + engine accessors**

Screens built in Task 6 used dict access on scenarios and direct `st.session_state.*` reads. Now that `current_scenario()` returns a `Scenario` dataclass and the legacy mirror is gone, each screen needs updates:

**`sim/ui/screens/status_bar.py`:**

- Replace `scenario["fault"]` with `scenario.fault`
- Replace `st.session_state.mode` with `current_mode()`; add `from sim.trial import current_mode`
- Replace `st.session_state.in_familiarization` with `in_familiarization()`; add `from sim.trial import in_familiarization` (shadowing: either rename the import or check directly via `from sim.state import session; session().in_familiarization`)

**`sim/ui/screens/console.py`:**

- Replace `scenario["trigger_cues"]` with `scenario.trigger_cues`
- Inside `render_trigger_cues`, cue dicts become `TriggerCue` — update widgets.py's `render_trigger_cues` to accept the dataclass: change `c["label"]`/`c["value"]` to `c.label`/`c.value`.
- Replace `st.session_state.in_familiarization` with a bridge call as above.

**`sim/ui/screens/linear.py`:**

- Replace `scenario["linear_checklist"]["steps"]` with `scenario.linear_checklist.steps`
- Replace `st.session_state.selected_checklist_id` with `selected_checklist_id()`; import from `sim.trial`
- Replace `st.session_state.completed_actions` with `completed_actions()`; import from `sim.trial`
- Replace `st.session_state.in_familiarization` as above
- `_render_linear_progress` needs to compare `picked` to current scenario. Since `current_scenario()` now returns a `Scenario` and `picked_linear_checklist()` returns a `LinearChecklist` (from Task 7.4 below), change comparison to use stored id — add a `from sim.trial import selected_checklist_id, current_scenario` and compare `selected_checklist_id() == current_scenario().id`.
- Access on `picked`: `picked.steps` and `picked.title`.
- `cand.steps`/`cand.trigger_cues` already use dataclass form (Task 6 step 6.9).

**`sim/ui/screens/branching.py`:**

- Replace `scenario["branching_checklist"]` with `scenario.branching_checklist`; replace `bc["title"]`, `bc["steps"]` with attribute access.
- Branching step dicts become dataclasses — add `from sim.domain.models import ActionStep, DecisionStep, TerminalStep`
- Replace `step.get("type") == "terminal"` with `isinstance(step, TerminalStep)`; similar for action/decision.
- Replace `step["id"]`, `step["text"]`, `step["prompt"]`, `step["options"]`, `step.get("note", "")` with attribute access (`step.id`, `step.text`, `step.prompt`, `step.options`, `step.note`). Note: dataclasses with defaults like `note: str = ""` don't support `.get()`.
- Inside the decision loop, `o["label"]` / `o["note"]` become `o.label` / `o.note`.
- Replace `st.session_state.branch_step_id` with `branch_step_id()` and `st.session_state.branch_path` with `branch_path()`; import from `sim.trial`.
- Replace `st.session_state.in_familiarization` as above.

**`sim/ui/screens/summary.py`:**

- Session summary reads `st.session_state.all_summaries` which contains plain dicts (from `dataclasses.asdict` in `_finalize_trial`). Keep dict access — no changes.

**`sim/ui/screens/survey.py`:**

- No changes — doesn't read flat state keys or scenario.

**`sim/ui/screens/familiarization_done.py`:**

- No changes.

**`sim/ui/widgets.py`:**

- `render_trigger_cues(cues)` currently expects a list of dicts with `label`/`value`. Update to accept an iterable of `TriggerCue`:

```python
def render_trigger_cues(cues) -> None:
    if not cues:
        return
    inner = "".join(
        f'<div class="hf-cue">'
        f'<div class="hf-cue-label">{esc(c.label)}</div>'
        f'<div class="hf-cue-value">{esc(c.value)}</div>'
        f'</div>'
        for c in cues
    )
    st.markdown(f'<div class="hf-cues">{inner}</div>', unsafe_allow_html=True)
```

- [ ] **Step 7.4: Delete `sim/scenarios.py`**

```bash
git rm sim/scenarios.py
```

Verify no imports remain: `grep -R "from sim.scenarios" sim/` → no output.

- [ ] **Step 7.5: Update `simulator.py`'s `_auto_refresh_if_running`**

Today it reads `st.session_state.trial_started`, `st.session_state.finished`, `st.session_state.in_familiarization`. After cleanup those first two flags don't exist. Rewrite:

```python
from sim.trial import trial_started, finished
from sim.state import session


def _auto_refresh_if_running() -> None:
    if st_autorefresh is None:
        return
    if not trial_started():
        return
    if finished():
        return
    if session().in_familiarization:
        return
    st_autorefresh(interval=1000, key="trial_timer_autorefresh")
```

Also fix the main() path in `simulator.py` where it checks `st.session_state.finished and not st.session_state.session_finished` — replace with `finished() and not session().session_finished`, etc.

- [ ] **Step 7.6: Manual smoke test**

Run: `streamlit run simulator.py`
Click through: intro → sidebar → practice trial → real trial (linear OR branching) → survey → summary.

- [ ] **Step 7.7: Run all tests**

Run: `pytest -v`
Expected: all pass.

- [ ] **Step 7.8: Commit**

```bash
git add -A
git commit -m "refactor: finalize state bridge; drop sim/scenarios.py shim; read dataclasses in UI"
```

---

## Task 8: Add smoke test

**Goal:** Catch broken imports and engine drift with a pytest file that (a) imports every `sim/` module, (b) runs every real scenario through the engine to completion.

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 8.1: Create `tests/test_smoke.py`**

```python
"""Smoke test — catches import errors, missing __init__.py, and engine drift.
Does NOT exercise Streamlit UI."""
import importlib
import pkgutil

import sim


def test_every_module_under_sim_imports():
    broken = []
    for modinfo in pkgutil.walk_packages(sim.__path__, prefix="sim."):
        # Skip the UI layer — it imports streamlit directly, which does import
        # cleanly but exercises too much framework code for a smoke test.
        # Also skip sim.state and sim.trial for the same reason.
        if modinfo.name.startswith("sim.ui"):
            continue
        if modinfo.name in {"sim.state", "sim.trial"}:
            continue
        try:
            importlib.import_module(modinfo.name)
        except Exception as exc:
            broken.append((modinfo.name, repr(exc)))
    assert broken == [], f"Modules failed to import: {broken}"


def _run_to_completion(scenario, condition):
    from sim.domain.engine import TrialEngine
    from sim.domain.models import (
        ActionStep, DecisionStep, TerminalStep, TrialContext,
    )
    ctx = TrialContext(session_id="s", participant_id="p", experience="None", trial_number=1)
    engine = TrialEngine(scenario, condition, ctx, start_time=0.0)
    now = 1.0
    if scenario.is_familiarization:
        engine.execute_action("ACK PRACTICE ALERT", now=now)
        return engine

    if condition.checklist_type == "linear":
        engine.select_linear_checklist(scenario.id, now=now)
        # Drive through the linear checklist in order
        for step in scenario.linear_checklist.steps:
            # Fake the expected mode if the action has one
            expected = scenario.action_expected_modes.get(step)
            if expected is not None and engine.mode != expected:
                engine.mode = expected  # simulate the spacecraft mode being right
            now += 1.0
            engine.execute_action(step, now=now)
            if engine.is_finished():
                break
        return engine

    # branching — walk correct decisions
    while not engine.is_finished() and engine.branch_step_id is not None:
        step = engine.current_branching_step()
        if isinstance(step, ActionStep):
            expected = scenario.action_expected_modes.get(step.text)
            if expected is not None and engine.mode != expected:
                engine.mode = expected
            now += 1.0
            engine.execute_action(step.text, now=now)
        elif isinstance(step, DecisionStep):
            correct_idx = next(i for i, o in enumerate(step.options) if o.correct)
            now += 1.0
            engine.submit_decision(correct_idx, now=now)
        elif isinstance(step, TerminalStep):
            break
    return engine


def test_every_real_scenario_completes_linearly():
    from sim.domain.conditions import CONDITIONS
    from sim.domain.scenarios.registry import get_all
    cond = CONDITIONS["linear_low"]
    for scenario in get_all():
        engine = _run_to_completion(scenario, cond)
        assert engine.is_finished(), f"{scenario.title} did not finish in linear_low"
        assert engine.end_reason() == "completed"


def test_every_real_scenario_completes_branching():
    from sim.domain.conditions import CONDITIONS
    from sim.domain.scenarios.registry import get_all
    cond = CONDITIONS["branching_low"]
    for scenario in get_all():
        engine = _run_to_completion(scenario, cond)
        assert engine.is_finished(), f"{scenario.title} did not finish in branching_low"
        assert engine.end_reason() == "completed"


def test_familiarization_completes():
    from sim.domain.conditions import CONDITIONS
    from sim.domain.scenarios.registry import get_familiarization
    engine = _run_to_completion(get_familiarization(), CONDITIONS["linear_low"])
    assert engine.is_finished()
    assert engine.end_reason() == "completed"
```

- [ ] **Step 8.2: Run**

Run: `pytest tests/test_smoke.py -v`
Expected: 4 tests PASS.

- [ ] **Step 8.3: Run all tests**

Run: `pytest -v`
Expected: everything passes.

- [ ] **Step 8.4: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add smoke test covering imports and engine playthroughs"
```

---

## Task 9: Cleanup

**Goal:** Sweep residual dead code, verify the app still works end-to-end, write a summary commit for the PR body.

- [ ] **Step 9.1: Search for dead imports**

Run: `python -c "import compileall; compileall.compile_dir('sim', quiet=1)"`
Expected: exits 0 (no syntax errors).

Run: `grep -R "from sim.views" sim/ simulator.py` and `grep -R "from sim.components" sim/ simulator.py` and `grep -R "from sim.config" sim/ simulator.py`
Expected: no matches.

- [ ] **Step 9.2: Check `sim/styles.py` is gone**

Run: `ls sim/styles.py 2>&1`
Expected: `No such file or directory`.

- [ ] **Step 9.3: Remove any remaining `ACTION_HELP`/`CONDITIONS` references from dead paths**

Run: `grep -R "ACTION_HELP\|CONDITIONS\|BACKGROUND_OPTIONS" sim/ | grep -v "sim/domain"`
Expected: only references in UI screens that `import` from `sim.domain.*` — any other reference is dead and must be removed.

- [ ] **Step 9.4: Full test run**

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 9.5: Full manual run**

Run: `streamlit run simulator.py`

Walk through: session start → familiarization → trial 1 (linear if condition is linear) → trial 2 → trial 3 → survey → summary. For at least one session: complete one linear trial successfully and one branching trial successfully. Verify timer counts down, mode updates, action buttons stay enabled, logs persist.

If Irfan is skipping manual click-through, note that explicitly in the PR body so Varsha can do it.

- [ ] **Step 9.6: Final commit (if any cleanup was needed)**

```bash
git add -A
git commit -m "refactor: final cleanup sweep"
```

- [ ] **Step 9.7: Push**

```bash
git push -u origin refactor/cleanup-2026-04
```

Expected: branch now visible on GitHub. PR can be opened from the GitHub UI against `main`.

---

## Self-review checklist (run this as the last thing)

- [ ] Every task produces a commit
- [ ] Every spec section has a task (domain/models, scenarios, conditions/survey/action_help, engine, scoring, UI screens, IO split, state bridge, tests, smoke)
- [ ] Every task ends with a passing `pytest` run OR a successful manual click-through
- [ ] `sim/config.py`, `sim/views.py`, `sim/scenarios.py`, `sim/sinks.py`, `sim/components.py`, `sim/styles.py` all deleted by end of plan
- [ ] No test in `tests/` imports `streamlit`
- [ ] Output column sets (`assignments`, `events`, `summaries`) preserved (frozen-schema tests in `test_engine.py`)
