from types import MappingProxyType

from sim.domain.engine import TrialEngine


def test_familiarization_completes_on_practice_action(ctx, condition_linear, familiarization_scenario):
    engine = TrialEngine(familiarization_scenario, condition_linear, ctx, start_time=0.0)
    engine.execute_action("ACK PRACTICE ALERT", now=1.0)
    assert engine.is_finished()
    assert engine.end_reason() == "completed"


def test_familiarization_requires_all_sandbox_steps(ctx, condition_linear):
    from sim.domain.scenarios.registry import get_familiarization

    scenario = get_familiarization()
    engine = TrialEngine(scenario, condition_linear, ctx, start_time=0.0)
    for i, step in enumerate(scenario.linear_checklist.steps[:-1], start=1):
        engine.execute_action(step, now=float(i))
        assert not engine.is_finished()

    engine.execute_action(scenario.linear_checklist.steps[-1], now=10.0)
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


def test_linear_reselect_clears_pick_and_actions_but_not_error(ctx, condition_linear, linear_scenario):
    """After a wrong pick, reset returns to the picker and clears completed_actions
    so the next checklist starts fresh, but the error flag stays sticky."""
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(scenario_id=999, now=0.1)
    engine.execute_action("A", now=0.5)
    assert engine.completed_actions == ["A"]
    engine.reset_checklist_selection(now=1.0)
    assert engine.selected_checklist_id is None
    assert engine.completed_actions == []
    assert engine.checklist_selection_error is True  # sticky
    # Re-pick correctly: error flag must remain True (we still want to record
    # that the subject originally misdiagnosed).
    engine.select_linear_checklist(linear_scenario.id, now=1.5)
    assert engine.checklist_selection_error is True


def test_linear_reset_no_op_when_nothing_picked(ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.reset_checklist_selection(now=0.1)
    assert engine.selected_checklist_id is None
    assert engine.checklist_selection_error is False


def test_action_cue_effect_updates_live_panel(ctx, condition_linear, linear_scenario):
    """Performing an action with a cue effect mutates the live cue panel.
    Subjects need this feedback to make grounded decisions at decision steps."""
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    # Initial cues are the scenario defaults.
    cues = {c.label: c.value for c in engine.current_cues()}
    assert cues == {"MODE": "AUTO", "WIDGET": "FAULT"}
    # Action B has a cue effect: WIDGET -> OK.
    engine.mode = "HOLD"  # avoid the wrong-mode side path
    engine.execute_action("B", now=1.0)
    cues = {c.label: c.value for c in engine.current_cues()}
    assert cues == {"MODE": "AUTO", "WIDGET": "OK"}


def test_end_trial_records_self_terminated(ctx, condition_linear, linear_scenario):
    """end_trial finishes the trial with end_reason='self_terminated' so the
    summary distinguishes 'subject said done' from 'objectively complete'."""
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("A", now=1.0)
    engine.end_trial(now=2.0)
    assert engine.is_finished()
    assert engine.end_reason() == "self_terminated"
    result = engine.result()
    assert result.completed is False
    assert result.timed_out is False
    assert result.end_reason == "self_terminated"


def test_finish_event_contains_summary_counters(ctx, condition_linear, linear_scenario):
    """The event sheet should be enough to reconstruct a trial summary if the
    summaries sheet has a transient write problem."""
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("B", now=1.0)
    engine.end_trial(now=2.0)

    finish_event = engine.event_log()[-1]
    assert finish_event.action == "TRIAL FINISH"
    assert finish_event.extra["end_reason"] == "self_terminated"
    assert finish_event.extra["completed"] is False
    assert finish_event.extra["timed_out"] is False
    assert finish_event.extra["wrong_mode_actions"] == 1
    assert finish_event.extra["order_errors"] == 1
    assert finish_event.extra["branch_decision_errors"] == 0
    assert finish_event.extra["checklist_selection_error"] == 0
    assert finish_event.extra["selected_checklist_id"] == linear_scenario.id


def test_auto_transition_does_not_refire_after_select_auto_mode(ctx, condition_branching):
    """Regression for the 'two phantom wrong_mode_actions per trial' bug:
    once the auto-transition has fired (mode AUTO -> SAFE/HOLD), tick() must
    NOT fire it again later — even when the subject legitimately changes mode
    back to AUTO via SELECT AUTO MODE near the end of the procedure. Without
    the latch, every subsequent AUTO-expecting action would falsely be flagged
    wrong_mode because the engine kept yanking mode back to the scenario's
    auto_transition target on each rerun."""
    from sim.domain.models import (
        ActionStep, AutoTransition, BranchingChecklist, LinearChecklist,
        Scenario, TriggerCue,
    )
    scenario = Scenario(
        id=20, title="Tick Latch", fault="F", initial_mode="AUTO",
        auto_transition=AutoTransition(time=5, new_mode="SAFE"),
        correct_mode="AUTO",
        trigger_cues=(TriggerCue("a", "b"),),
        linear_checklist=LinearChecklist(title="L", steps=()),
        branching_checklist=BranchingChecklist(title="B", steps=(
            ActionStep(id=1, text="SELECT AUTO MODE", next=2),
            ActionStep(id=2, text="VERIFY ATTITUDE STABLE", next=None),
        )),
        action_expected_modes=MappingProxyType({
            "SELECT AUTO MODE": "SAFE",
            "VERIFY ATTITUDE STABLE": "AUTO",
        }),
    )
    engine = TrialEngine(scenario, condition_branching, ctx, start_time=0.0)
    engine.tick(now=6.0)
    assert engine.mode == "SAFE"  # auto-transition fired once
    engine.execute_action("SELECT AUTO MODE", now=7.0)
    assert engine.mode == "AUTO"  # subject moved spacecraft back to AUTO
    engine.tick(now=8.0)
    assert engine.mode == "AUTO"  # tick must NOT yank mode back to SAFE
    engine.execute_action("VERIFY ATTITUDE STABLE", now=9.0)
    assert engine.wrong_mode_actions == 0  # no phantom wrong-mode flags
    assert engine.is_finished()
    assert engine.end_reason() == "completed"


def test_end_trial_after_finish_is_noop(ctx, condition_linear, linear_scenario):
    """A second end_trial call on an already-finished engine must NOT
    overwrite the original end reason."""
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("A", now=1.0)
    engine.execute_action("B", now=2.0)  # wrong-mode is fine; mode stays AUTO=correct_mode
    engine.execute_action("C", now=3.0)
    assert engine.end_reason() == "completed"
    engine.end_trial(now=4.0)
    assert engine.end_reason() == "completed"  # unchanged


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


def test_branching_action_click_at_decision_step_is_order_error(ctx, condition_branching, branching_scenario):
    """Pressing a console action while a DecisionStep is pending must NOT
    silently mutate completed_actions or mode. It records an ORDER ERROR and
    short-circuits — the subject has to use the right-panel radio to advance.
    Without this, console clicks at a decision step looked like 'nothing
    happened' to the subject while quietly polluting the trial data."""
    engine = TrialEngine(branching_scenario, condition_branching, ctx, start_time=0.0)
    engine.execute_action("ACK", now=1.0)  # ActionStep id=1, advances to decision id=2
    assert engine.branch_step_id == 2  # at decision now
    # Click an action button at the decision — must NOT advance, NOT add to
    # completed_actions, NOT change mode; must record an order error.
    prev_completed = list(engine.completed_actions)
    prev_mode = engine.mode
    engine.execute_action("SELECT AUTO MODE", now=2.0)
    assert engine.order_errors == 1
    assert engine.completed_actions == prev_completed
    assert engine.mode == prev_mode  # SELECT AUTO MODE did NOT flip mode behind the curtain
    assert engine.branch_step_id == 2  # still at decision
    # Decision still works afterward.
    engine.submit_decision(0, now=3.0)
    assert engine.branch_step_id == 3  # advanced past the decision


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
        action_expected_modes=MappingProxyType({}),
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
        action_expected_modes=MappingProxyType({}),
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
        action_expected_modes=MappingProxyType({}),
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
