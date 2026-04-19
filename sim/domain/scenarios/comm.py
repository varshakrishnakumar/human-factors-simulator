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
