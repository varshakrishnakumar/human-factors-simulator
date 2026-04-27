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
