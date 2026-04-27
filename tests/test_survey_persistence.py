from sim import trial as trial_mod


class _FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_summary_for_sheet_includes_blank_workload_columns():
    row = trial_mod._summary_for_sheet({"session_id": "s1", "trial_number": 1})

    assert row["session_id"] == "s1"
    assert row["nasa_tlx_mental"] == ""
    assert row["nasa_tlx_frustration"] == ""
    assert row["tlx_effort_comment"] == ""
    assert row["general_comment"] == ""


def test_submit_session_survey_backfills_summary_rows(monkeypatch):
    fake_state = _FakeSessionState(
        session_id="s1",
        participant_id="p1",
        experience="None",
        condition_key="linear_high",
    )
    monkeypatch.setattr(trial_mod.st, "session_state", fake_state)

    persist_calls = []
    update_calls = []

    def _fake_persist(name, rows):
        persist_calls.append((name, rows[0]))
        return "google_sheets"

    def _fake_update_rows(name, match, updates):
        update_calls.append((name, match, updates))
        return "google_sheets"

    monkeypatch.setattr(trial_mod, "persist", _fake_persist)
    monkeypatch.setattr(trial_mod, "update_rows", _fake_update_rows)

    trial_mod.submit_session_survey({
        "nasa_tlx_mental": 6,
        "nasa_tlx_temporal": 5,
        "nasa_tlx_effort": 4,
        "nasa_tlx_frustration": 3,
        "general_comment": "fine",
    })

    assert persist_calls[0][0] == "session_workload"
    assert update_calls[0][0] == "summaries"
    assert update_calls[0][1] == {"session_id": "s1"}
    assert update_calls[0][2]["nasa_tlx_mental"] == 6
    assert update_calls[0][2]["tlx_mental_comment"] == ""
    assert update_calls[0][2]["general_comment"] == "fine"
    assert fake_state.session_survey_submitted is True
