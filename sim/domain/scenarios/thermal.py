"""Thermal loop recovery scenario domain constant."""
from types import MappingProxyType

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
    action_expected_modes=MappingProxyType({
        "CYCLE RADIATOR BYPASS VALVE": "SAFE",
        "ENGAGE BACKUP HEATER": "SAFE",
        "CONFIRM THERMAL LOOP STABLE": "SAFE",
        "SELECT AUTO MODE": "SAFE",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    }),
)
