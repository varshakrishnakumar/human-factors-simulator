from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from sim.config import GOOGLE_SCOPES, LOG_DIR

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


def _get_sheet_client():
    if gspread is None or Credentials is None:
        return None
    if "gcp_service_account" not in st.secrets:
        return None
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=GOOGLE_SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def _get_spreadsheet():
    client = _get_sheet_client()
    if client is None:
        return None
    spreadsheet_id = st.secrets.get("google_sheets", {}).get("spreadsheet_id")
    if not spreadsheet_id:
        return None
    return client.open_by_key(spreadsheet_id)


def _get_worksheet(name: str, rows: int = 1000, cols: int = 40):
    spreadsheet = _get_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        return spreadsheet.worksheet(name)
    except Exception:
        return spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)


def _append_sheet(name: str, rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return True
    ws = _get_worksheet(name)
    if ws is None:
        return False

    row_headers = list(rows[0].keys())
    existing = ws.row_values(1)
    if not existing:
        headers = row_headers
        ws.append_row(headers)
    else:
        headers = existing[:]
        for h in row_headers:
            if h not in headers:
                headers.append(h)
        if headers != existing:
            ws.update([headers], "A1")
    values = [[r.get(c, "") for c in headers] for r in rows]
    ws.append_rows(values, value_input_option="USER_ENTERED")
    return True


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
    """
    Pick the condition with the fewest prior assignments for this experience level.
    Tie-breaker: lowest overall count for the condition; final tie-breaker: list order.
    Falls back to the first condition when no data is available.
    """
    counts = read_assignment_counts()
    if not condition_keys:
        return ""

    best_key: Optional[str] = None
    best_score: Optional[Tuple[int, int]] = None
    totals: Dict[str, int] = {}
    for c in condition_keys:
        totals[c] = sum(n for (cond, _), n in counts.items() if cond == c)

    for c in condition_keys:
        per_exp = counts.get((c, experience), 0)
        score = (per_exp, totals[c])
        if best_score is None or score < best_score:
            best_score = score
            best_key = c

    return best_key or condition_keys[0]
