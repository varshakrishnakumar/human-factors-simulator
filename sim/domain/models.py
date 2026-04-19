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
