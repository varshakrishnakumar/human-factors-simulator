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
