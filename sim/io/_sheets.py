"""gspread plumbing — the leading underscore means only sinks.py should import
from this. I isolated it here so that swapping the Sheets backend (credentials
format, library version, etc.) is a single-file change that doesn't touch any
domain or UI code. If gspread or the google-auth library isn't installed the
import is silently swallowed and every _get_sheet_client() call returns None,
causing sinks.py to fall back to CSV automatically."""
from pathlib import Path
from typing import Any, Dict, List

try:
    import streamlit as st
except Exception:
    st = None

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_sheet_client():
    if st is None or gspread is None or Credentials is None:
        return None
    try:
        has_secret = "gcp_service_account" in st.secrets
    except Exception:
        return None
    if not has_secret:
        return None
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=GOOGLE_SCOPES
        )
        return gspread.authorize(creds)
    except Exception:
        return None


if st is not None:
    _cache_resource = st.cache_resource(show_spinner=False)
else:
    def _cache_resource(func):
        return func


@_cache_resource
def _get_spreadsheet():
    client = _get_sheet_client()
    if client is None:
        return None
    try:
        spreadsheet_id = st.secrets.get("google_sheets", {}).get("spreadsheet_id")
    except Exception:
        return None
    if not spreadsheet_id:
        return None
    try:
        return client.open_by_key(spreadsheet_id)
    except Exception:
        return None


def _get_worksheet(name: str, rows: int = 1000, cols: int = 40):
    spreadsheet = _get_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        return spreadsheet.worksheet(name)
    except Exception:
        try:
            return spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)
        except Exception:
            return None


def _append_sheet(name: str, rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return True
    ws = _get_worksheet(name)
    if ws is None:
        return False
    try:
        # Collect keys from ALL rows, not just the first — events emitted in one
        # batch have varying shapes (TRIAL START has minimal extras, DECISION
        # has step_id/choice/correct, etc.) and dropping later-row keys silently
        # corrupts the data.
        seen: List[str] = []
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.append(k)
        row_headers = seen
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
    except Exception:
        return False


def _update_sheet_rows(name: str, match: Dict[str, Any], updates: Dict[str, Any]) -> bool:
    """Update existing worksheet rows matching `match` with `updates`.

    Used for session-level data (NASA-TLX) that is collected after per-trial
    summary rows have already been appended.
    """
    if not match or not updates:
        return False
    ws = _get_worksheet(name)
    if ws is None:
        return False
    try:
        values = ws.get_all_values()
        if not values:
            return False

        headers = list(values[0])
        changed_headers = False
        for key in list(match.keys()) + list(updates.keys()):
            if key not in headers:
                headers.append(key)
                changed_headers = True
        if changed_headers:
            ws.update([headers], "A1")

        match_cols = {key: headers.index(key) for key in match}
        update_cols = {key: headers.index(key) for key in updates}
        matched_rows: List[int] = []

        for row_number, row in enumerate(values[1:], start=2):
            padded = row + [""] * (len(headers) - len(row))
            if all(str(padded[match_cols[key]]) == str(value) for key, value in match.items()):
                matched_rows.append(row_number)

        for row_number in matched_rows:
            for key, value in updates.items():
                ws.update_cell(row_number, update_cols[key] + 1, value)
        return bool(matched_rows)
    except Exception:
        return False
