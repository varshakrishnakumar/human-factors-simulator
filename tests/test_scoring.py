from sim.domain.models import TrialResult
from sim.domain.scoring import aggregate_errors


def _make_result(**overrides):
    base = dict(
        session_id="s", participant_id="p", experience="None",
        condition="c", checklist_type="linear", time_limit=60,
        trial_number=1, scenario_id=1, scenario_title="t", fault="f",
        completion_time_s=1.0, end_reason="completed", completed=True,
        timed_out=False, wrong_mode_actions=0, order_errors=0,
        branch_decision_errors=0, checklist_selection_error=0,
        selected_checklist_id=1,
    )
    base.update(overrides)
    return TrialResult(**base)


def test_aggregate_errors_sums_all_four():
    r = _make_result(
        order_errors=1, wrong_mode_actions=2,
        branch_decision_errors=3, checklist_selection_error=1,
    )
    assert aggregate_errors(r) == 7


def test_aggregate_errors_all_zero():
    r = _make_result()
    assert aggregate_errors(r) == 0


def test_aggregate_errors_single_field():
    r = _make_result(order_errors=3)
    assert aggregate_errors(r) == 3
