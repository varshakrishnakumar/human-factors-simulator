"""All typed shapes shared by the domain layer. No Streamlit import here —
these classes need to be importable by tests and by the pure engine without
dragging in any UI dependencies.

I made scenario-definition types (Scenario, its component types, Condition,
TrialContext, SurveyQuestion) `frozen=True` so they're effectively immutable
constants after construction — no accidental mutation mid-trial. The mutable
types (TrialEvent, TrialResult) are plain dataclasses because they are built up
during a trial and then persisted; MappingProxyType on
Scenario.action_expected_modes gives the same immutability guarantee for that
dict without needing a custom __setattr__."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Literal, Optional, Tuple, Union


@dataclass(frozen=True)
class TriggerCue:
    """One indicator shown on the console (label + value pair) that the subject
    uses to identify which fault is active."""
    label: str
    value: str


@dataclass(frozen=True)
class LinearChecklist:
    """A named, ordered list of action strings. In linear conditions the
    subject picks one of three of these before executing steps."""
    title: str
    steps: Tuple[str, ...]


@dataclass(frozen=True)
class ActionStep:
    """A branching-checklist step that maps to a console button. `next` is the
    id of the step that follows if the action is completed."""
    id: int
    text: str
    next: Optional[int]
    note: str = ""
    type: Literal["action"] = "action"


@dataclass(frozen=True)
class DecisionOption:
    """One branch of a DecisionStep. `correct` is the expected/optimal choice;
    picking an incorrect option increments branch_decision_errors."""
    label: str
    next: Optional[int]
    correct: bool
    note: str = ""


@dataclass(frozen=True)
class DecisionStep:
    """A branching-checklist step that asks the subject to pick a path. The
    engine records the choice and routes to the option's `next` step id."""
    id: int
    prompt: str
    options: Tuple[DecisionOption, ...]
    type: Literal["decision"] = "decision"


@dataclass(frozen=True)
class TerminalStep:
    """A dead-end step in the branching flow — reaching it means the subject
    took a wrong branch. The engine ends the trial with end_reason='wrong_branch'."""
    id: int
    text: str
    note: str = ""
    type: Literal["terminal"] = "terminal"


BranchingStep = Union[ActionStep, DecisionStep, TerminalStep]


@dataclass(frozen=True)
class BranchingChecklist:
    """The full branching procedure for a scenario: a heterogeneous tuple of
    ActionStep, DecisionStep, and TerminalStep nodes forming a decision tree."""
    title: str
    steps: Tuple[BranchingStep, ...]


@dataclass(frozen=True)
class AutoTransition:
    """Describes the automatic mode change that happens when the subject waits
    too long without acting — `time` seconds elapsed causes a switch to
    `new_mode`. Every scenario has exactly one of these (even if it's set far
    in the future for scenarios that don't use it)."""
    time: float
    new_mode: str


@dataclass(frozen=True)
class Scenario:
    """All static data for one fault scenario. Frozen so the registry can hand
    out the same instance to every trial without fear of mutation. If you're
    adding a new scenario, see domain/scenarios/registry.py — you only need to
    define a SCENARIO constant and add one line there.

    `action_cue_effects` is the recovery-feedback table: for each action label,
    one or more (cue_label, new_value) pairs that get applied to the live cue
    panel when the action is performed. Without this the console shows the same
    fault state forever and decision steps like 'Is the ground link active and
    stable?' have no observable evidence behind them. Defaults to empty so
    scenarios that opt out of dynamic cues stay frozen-state."""
    id: int
    title: str
    fault: str
    initial_mode: str
    auto_transition: AutoTransition
    correct_mode: str
    trigger_cues: Tuple[TriggerCue, ...]
    linear_checklist: LinearChecklist
    branching_checklist: BranchingChecklist
    action_expected_modes: "MappingProxyType[str, str]"
    action_cue_effects: "MappingProxyType[str, Tuple[Tuple[str, str], ...]]" = field(
        default_factory=lambda: MappingProxyType({}),
    )
    is_familiarization: bool = False


@dataclass(frozen=True)
class LinearCandidate:
    """A lightweight projection of a Scenario used by the linear checklist
    picker — only the fields the subject needs to identify which checklist
    matches the console indications. The full Scenario is not exposed to avoid
    leaking the correct_mode answer."""
    scenario_id: int
    title: str
    steps: Tuple[str, ...]
    trigger_cues: Tuple[TriggerCue, ...]


@dataclass(frozen=True)
class Condition:
    """One of the four experimental conditions (2 checklist types × 2 time
    pressures). Frozen so the CONDITIONS dict in conditions.py is a true
    immutable constant."""
    key: str
    checklist_type: Literal["linear", "branching"]
    time_limit: int
    label: str


@dataclass(frozen=True)
class TrialContext:
    """The participant/session metadata the engine needs to produce output rows.
    Separated from Condition so the engine signature stays explicit about what
    is participant data versus experimental manipulation."""
    session_id: str
    participant_id: str
    experience: str
    trial_number: int


@dataclass(frozen=True)
class SurveyQuestion:
    """One NASA-TLX item. The render loop in ui/screens/survey.py reads these
    directly, so wording/anchor changes are made here without touching UI code."""
    key: str
    label: str
    question: str
    low_anchor: str
    high_anchor: str
    min: int = 1
    max: int = 7
    default: int = 4


@dataclass
class TrialEvent:
    """A single timestamped event emitted by the engine during a trial.
    Mutable because the engine appends to a list as the trial runs. The extra
    dict carries event-specific fields (e.g. wrong_mode, choice, selected_id)
    that vary by action type."""
    timestamp_s: float
    mode: Optional[str]
    action: str
    extra: Dict[str, Any] = field(default_factory=dict)


EndReason = Literal["completed", "timeout", "wrong_branch", "procedure_end", "self_terminated"]


@dataclass
class TrialResult:
    """Flat summary row produced by the engine once a trial ends. One row per
    trial, persisted to the 'summaries' sheet/CSV. NASA-TLX workload data is
    written once per session and joined by session_id during analysis."""
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
