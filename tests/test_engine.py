from sim.domain.engine import TrialEngine


def test_familiarization_completes_on_practice_action(ctx, condition_linear, familiarization_scenario):
    engine = TrialEngine(familiarization_scenario, condition_linear, ctx, start_time=0.0)
    engine.execute_action("ACK PRACTICE ALERT", now=1.0)
    assert engine.is_finished()
    assert engine.end_reason() == "completed"


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


def test_linear_order_error_increments(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    # Skip "A", try "B" first
    engine.execute_action("B", now=1.0)
    assert engine.order_errors == 1
    # "B" still records (no enforcement)
    assert "B" in engine.completed_actions


def test_linear_wrong_checklist_sets_error_flag(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(scenario_id=999, now=0.1)
    assert engine.checklist_selection_error is True
    assert engine.selected_checklist_id == 999
    assert not engine.is_finished()


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


def test_branching_wrong_decision_hits_terminal(ctx, condition_branching, branching_scenario):
    engine = TrialEngine(branching_scenario, condition_branching, ctx, start_time=0.0)
    engine.execute_action("ACK", now=1.0)
    engine.submit_decision(1, now=2.0)  # "no" → next=99 (terminal)
    # After submit, classify_end sees current step as TerminalStep → wrong_branch
    assert engine.is_finished()
    assert engine.end_reason() == "wrong_branch"
    assert engine.branch_decision_errors == 1


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


def test_branching_procedure_end_when_mode_wrong_at_finish(ctx, condition_branching):
    """Branching that reaches next=None but ends in a mode other than
    scenario.correct_mode classifies as procedure_end (not completed)."""
    from sim.domain.models import (
        ActionStep, AutoTransition, BranchingChecklist, LinearChecklist,
        Scenario, TriggerCue,
    )
    scenario = Scenario(
        id=11, title="Bad end", fault="F", initial_mode="AUTO",
        # Force mode into HOLD early so we never hit correct_mode="AUTO".
        auto_transition=AutoTransition(time=1, new_mode="HOLD"),
        correct_mode="AUTO",
        trigger_cues=(TriggerCue("a", "b"),),
        linear_checklist=LinearChecklist(title="L", steps=()),
        branching_checklist=BranchingChecklist(title="B", steps=(
            ActionStep(id=1, text="A1", next=2),
            ActionStep(id=2, text="A2", next=None),
        )),
        action_expected_modes={},
    )
    engine = TrialEngine(scenario, condition_branching, ctx, start_time=0.0)
    # Tick past auto_transition time so mode becomes HOLD before finishing.
    engine.tick(now=2.0)
    assert engine.mode == "HOLD"
    engine.execute_action("A1", now=3.0)
    engine.execute_action("A2", now=4.0)
    assert engine.is_finished()
    assert engine.end_reason() == "procedure_end"


def test_timeout(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.tick(now=condition_linear.time_limit + 1)
    assert engine.is_finished()
    assert engine.end_reason() == "timeout"


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
