from sim import trial as trial_mod
from sim.domain.engine import TrialEngine


class _FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_finalize_latches_summary_before_summary_persist(monkeypatch, ctx, condition_linear, linear_scenario):
    """A slow Sheets append can overlap with another Streamlit rerun.
    Finalization must latch before persist() so the same finished engine cannot
    append duplicate summary rows."""
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("A", now=1.0)
    engine.execute_action("B", now=2.0)
    engine.execute_action("C", now=3.0)

    fake_state = _FakeSessionState(all_summaries=[])
    monkeypatch.setattr(trial_mod.st, "session_state", fake_state)

    calls = []

    def _fake_persist(name, rows):
        calls.append(name)
        if name == "summaries":
            trial_mod._finalize_trial(engine)
        return "google_sheets"

    monkeypatch.setattr(trial_mod, "persist", _fake_persist)

    trial_mod._finalize_trial(engine)
    trial_mod._finalize_trial(engine)

    assert calls.count("events") == 1
    assert calls.count("summaries") == 1


def test_event_persist_failure_does_not_drop_summary(monkeypatch, ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("A", now=1.0)
    engine.execute_action("B", now=2.0)
    engine.execute_action("C", now=3.0)

    fake_state = _FakeSessionState(all_summaries=[])
    monkeypatch.setattr(trial_mod.st, "session_state", fake_state)

    calls = []

    def _fake_persist(name, rows):
        calls.append(name)
        if name == "events":
            raise RuntimeError("events write failed")
        return "google_sheets"

    monkeypatch.setattr(trial_mod, "persist", _fake_persist)

    trial_mod._finalize_trial(engine)

    assert calls == ["summaries", "events"]
    assert len(fake_state["all_summaries"]) == 1
    assert fake_state["summary_trial_1"]["trial_number"] == 1
    assert fake_state["summary_sink"] == "google_sheets"
    assert fake_state["data_sink"] == "error:RuntimeError"
    assert fake_state["_persist_errors"][0]["name"] == "events"


def test_summary_persist_failure_still_updates_summary_screen(monkeypatch, ctx, condition_linear, linear_scenario):
    engine = TrialEngine(linear_scenario, condition_linear, ctx, start_time=0.0)
    engine.select_linear_checklist(linear_scenario.id, now=0.1)
    engine.execute_action("A", now=1.0)
    engine.execute_action("B", now=2.0)
    engine.execute_action("C", now=3.0)

    fake_state = _FakeSessionState(all_summaries=[])
    monkeypatch.setattr(trial_mod.st, "session_state", fake_state)

    def _fake_persist(name, rows):
        if name == "summaries":
            raise RuntimeError("summary write failed")
        return "google_sheets"

    monkeypatch.setattr(trial_mod, "persist", _fake_persist)

    trial_mod._finalize_trial(engine)

    assert len(fake_state["all_summaries"]) == 1
    assert fake_state["summary_trial_1"]["scenario_title"] == linear_scenario.title
    assert fake_state["summary_sink"] == "error:RuntimeError"
    assert fake_state["data_sink"] == "google_sheets"
