"""Persistence surface for the simulator. Tries Google Sheets first; falls back
to local CSV in logs/. Both backends write the same column sets so analysis
scripts don't need to care which backend was active during a run.

I also put the I/O wrapper for balanced_condition() here — the pure algorithm
lives in domain/conditions.py, this wrapper fetches real counts from Sheets and
calls it. That keeps the domain layer clean and testable while still letting the
live app do real balancing."""
from typing import Any, Dict, List, Tuple

import csv
import json

from sim.domain.conditions import balanced_condition as _pure_balanced_condition
from sim.io._sheets import LOG_DIR, _append_sheet, _get_worksheet, _update_sheet_rows


def _cell_value(value: Any) -> Any:
    """Convert nested event extras into a single sheet/CSV cell value."""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return json.dumps(value)
    except TypeError:
        return str(value)


def _normalise_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: _cell_value(v) for k, v in row.items()} for row in rows]


def _normalise_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _cell_value(v) for k, v in row.items()}


def _append_local(name: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{name}.csv"

    existing_headers: List[str] = []
    existing_rows: List[Dict[str, Any]] = []
    if path.exists() and path.stat().st_size > 0:
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_headers = list(reader.fieldnames or [])
            existing_rows = list(reader)

    headers = existing_headers[:]
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)

    mode = "a" if existing_headers == headers and existing_headers else "w"
    with path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        if mode == "w":
            writer.writeheader()
            writer.writerows(existing_rows)
        writer.writerows(rows)
    return str(path)


def _update_local(name: str, match: Dict[str, Any], updates: Dict[str, Any]) -> str:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{name}.csv"
    if not path.exists() or path.stat().st_size == 0:
        return ""

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    for key in list(match.keys()) + list(updates.keys()):
        if key not in headers:
            headers.append(key)

    for row in rows:
        if all(str(row.get(key, "")) == str(value) for key, value in match.items()):
            row.update(updates)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def persist(name: str, rows: List[Dict[str, Any]]) -> str:
    """Append rows to the named sheet/CSV. Returns 'google_sheets' or the local
    file path so the caller can record which backend was used (stored in
    session_state.data_sink for debugging)."""
    normalised = _normalise_rows(rows)
    if _append_sheet(name, normalised):
        return "google_sheets"
    return _append_local(name, normalised)


def update_rows(name: str, match: Dict[str, Any], updates: Dict[str, Any]) -> str:
    """Update existing rows in a named sheet/CSV.

    Returns 'google_sheets' when the remote worksheet was updated, otherwise
    the local CSV path if the fallback file existed and was rewritten.
    """
    normalised_match = _normalise_row(match)
    normalised_updates = _normalise_row(updates)
    if _update_sheet_rows(name, normalised_match, normalised_updates):
        return "google_sheets"
    return _update_local(name, normalised_match, normalised_updates)


def record_assignment(assignment: Dict[str, Any]) -> str:
    """Persist a single session-start assignment row to the 'assignments' table.
    Called once per session in trial.py's start_session()."""
    return persist("assignments", [assignment])


def read_assignment_counts() -> Dict[Tuple[str, str], int]:
    """Return a map of (condition_key, experience) -> count from the assignments
    worksheet. Returns an empty dict if Sheets is unavailable — the caller
    (balanced_condition below) falls back to round-robin in that case."""
    ws = _get_worksheet("assignments")
    if ws is None:
        return {}
    try:
        records = ws.get_all_records()
    except Exception:
        return {}
    counts: Dict[Tuple[str, str], int] = {}
    for r in records:
        key = (str(r.get("condition", "")), str(r.get("experience", "")))
        counts[key] = counts.get(key, 0) + 1
    return counts


def balanced_condition(experience: str, condition_keys: List[str]) -> str:
    """I/O wrapper around the pure domain function. Fetches current assignment
    counts from Sheets (empty dict if unavailable) and delegates to
    domain/conditions.py's balanced_condition() for the actual selection logic.
    The sidebar calls this to suggest a condition before the session starts."""
    counts = read_assignment_counts()
    return _pure_balanced_condition(experience, counts, condition_keys)
