"""Navigation fault recovery scenario domain constant."""
from types import MappingProxyType

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
    action_expected_modes=MappingProxyType({
        "RESET NAVIGATION FILTER": "HOLD",
        "REINITIALIZE STAR TRACKER": "HOLD",
        "CONFIRM NAVIGATION DATA RESTORED": "HOLD",
        "SELECT AUTO MODE": "HOLD",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    }),
    action_cue_effects=MappingProxyType({
        "RESET NAVIGATION FILTER": (("NAV DATA", "RESETTING"),),
        "REINITIALIZE STAR TRACKER": (
            ("STAR TRACKER", "NOMINAL"),
            ("NAV DATA", "VALID"),
        ),
        "CONFIRM NAVIGATION DATA RESTORED": (("NAV DATA", "VALID"),),
    }),
)
