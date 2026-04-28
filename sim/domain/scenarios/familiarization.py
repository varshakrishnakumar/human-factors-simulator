"""Sandbox/familiarization scenario domain constant."""
from types import MappingProxyType

from sim.domain.models import (
    ActionStep, AutoTransition, BranchingChecklist,
    LinearChecklist, Scenario, TriggerCue,
)

SCENARIO = Scenario(
    id=0,
    title="Sandbox Familiarization",
    fault="Sandbox practice alert (not a real fault)",
    initial_mode="HOLD",
    auto_transition=AutoTransition(time=99999, new_mode="HOLD"),
    correct_mode="AUTO",
    trigger_cues=(
        TriggerCue(label="MODE", value="HOLD"),
        TriggerCue(label="SANDBOX ALERT", value="ACTIVE"),
        TriggerCue(label="PRACTICE PANEL", value="CLOSED"),
    ),
    linear_checklist=LinearChecklist(
        title="Sandbox Walkthrough",
        steps=(
            "ACK PRACTICE ALERT",
            "OPEN PRACTICE STATUS PANEL",
            "SELECT AUTO MODE",
            "REPORT PRACTICE COMPLETE",
        ),
    ),
    branching_checklist=BranchingChecklist(
        title="Sandbox Walkthrough",
        steps=(
            ActionStep(id=1, text="ACK PRACTICE ALERT", next=2),
            ActionStep(id=2, text="OPEN PRACTICE STATUS PANEL", next=3),
            ActionStep(id=3, text="SELECT AUTO MODE", next=4),
            ActionStep(id=4, text="REPORT PRACTICE COMPLETE", next=None),
        ),
    ),
    action_expected_modes=MappingProxyType({
        "ACK PRACTICE ALERT": "HOLD",
        "OPEN PRACTICE STATUS PANEL": "HOLD",
        "SELECT AUTO MODE": "HOLD",
        "REPORT PRACTICE COMPLETE": "AUTO",
    }),
    action_cue_effects=MappingProxyType({
        "ACK PRACTICE ALERT": (("SANDBOX ALERT", "ACKNOWLEDGED"),),
        "OPEN PRACTICE STATUS PANEL": (("PRACTICE PANEL", "OPEN"),),
        "SELECT AUTO MODE": (("MODE", "AUTO"),),
        "REPORT PRACTICE COMPLETE": (("SANDBOX ALERT", "OK"),),
    }),
    is_familiarization=True,
)
