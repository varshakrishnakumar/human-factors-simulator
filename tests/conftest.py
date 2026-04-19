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
