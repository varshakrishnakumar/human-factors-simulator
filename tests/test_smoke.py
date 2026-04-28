"""Smoke test — catches import errors, missing __init__.py, and engine drift.
Does NOT exercise Streamlit UI."""
import importlib
import pkgutil

import sim


def test_every_module_under_sim_imports():
    broken = []
    for modinfo in pkgutil.walk_packages(sim.__path__, prefix="sim."):
        # Skip the UI layer — it imports streamlit directly, which does import
        # cleanly but exercises too much framework code for a smoke test.
        # Also skip sim.state and sim.trial for the same reason.
        if modinfo.name.startswith("sim.ui"):
            continue
        if modinfo.name in {"sim.state", "sim.trial"}:
            continue
        try:
            importlib.import_module(modinfo.name)
        except Exception as exc:
            broken.append((modinfo.name, repr(exc)))
    assert broken == [], f"Modules failed to import: {broken}"


def _run_to_completion(scenario, condition):
    from sim.domain.engine import TrialEngine
    from sim.domain.models import (
        ActionStep, DecisionStep, TerminalStep, TrialContext,
    )
    ctx = TrialContext(session_id="s", participant_id="p", experience="None", trial_number=1)
    engine = TrialEngine(scenario, condition, ctx, start_time=0.0)
    now = 1.0
    if scenario.is_familiarization:
        for step in scenario.linear_checklist.steps:
            now += 1.0
            engine.execute_action(step, now=now)
        return engine

    if condition.checklist_type == "linear":
        engine.select_linear_checklist(scenario.id, now=now)
        # Drive through the linear checklist in order
        for step in scenario.linear_checklist.steps:
            # Fake the expected mode if the action has one
            expected = scenario.action_expected_modes.get(step)
            if expected is not None and engine.mode != expected:
                engine.mode = expected  # simulate the spacecraft mode being right
            now += 1.0
            engine.execute_action(step, now=now)
            if engine.is_finished():
                break
        return engine

    # branching — walk correct decisions
    while not engine.is_finished() and engine.branch_step_id is not None:
        step = engine.current_branching_step()
        if isinstance(step, ActionStep):
            expected = scenario.action_expected_modes.get(step.text)
            if expected is not None and engine.mode != expected:
                engine.mode = expected
            now += 1.0
            engine.execute_action(step.text, now=now)
        elif isinstance(step, DecisionStep):
            correct_idx = next(i for i, o in enumerate(step.options) if o.correct)
            now += 1.0
            engine.submit_decision(correct_idx, now=now)
        elif isinstance(step, TerminalStep):
            break
    return engine


def test_every_real_scenario_completes_linearly():
    from sim.domain.conditions import CONDITIONS
    from sim.domain.scenarios.registry import get_all
    cond = CONDITIONS["linear_low"]
    for scenario in get_all():
        engine = _run_to_completion(scenario, cond)
        assert engine.is_finished(), f"{scenario.title} did not finish in linear_low"
        assert engine.end_reason() == "completed"


def test_every_real_scenario_completes_branching():
    from sim.domain.conditions import CONDITIONS
    from sim.domain.scenarios.registry import get_all
    cond = CONDITIONS["branching_low"]
    for scenario in get_all():
        engine = _run_to_completion(scenario, cond)
        assert engine.is_finished(), f"{scenario.title} did not finish in branching_low"
        assert engine.end_reason() == "completed"


def test_familiarization_completes():
    from sim.domain.conditions import CONDITIONS
    from sim.domain.scenarios.registry import get_familiarization
    engine = _run_to_completion(get_familiarization(), CONDITIONS["linear_low"])
    assert engine.is_finished()
    assert engine.end_reason() == "completed"
