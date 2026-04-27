import csv

from sim.io import sinks


def test_local_persist_reconciles_headers_and_serializes_nested_cells(tmp_path, monkeypatch):
    monkeypatch.setattr(sinks, "_append_sheet", lambda name, rows: False)
    monkeypatch.setattr(sinks, "LOG_DIR", tmp_path)

    path = sinks.persist("events", [{"a": 1, "nested": [("label", "value")]}])
    sinks.persist("events", [{"a": 2, "b": "later column"}])

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames == ["a", "nested", "b"]
    assert rows[0]["nested"] == '[["label", "value"]]'
    assert rows[0]["b"] == ""
    assert rows[1]["a"] == "2"
    assert rows[1]["b"] == "later column"


def test_update_rows_backfills_matching_local_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(sinks, "_update_sheet_rows", lambda name, match, updates: False)
    monkeypatch.setattr(sinks, "LOG_DIR", tmp_path)

    sinks.persist("summaries", [
        {"session_id": "s1", "trial_number": 1},
        {"session_id": "s1", "trial_number": 2},
        {"session_id": "s2", "trial_number": 1},
    ])

    path = sinks.update_rows(
        "summaries",
        {"session_id": "s1"},
        {"nasa_tlx_mental": 6, "general_comment": "worked"},
    )

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["nasa_tlx_mental"] == "6"
    assert rows[1]["nasa_tlx_mental"] == "6"
    assert rows[2]["nasa_tlx_mental"] == ""
    assert rows[0]["general_comment"] == "worked"
