"""Persistence surface. Hides backend choice (Sheets-first, local CSV fallback).
Hides identity of `balanced_condition` pure vs I/O."""
from typing import Any, Dict, List, Tuple

import pandas as pd

from sim.domain.conditions import balanced_condition as _pure_balanced_condition
from sim.io._sheets import LOG_DIR, _append_sheet, _get_worksheet


def _append_local(name: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{name}.csv"
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header)
    return str(path)


def persist(name: str, rows: List[Dict[str, Any]]) -> str:
    if _append_sheet(name, rows):
        return "google_sheets"
    return _append_local(name, rows)


def record_assignment(assignment: Dict[str, Any]) -> str:
    return persist("assignments", [assignment])


def read_assignment_counts() -> Dict[Tuple[str, str], int]:
    """
    Return a map of (condition, experience) -> count, read from the assignments
    worksheet. Empty dict if Sheets is unavailable (caller falls back to round-robin).
    """
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
    """I/O wrapper — reads counts from Sheets, delegates to pure domain func."""
    counts = read_assignment_counts()
    return _pure_balanced_condition(experience, counts, condition_keys)
