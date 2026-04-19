"""gspread plumbing — the leading underscore means only sinks.py should import
from this. I isolated it here so that swapping the Sheets backend (credentials
format, library version, etc.) is a single-file change that doesn't touch any
domain or UI code. If gspread or the google-auth library isn't installed the
import is silently swallowed and every _get_sheet_client() call returns None,
causing sinks.py to fall back to CSV automatically."""
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

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
    if gspread is None or Credentials is None:
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


@st.cache_resource(show_spinner=False)
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
    except Exception:
        return False
