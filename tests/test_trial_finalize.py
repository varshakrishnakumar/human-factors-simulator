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


def test_finalize_latches_before_summary_persist(monkeypatch, ctx, condition_linear, linear_scenario):
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
