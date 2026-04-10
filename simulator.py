import json
import random
import re
import time
import html
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid
import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


BASE_DIR = Path(__file__).resolve().parent
SCENARIO_DIR = BASE_DIR / "scenarios"
ANALYSIS_DIR = BASE_DIR / "analysis"
EVENT_LOG = ANALYSIS_DIR / "events.csv"
SUMMARY_LOG = ANALYSIS_DIR / "summaries.csv"
GROUP_ANALYSIS_DIR = ANALYSIS_DIR / "by_group"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CONDITIONS = {
    "linear_high": {"checklist_type": "linear", "time_limit": 45},
    "linear_low": {"checklist_type": "linear", "time_limit": 90},
    "branching_high": {"checklist_type": "branching", "time_limit": 45},
    "branching_low": {"checklist_type": "branching", "time_limit": 90},
}

ACTION_HELP = {
    "ACK ALARM": "Acknowledge the annunciated navigation fault.",
    "SILENCE CAUTION TONE": "Silence the caution tone after the alarm is acknowledged.",
    "OPEN GNC STATUS PANEL": "Open guidance, navigation, and control status details.",
    "RESET NAVIGATION FILTER": "Reset the navigation filter while the spacecraft remains in HOLD.",
    "REINITIALIZE STAR TRACKER": "Reinitialize the star tracker to recover valid navigation data.",
    "CONFIRM NAVIGATION DATA RESTORED": "Confirm the navigation solution is restored and valid.",
    "SELECT AUTO MODE": "Command the spacecraft back into AUTO mode.",
    "VERIFY ATTITUDE STABLE": "Confirm the spacecraft attitude is stable after recovery.",
    "REPORT PROCEDURE COMPLETE": "Report that the procedure is complete.",
}

BACKGROUND_OPTIONS = [
    "None",
    "Some aviation",
    "Some spacecraft ops",
    "Professional",
]

SAMPLE_SCENARIOS = [
    {
        "scenario_id": 1,
        "title": "Navigation Fault Recovery",
        "initial_mode": "AUTO",
        "fault": "Loss of navigation data",
        "transition_reason": "Navigation data fault triggered an automatic HOLD transition",
        "auto_transition": {"time": 5, "new_mode": "HOLD"},
        "correct_mode": "AUTO",
        "expected_transition_mode": "HOLD",
        "diagnosis_prompt": "Did the spacecraft transition because of loss of navigation data?",
        "diagnosis_options": [
            "Yes - loss of navigation data",
            "No - another fault triggered the transition",
        ],
        "correct_diagnosis": "Yes - loss of navigation data",
        "linear_actions": [
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN GNC STATUS PANEL",
            "RESET NAVIGATION FILTER",
            "REINITIALIZE STAR TRACKER",
            "CONFIRM NAVIGATION DATA RESTORED",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ],
        "branch_opening_actions": [
            "ACK ALARM",
            "OPEN GNC STATUS PANEL",
        ],
        "branch_recovery_actions": [
            "RESET NAVIGATION FILTER",
            "REINITIALIZE STAR TRACKER",
        ],
        "branch_final_actions": [
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ],
        "action_expected_modes": {
            "RESET NAVIGATION FILTER": "HOLD",
            "REINITIALIZE STAR TRACKER": "HOLD",
            "CONFIRM NAVIGATION DATA RESTORED": "HOLD",
            "SELECT AUTO MODE": "HOLD",
            "VERIFY ATTITUDE STABLE": "AUTO",
            "REPORT PROCEDURE COMPLETE": "AUTO",
        },
        "allowed_actions": [
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN GNC STATUS PANEL",
            "RESET NAVIGATION FILTER",
            "REINITIALIZE STAR TRACKER",
            "CONFIRM NAVIGATION DATA RESTORED",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ],
    },
]


def ensure_scenario_files() -> None:
    SCENARIO_DIR.mkdir(exist_ok=True)
    for s in SAMPLE_SCENARIOS:
        out = SCENARIO_DIR / f"scenario_{s['scenario_id']}.json"
        if not out.exists():
            out.write_text(json.dumps(s, indent=2))
            
    


def load_scenarios() -> List[Dict[str, Any]]:
    ensure_scenario_files()
    scenarios = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        with open(path, "r") as f:
            scenario = json.load(f)
            scenarios.append(normalize_scenario(scenario))
    return scenarios


def get_sheet_client():
    if gspread is None or Credentials is None:
        return None

    if "gcp_service_account" not in st.secrets:
        return None

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=GOOGLE_SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_log_worksheets():
    client = get_sheet_client()
    if client is None:
        return None, None

    spreadsheet_id = st.secrets.get("google_sheets", {}).get("spreadsheet_id")
    if not spreadsheet_id:
        return None, None

    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        event_ws = spreadsheet.worksheet("events")
    except Exception:
        event_ws = spreadsheet.add_worksheet(title="events", rows=1000, cols=30)

    try:
        summary_ws = spreadsheet.worksheet("summaries")
    except Exception:
        summary_ws = spreadsheet.add_worksheet(title="summaries", rows=1000, cols=40)

    return event_ws, summary_ws



def append_rows_to_google_sheet(kind: str, rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return True

    worksheets = get_log_worksheets()
    if worksheets == (None, None):
        return False

    target_ws = worksheets[0] if kind == "events" else worksheets[1]
    if target_ws is None:
        return False

    row_headers = list(rows[0].keys())
    existing_headers = target_ws.row_values(1)

    if not existing_headers:
        target_headers = row_headers
        target_ws.append_row(target_headers)
    else:
        target_headers = existing_headers[:]
        for header in row_headers:
            if header not in target_headers:
                target_headers.append(header)
        if target_headers != existing_headers:
            target_ws.update([target_headers], "A1")

    values = [[row.get(col, "") for col in target_headers] for row in rows]
    target_ws.append_rows(values, value_input_option="USER_ENTERED")
    return True



def append_rows_local(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header)



def persist_rows(kind: str, rows: List[Dict[str, Any]], local_paths) -> str:
    ok = append_rows_to_google_sheet(kind, rows)
    if ok:
        return "google_sheets"

    if isinstance(local_paths, Path):
        local_paths = [local_paths]

    written_paths = []
    for path in local_paths:
        append_rows_local(path, rows)
        written_paths.append(str(path))
    return ", ".join(written_paths)


def sanitize_group_name(group_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", group_name.strip().lower()).strip("_")
    return cleaned or "unassigned"


def init_state() -> None:
    defaults = {
        "participant_id": "",
        "subject_group": "",
        "experience": "None",
        "session_started": False,
        "session_id": None,
        "condition_assignment_mode": "manual",
        "condition_key": None,
        "scenario_pool": [],
        "trial_index": 0,
        "num_trials": 3,
        "trial_order": [],
        "scenario": None,
        "trial_started": False,
        "start_time": None,
        "mode": None,
        "event_rows": [],
        "trial_event_rows": [],
        "completed_actions": [],
        "wrong_mode_actions": 0,
        "order_errors": 0,
        "mode_checks": 0,
        "mode_check_errors": 0,
        "diagnosis_attempts": 0,
        "diagnosis_errors": 0,
        "branch_gate_open": False,
        "mode_verified": False,
        "diagnosis_verified": False,
        "recovery_checks": 0,
        "recovery_check_errors": 0,
        "recovery_verified": False,
        "final_mode_checks": 0,
        "final_mode_check_errors": 0,
        "final_mode_verified": False,
        "branch_wait_logged": False,
        "finished": False,
        "summary": None,
        "survey_submitted": False,
        "data_sink": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value



def reset_trial_state() -> None:
    st.session_state.trial_started = False
    st.session_state.start_time = None
    st.session_state.mode = None
    st.session_state.trial_event_rows = []
    st.session_state.completed_actions = []
    st.session_state.wrong_mode_actions = 0
    st.session_state.order_errors = 0
    st.session_state.mode_checks = 0
    st.session_state.mode_check_errors = 0
    st.session_state.diagnosis_attempts = 0
    st.session_state.diagnosis_errors = 0
    st.session_state.branch_gate_open = False
    st.session_state.mode_verified = False
    st.session_state.diagnosis_verified = False
    st.session_state.recovery_checks = 0
    st.session_state.recovery_check_errors = 0
    st.session_state.recovery_verified = False
    st.session_state.final_mode_checks = 0
    st.session_state.final_mode_check_errors = 0
    st.session_state.final_mode_verified = False
    st.session_state.branch_wait_logged = False
    st.session_state.finished = False
    st.session_state.summary = None
    st.session_state.survey_submitted = False
    for key in [
        "nasa_tlx_mental",
        "nasa_tlx_temporal",
        "nasa_tlx_effort",
        "nasa_tlx_frustration",
        "mode_guess",
        "diagnosis_guess",
        "recovery_guess",
        "final_mode_guess",
    ]:
        if key in st.session_state:
            del st.session_state[key]

def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --hf-bg: #05070c;
            --hf-bg-alt: #0a1019;
            --hf-panel: #0b1119;
            --hf-panel-alt: #101827;
            --hf-line: rgba(120, 147, 181, 0.24);
            --hf-line-strong: rgba(125, 211, 252, 0.38);
            --hf-text: #ecf2f8;
            --hf-muted: #94a7bd;
            --hf-blue: #5fb4ff;
            --hf-cyan: #7dd3fc;
            --hf-green: #4ade80;
            --hf-amber: #facc15;
            --hf-orange: #fb923c;
            --hf-red: #fb4d3d;
        }
        .stApp {
            background:
                radial-gradient(circle at top, rgba(35, 61, 96, 0.34), transparent 34%),
                linear-gradient(180deg, #070b11 0%, #05070c 58%, #03050a 100%);
            color: var(--hf-text);
        }
        [data-testid="stHeader"] {
            background: rgba(5, 7, 12, 0.82);
            border-bottom: 1px solid var(--hf-line);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #070b11 0%, #0c121c 100%);
            border-right: 1px solid var(--hf-line);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: var(--hf-text);
        }
        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1500px;
            padding-top: 1.75rem;
            padding-bottom: 3rem;
        }
        .hf-masthead {
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(145deg, rgba(10, 16, 25, 0.98), rgba(16, 24, 38, 0.96));
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.03);
            padding: 1.35rem 1.45rem 1.3rem;
            margin-bottom: 1.35rem;
        }
        .hf-masthead::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 10px;
            background: repeating-linear-gradient(
                -45deg,
                rgba(250, 204, 21, 0.92) 0 12px,
                rgba(6, 10, 15, 1) 12px 24px
            );
        }
        .hf-masthead::after {
            content: "";
            position: absolute;
            top: -60px;
            right: -60px;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(95, 180, 255, 0.18) 0%, rgba(95, 180, 255, 0) 70%);
        }
        .hf-masthead-eyebrow {
            margin-top: 0.65rem;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            color: var(--hf-amber);
        }
        .hf-masthead-title {
            margin-top: 0.45rem;
            font-size: clamp(2.15rem, 4vw, 3.85rem);
            line-height: 0.96;
            font-weight: 850;
            color: var(--hf-text);
        }
        .hf-masthead-subtitle {
            max-width: 58rem;
            margin-top: 0.55rem;
            color: var(--hf-muted);
            font-size: 1rem;
            line-height: 1.55;
        }
        .hf-chip-row {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 1.2rem;
        }
        .hf-chip {
            position: relative;
            overflow: hidden;
            border-radius: 16px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(180deg, rgba(14, 21, 32, 0.96), rgba(10, 15, 24, 0.94));
            padding: 0.85rem 0.95rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
        }
        .hf-chip::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            background: var(--hf-accent, var(--hf-blue));
        }
        .hf-chip-label {
            font-size: 0.72rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--hf-muted);
            margin-bottom: 0.45rem;
        }
        .hf-chip-value {
            color: var(--hf-text);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 1.1rem;
            line-height: 1.25;
            word-break: break-word;
        }
        .hf-chip-blue { --hf-accent: var(--hf-blue); }
        .hf-chip-amber { --hf-accent: var(--hf-amber); }
        .hf-chip-red { --hf-accent: var(--hf-red); }
        .hf-chip-green { --hf-accent: var(--hf-green); }
        .hf-panel-titlebar {
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 1rem;
            padding: 0.35rem 0 0.75rem;
            margin-bottom: 0.9rem;
            border-bottom: 1px solid var(--hf-line);
        }
        .hf-panel-kicker {
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--hf-cyan);
            font-weight: 700;
        }
        .hf-panel-title {
            margin-top: 0.22rem;
            color: var(--hf-text);
            font-size: 1.8rem;
            line-height: 1.05;
            font-weight: 800;
        }
        .hf-panel-subtitle {
            margin-top: 0.3rem;
            color: var(--hf-muted);
            font-size: 0.93rem;
            line-height: 1.45;
            max-width: 42rem;
        }
        .hf-panel-tag {
            border-radius: 999px;
            border: 1px solid var(--hf-line-strong);
            background: rgba(12, 19, 30, 0.84);
            color: var(--hf-amber);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.74rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            padding: 0.5rem 0.7rem;
            white-space: nowrap;
        }
        .hf-telemetry-card {
            position: relative;
            overflow: hidden;
            border-radius: 18px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(180deg, rgba(13, 20, 31, 0.98), rgba(8, 13, 22, 0.96));
            padding: 0.95rem 1rem 1rem;
            margin-bottom: 0.95rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
        }
        .hf-telemetry-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 3px;
            background: var(--hf-accent, var(--hf-blue));
        }
        .hf-telemetry-blue { --hf-accent: var(--hf-blue); }
        .hf-telemetry-cyan { --hf-accent: var(--hf-cyan); }
        .hf-telemetry-amber { --hf-accent: var(--hf-amber); }
        .hf-telemetry-red { --hf-accent: var(--hf-red); }
        .hf-telemetry-green { --hf-accent: var(--hf-green); }
        .hf-telemetry-label {
            color: var(--hf-muted);
            font-size: 0.7rem;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .hf-telemetry-value {
            color: var(--hf-text);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 1.45rem;
            line-height: 1.15;
        }
        .hf-telemetry-note {
            margin-top: 0.55rem;
            color: var(--hf-muted);
            font-size: 0.83rem;
            line-height: 1.45;
        }
        .hf-mode-shell {
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(145deg, rgba(9, 15, 23, 0.98), rgba(12, 19, 30, 0.96));
            padding: 1.05rem 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03), 0 18px 40px rgba(0, 0, 0, 0.28);
        }
        .hf-mode-shell::before {
            content: "";
            position: absolute;
            inset: 18% 16%;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 999px;
        }
        .hf-mode-label {
            color: var(--hf-muted);
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            text-align: center;
            margin-bottom: 0.7rem;
            position: relative;
            z-index: 1;
        }
        .hf-mode-value {
            position: relative;
            z-index: 1;
            border-radius: 18px;
            background: linear-gradient(180deg, var(--mode-color), var(--mode-color));
            box-shadow: 0 0 34px var(--mode-glow), inset 0 1px 0 rgba(255, 255, 255, 0.2);
            color: white;
            padding: 1rem 1.1rem;
            text-align: center;
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: clamp(1.9rem, 4vw, 3rem);
            letter-spacing: 0.16em;
            font-weight: 800;
        }
        .hf-mode-caption {
            position: relative;
            z-index: 1;
            margin-top: 0.7rem;
            text-align: center;
            color: var(--hf-muted);
            font-size: 0.82rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }
        .hf-fault {
            position: relative;
            overflow: hidden;
            border-radius: 18px;
            border: 1px solid rgba(251, 77, 61, 0.38);
            background: linear-gradient(180deg, rgba(65, 15, 15, 0.92), rgba(37, 11, 11, 0.88));
            color: #ffe6e3;
            padding: 0.95rem 1rem;
            margin: 0.75rem 0 1rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
        }
        .hf-fault::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 8px;
            background: linear-gradient(180deg, var(--hf-red), var(--hf-orange));
        }
        .hf-fault-label {
            color: rgba(255, 226, 222, 0.76);
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            margin-left: 0.3rem;
        }
        .hf-fault-value {
            margin-left: 0.3rem;
            margin-top: 0.35rem;
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 1.1rem;
            line-height: 1.35;
            color: #fff5f4;
            text-transform: uppercase;
        }
        .hf-notice {
            border-radius: 16px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(180deg, rgba(13, 20, 31, 0.98), rgba(10, 16, 25, 0.94));
            padding: 0.85rem 1rem;
            margin: 0.75rem 0;
            color: var(--hf-text);
            line-height: 1.45;
        }
        .hf-notice-info {
            border-color: rgba(95, 180, 255, 0.32);
            background: linear-gradient(180deg, rgba(13, 29, 48, 0.96), rgba(10, 21, 36, 0.94));
            color: #d9efff;
        }
        .hf-notice-warn {
            border-color: rgba(250, 204, 21, 0.34);
            background: linear-gradient(180deg, rgba(43, 34, 11, 0.96), rgba(31, 24, 9, 0.94));
            color: #fff1b8;
        }
        .hf-notice-success {
            border-color: rgba(74, 222, 128, 0.34);
            background: linear-gradient(180deg, rgba(14, 42, 26, 0.96), rgba(10, 28, 18, 0.94));
            color: #dcfce7;
        }
        .hf-notice-danger {
            border-color: rgba(251, 77, 61, 0.34);
            background: linear-gradient(180deg, rgba(57, 16, 16, 0.96), rgba(35, 12, 12, 0.94));
            color: #ffe4e0;
        }
        .hf-action-help {
            min-height: 2.5rem;
            margin: 0.45rem 0.15rem 1rem;
            color: var(--hf-muted);
            font-size: 0.86rem;
            line-height: 1.45;
        }
        .hf-step-current,
        .hf-step-done,
        .hf-step-upcoming {
            position: relative;
            border-radius: 16px;
            border: 1px solid var(--hf-line);
            padding: 0.82rem 0.95rem;
            margin-bottom: 0.55rem;
            background: linear-gradient(180deg, rgba(13, 20, 31, 0.96), rgba(9, 14, 22, 0.94));
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.98rem;
            line-height: 1.45;
            color: var(--hf-text);
        }
        .hf-step-current::before,
        .hf-step-done::before,
        .hf-step-upcoming::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 6px;
        }
        .hf-step-current {
            border-color: rgba(95, 180, 255, 0.36);
            box-shadow: inset 0 0 0 1px rgba(95, 180, 255, 0.08);
        }
        .hf-step-current::before {
            background: var(--hf-blue);
        }
        .hf-step-done {
            border-color: rgba(74, 222, 128, 0.34);
            color: #dcfce7;
        }
        .hf-step-done::before {
            background: var(--hf-green);
        }
        .hf-step-upcoming {
            color: var(--hf-muted);
        }
        .hf-step-upcoming::before {
            background: rgba(148, 163, 184, 0.55);
        }
        .hf-section-header {
            padding: 0.9rem 0 0.45rem;
            margin-top: 0.6rem;
            border-bottom: 1px dashed rgba(148, 163, 184, 0.18);
        }
        .hf-section-kicker {
            color: var(--hf-amber);
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            font-weight: 700;
        }
        .hf-section-title {
            margin-top: 0.22rem;
            color: var(--hf-text);
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 1.35;
        }
        .hf-inline-stat {
            margin-top: 0.9rem;
            color: var(--hf-muted);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .stButton > button {
            width: 100%;
            min-height: 3.45rem;
            border-radius: 16px;
            border: 1px solid rgba(120, 147, 181, 0.26);
            background: linear-gradient(180deg, rgba(17, 26, 39, 0.98), rgba(10, 16, 25, 0.96));
            color: var(--hf-text);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 10px 24px rgba(0, 0, 0, 0.2);
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
        }
        .stButton > button p {
            color: inherit;
            font-size: 1rem;
        }
        .stButton > button:hover:not(:disabled) {
            transform: translateY(-1px);
            border-color: rgba(95, 180, 255, 0.5);
            background: linear-gradient(180deg, rgba(23, 35, 52, 0.98), rgba(11, 18, 29, 0.96));
            box-shadow: 0 16px 28px rgba(0, 0, 0, 0.28), 0 0 0 1px rgba(95, 180, 255, 0.12);
        }
        .stButton > button:disabled {
            color: rgba(236, 242, 248, 0.45);
            -webkit-text-fill-color: rgba(236, 242, 248, 0.45);
            background: linear-gradient(180deg, rgba(14, 19, 28, 0.82), rgba(9, 13, 20, 0.78));
            border-style: dashed;
            border-color: rgba(120, 147, 181, 0.16);
            opacity: 1;
        }
        .stProgress > div > div {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
        }
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, var(--hf-blue), var(--hf-cyan));
            border-radius: 999px;
        }
        [data-testid="stMetric"] {
            border-radius: 16px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(180deg, rgba(13, 20, 31, 0.98), rgba(9, 14, 22, 0.95));
            padding: 0.7rem 0.85rem;
        }
        [data-testid="stMetricLabel"] {
            color: var(--hf-muted);
            text-transform: uppercase;
            letter-spacing: 0.16em;
        }
        [data-testid="stMetricValue"] {
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            color: var(--hf-text);
        }
        @media (max-width: 900px) {
            .hf-chip-row {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .hf-panel-titlebar {
                flex-direction: column;
                align-items: start;
            }
            .hf-panel-tag {
                white-space: normal;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def mode_color(mode: str) -> str:
    colors = {
        "AUTO": "#1565c0",
        "NOMINAL": "#2e7d32",
        "HOLD": "#ef6c00",
        "SAFE": "#c62828",
        "MANUAL": "#455a64",
        "AUTO_APPROACH": "#1565c0",
        "AUTO_THERMAL": "#6a1b9a",
    }
    return colors.get(mode, "#424242")


def mode_glow(mode: str) -> str:
    glows = {
        "AUTO": "rgba(21, 101, 192, 0.42)",
        "NOMINAL": "rgba(46, 125, 50, 0.36)",
        "HOLD": "rgba(239, 108, 0, 0.34)",
        "SAFE": "rgba(198, 40, 40, 0.36)",
        "MANUAL": "rgba(69, 90, 100, 0.3)",
    }
    return glows.get(mode, "rgba(148, 163, 184, 0.24)")


def escape_text(value: Any) -> str:
    return html.escape(str(value))


def render_panel_heading(title: str, tag: str, subtitle: str = "") -> None:
    subtitle_html = f'<div class="hf-panel-subtitle">{escape_text(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="hf-panel-titlebar">
            <div>
                <div class="hf-panel-kicker">{escape_text(tag)}</div>
                <div class="hf-panel-title">{escape_text(title)}</div>
                {subtitle_html}
            </div>
            <div class="hf-panel-tag">{escape_text(tag)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_telemetry_row(cards: List[Dict[str, str]]) -> None:
    if not cards:
        return

    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        tone = card.get("tone", "blue")
        note = card.get("note", "")
        note_html = f'<div class="hf-telemetry-note">{escape_text(note)}</div>' if note else ""
        with col:
            st.markdown(
                f"""
                <div class="hf-telemetry-card hf-telemetry-{escape_text(tone)}">
                    <div class="hf-telemetry-label">{escape_text(card['label'])}</div>
                    <div class="hf-telemetry-value">{escape_text(card['value'])}</div>
                    {note_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_notice(message: str, tone: str = "info") -> None:
    st.markdown(
        f'<div class="hf-notice hf-notice-{escape_text(tone)}">{escape_text(message)}</div>',
        unsafe_allow_html=True,
    )


def render_section_header(kicker: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="hf-section-header">
            <div class="hf-section-kicker">{escape_text(kicker)}</div>
            <div class="hf-section-title">{escape_text(title)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_help(text: str) -> None:
    st.markdown(
        f'<div class="hf-action-help">{escape_text(text)}</div>',
        unsafe_allow_html=True,
    )


def render_mode_badge(mode: str) -> None:
    color = mode_color(mode)
    glow = mode_glow(mode)
    st.markdown(
        f"""
        <div class="hf-mode-shell" style="--mode-color:{color}; --mode-glow:{glow};">
            <div class="hf-mode-label">Current Spacecraft Mode</div>
            <div class="hf-mode-value">{escape_text(mode)}</div>
            <div class="hf-mode-caption">Active control state monitor</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_timer(rem: float, total: int) -> None:
    progress = max(0.0, min(1.0, rem / total))
    st.progress(progress)

    if rem <= 10:
        render_notice(f"Critical time window // {int(rem)} s remaining", "danger")
    elif rem <= 20:
        render_notice(f"Compressed response window // {int(rem)} s remaining", "warn")
    else:
        render_notice(f"Mission timer nominal // {int(rem)} s remaining", "info")

def start_session(scenarios: List[Dict[str, Any]]) -> None:
    st.session_state.session_started = True

    st.session_state.session_id = str(uuid.uuid4())[:8]

    if st.session_state.condition_assignment_mode == "random":
        st.session_state.condition_key = random.choice(list(CONDITIONS.keys()))

    n = min(st.session_state.num_trials, len(scenarios))
    st.session_state.trial_order = random.sample(scenarios, n)
    st.session_state.trial_index = 0
    load_current_trial()



def load_current_trial() -> None:
    reset_trial_state()
    st.session_state.scenario = st.session_state.trial_order[st.session_state.trial_index]
    st.session_state.trial_started = True
    st.session_state.start_time = time.time()
    st.session_state.mode = st.session_state.scenario["initial_mode"]
    log_event("TRIAL START", {"trial_number": current_trial_number()})



def current_trial_number() -> int:
    return st.session_state.trial_index + 1



def total_trials() -> int:
    return len(st.session_state.trial_order)



def elapsed_time() -> float:
    if not st.session_state.start_time:
        return 0.0
    return time.time() - st.session_state.start_time



def current_time_limit() -> int:
    return CONDITIONS[st.session_state.condition_key]["time_limit"]



def remaining_time() -> float:
    return max(0.0, current_time_limit() - elapsed_time())



def checklist_type() -> str:
    return CONDITIONS[st.session_state.condition_key]["checklist_type"]


def current_subject_group() -> str:
    entered_group = st.session_state.get("subject_group", "").strip()
    if entered_group:
        return entered_group
    return st.session_state.condition_key or "unassigned"


def group_log_paths(kind: str) -> List[Path]:
    filename = "events.csv" if kind == "events" else "summaries.csv"
    aggregate_path = EVENT_LOG if kind == "events" else SUMMARY_LOG
    group_dir = GROUP_ANALYSIS_DIR / sanitize_group_name(current_subject_group())
    return [aggregate_path, group_dir / filename]


def required_actions() -> List[str]:
    scenario = st.session_state.scenario
    if checklist_type() == "linear":
        return scenario["linear_actions"]
    return (
        scenario["branch_opening_actions"]
        + scenario["branch_recovery_actions"]
        + scenario["branch_final_actions"]
    )


def checklist_omissions() -> List[str]:
    scenario = st.session_state.scenario
    omissions = [action for action in required_actions() if action not in st.session_state.completed_actions]

    if checklist_type() == "branching":
        if not st.session_state.mode_verified:
            omissions.append("VERIFY CURRENT MODE")
        if not st.session_state.diagnosis_verified:
            omissions.append("CONFIRM REASON FOR TRANSITION")
        if not st.session_state.recovery_verified:
            omissions.append("CONFIRM NAVIGATION DATA RESTORED")
        if not st.session_state.final_mode_verified:
            omissions.append("VERIFY INTENDED FINAL MODE")

    return omissions


def action_expected_mode(action: str) -> Optional[str]:
    return st.session_state.scenario.get("action_expected_modes", {}).get(action)


def completed_all(actions: List[str]) -> bool:
    return all(action in st.session_state.completed_actions for action in actions)


def action_disabled(action: str) -> bool:
    if checklist_type() == "linear":
        return action in required_actions() and action != current_expected_step()

    scenario = st.session_state.scenario
    if action in scenario["branch_opening_actions"]:
        return False
    if action in scenario["branch_recovery_actions"]:
        return not st.session_state.branch_gate_open
    if action in scenario["branch_final_actions"]:
        return not (st.session_state.recovery_verified and st.session_state.final_mode_verified)
    if action == "CONFIRM NAVIGATION DATA RESTORED":
        return True
    return False


def log_event(action: str, extra=None):

    row = {
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
        "subject_group": current_subject_group(),
        "condition": st.session_state.condition_key,
        "trial_number": current_trial_number(),
        "scenario_id": st.session_state.scenario["scenario_id"],
        "timestamp_s": round(elapsed_time(), 3),
        "mode": st.session_state.mode,
        "action": action
    }

    if extra:
        row.update(extra)

    st.session_state.event_rows.append(row)
    st.session_state.trial_event_rows.append(row)



def maybe_auto_transition() -> None:
    scenario = st.session_state.scenario
    if not scenario or not st.session_state.trial_started:
        return

    transition_time = scenario["auto_transition"]["time"]
    new_mode = scenario["auto_transition"]["new_mode"]
    if elapsed_time() >= transition_time and st.session_state.mode != new_mode:
        old_mode = st.session_state.mode
        st.session_state.mode = new_mode
        log_event(
            "AUTO TRANSITION",
            {
                "from_mode": old_mode,
                "to_mode": new_mode,
                "note": f"Automatic transition at {transition_time}s",
            },
        )



def current_expected_step() -> Optional[str]:
    for step in required_actions():
        if step not in st.session_state.completed_actions:
            return step
    return None



def step_order_status(action: str) -> Tuple[bool, Optional[str]]:
    expected = current_expected_step()
    if expected is None:
        return True, None
    return action == expected, expected



def execute_action(action: str) -> None:
    scenario = st.session_state.scenario
    checklist = checklist_type()
    required = required_actions()

    if checklist == "branching":
        if action in scenario["branch_recovery_actions"] and not st.session_state.branch_gate_open:
            log_event("BLOCKED ACTION", {"attempted_action": action, "reason": "verify_mode_and_fault_first"})
            render_notice("Verify current mode and confirm the transition cause before recovery actions.", "warn")
            return

        if action in scenario["branch_final_actions"] and not (
            st.session_state.recovery_verified and st.session_state.final_mode_verified
        ):
            log_event("BLOCKED ACTION", {"attempted_action": action, "reason": "final_branch_locked"})
            render_notice("Complete the recovery-condition and final-mode checks before final recovery actions.", "warn")
            return

    in_required_actions = action in required
    in_allowed_actions = action in scenario.get("allowed_actions", [])

    if not in_allowed_actions:
        log_event("UNAVAILABLE ACTION", {"attempted_action": action})
        render_notice("That action is not available in this scenario.", "danger")
        return

    if checklist == "linear" and in_required_actions:
        in_order, expected = step_order_status(action)
        if not in_order:
            st.session_state.order_errors += 1
            log_event("ORDER ERROR", {"attempted_action": action, "expected_action": expected})

    expected_mode = action_expected_mode(action)
    wrong_mode = False
    if expected_mode and st.session_state.mode != expected_mode:
        st.session_state.wrong_mode_actions += 1
        wrong_mode = True

    if action not in st.session_state.completed_actions and in_required_actions:
        st.session_state.completed_actions.append(action)

    previous_mode = st.session_state.mode

    if action == "SELECT AUTO MODE":
        st.session_state.mode = "AUTO"

    log_event(
        action,
        {
            "wrong_mode": wrong_mode,
            "from_mode": previous_mode,
            "to_mode": st.session_state.mode,
        },
    )



def submit_mode_check(mode_guess: str) -> None:
    st.session_state.mode_checks += 1
    expected_mode = st.session_state.scenario.get("expected_transition_mode", "HOLD")
    correct = mode_guess == expected_mode and st.session_state.mode == expected_mode
    if not correct:
        st.session_state.mode_check_errors += 1
    else:
        st.session_state.mode_verified = True
    log_event("MODE CHECK", {"guess": mode_guess, "correct": correct})



def submit_diagnosis(diagnosis_guess: str) -> None:
    scenario = st.session_state.scenario
    st.session_state.diagnosis_attempts += 1
    correct = diagnosis_guess == scenario["correct_diagnosis"]
    if not correct:
        st.session_state.diagnosis_errors += 1
    else:
        st.session_state.diagnosis_verified = True
    log_event("DIAGNOSIS CHECK", {"guess": diagnosis_guess, "correct": correct})

    if st.session_state.mode_verified and st.session_state.diagnosis_verified:
        st.session_state.branch_gate_open = True


def submit_recovery_check(recovery_guess: str) -> None:
    st.session_state.recovery_checks += 1
    correct = recovery_guess == "Yes" and completed_all(st.session_state.scenario["branch_recovery_actions"])
    if not correct:
        st.session_state.recovery_check_errors += 1
    else:
        st.session_state.recovery_verified = True
    log_event("RECOVERY CHECK", {"guess": recovery_guess, "correct": correct})


def submit_final_mode_check(final_mode_guess: str) -> None:
    st.session_state.final_mode_checks += 1
    correct = final_mode_guess == st.session_state.scenario["correct_mode"]
    if not correct:
        st.session_state.final_mode_check_errors += 1
    else:
        st.session_state.final_mode_verified = True
    log_event("FINAL MODE CHECK", {"guess": final_mode_guess, "correct": correct})



def can_finish_trial() -> Tuple[bool, str]:
    missing = checklist_omissions()
    if missing and remaining_time() > 0:
        return False, "Complete the required procedure or let the timer expire before finishing."
    if not st.session_state.survey_submitted:
        return False, "Submit the workload survey first."
    return True, ""

def normalize_scenario(s: dict) -> dict:
    s.setdefault("transition_reason", "Not shown")
    s.setdefault("diagnosis_prompt", f"Why did the spacecraft leave {s.get('initial_mode', 'the current mode')}?")
    s.setdefault("diagnosis_options", [s.get("fault", "Unknown fault")])
    s.setdefault("correct_diagnosis", s.get("fault", "Unknown fault"))
    s.setdefault("linear_actions", s.get("correct_actions", []))
    s.setdefault("branch_opening_actions", [])
    s.setdefault("branch_recovery_actions", [])
    s.setdefault("branch_final_actions", [])
    s.setdefault("expected_transition_mode", s.get("auto_transition", {}).get("new_mode", "HOLD"))
    s.setdefault("action_expected_modes", {})
    if "allowed_actions" not in s:
        allowed = s["linear_actions"] + s["branch_opening_actions"] + s["branch_recovery_actions"] + s["branch_final_actions"]
        s["allowed_actions"] = list(dict.fromkeys(allowed))
    return s

def finish_trial(timeout: bool = False) -> None:
    if st.session_state.finished:
        return

    scenario = st.session_state.scenario
    completed = st.session_state.completed_actions
    omissions = checklist_omissions()
    extra_actions = [a for a in completed if a not in required_actions()]

    summary = {
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
        "subject_group": current_subject_group(),
        "experience": st.session_state.experience,
        "condition": st.session_state.condition_key,
        "checklist_type": checklist_type(),
        "time_limit": current_time_limit(),
        "trial_number": current_trial_number(),
        "scenario_id": scenario["scenario_id"],
        "scenario_title": scenario["title"],
        "fault": scenario["fault"],
        "transition_reason": scenario.get("transition_reason", ""),
        "completion_time_s": round(elapsed_time(), 3),
        "timed_out": timeout,
        "wrong_mode_actions": st.session_state.wrong_mode_actions,
        "order_errors": st.session_state.order_errors,
        "mode_checks": st.session_state.mode_checks,
        "mode_check_errors": st.session_state.mode_check_errors,
        "diagnosis_attempts": st.session_state.diagnosis_attempts,
        "diagnosis_errors": st.session_state.diagnosis_errors,
        "recovery_checks": st.session_state.recovery_checks,
        "recovery_check_errors": st.session_state.recovery_check_errors,
        "final_mode_checks": st.session_state.final_mode_checks,
        "final_mode_check_errors": st.session_state.final_mode_check_errors,
        "step_omissions": len(omissions),
        "extra_actions": len(extra_actions),
        "completed_all_required": len(omissions) == 0,
        "actions_completed": " | ".join(completed),
        "omitted_actions": " | ".join(omissions),
        "nasa_tlx_mental": st.session_state.get("nasa_tlx_mental", None),
        "nasa_tlx_temporal": st.session_state.get("nasa_tlx_temporal", None),
        "nasa_tlx_effort": st.session_state.get("nasa_tlx_effort", None),
        "nasa_tlx_frustration": st.session_state.get("nasa_tlx_frustration", None),
    }

    log_event("TRIAL FINISH", {"timeout": timeout, "omissions": len(omissions)})

    event_paths = group_log_paths("events")
    summary_paths = group_log_paths("summaries")
    data_sink = persist_rows("events", st.session_state.trial_event_rows, event_paths)
    persist_rows("summaries", [summary], summary_paths)
    st.session_state.data_sink = data_sink
    st.session_state.summary = summary
    st.session_state.finished = True
    st.session_state.trial_event_rows = []


def render_sidebar_setup(scenarios: List[Dict[str, Any]]) -> None:
    st.sidebar.header("Experiment Setup")
    st.session_state.participant_id = st.sidebar.text_input(
        "Participant ID",
        value=st.session_state.participant_id,
        help="Required before starting the session.",
    )

    st.session_state.subject_group = st.sidebar.text_input(
        "Subject group",
        value=st.session_state.subject_group,
        help="Optional grouping label for analysis. If left blank, the assigned condition is used.",
    )

    st.session_state.experience = st.sidebar.selectbox(
        "Relevant experience",
        BACKGROUND_OPTIONS,
        index=BACKGROUND_OPTIONS.index(st.session_state.experience),
    )

    st.session_state.condition_assignment_mode = st.sidebar.radio(
        "Condition assignment",
        ["manual", "random"],
        index=0 if st.session_state.condition_assignment_mode == "manual" else 1,
        horizontal=True,
    )

    condition_keys = list(CONDITIONS.keys())
    current_condition = st.session_state.condition_key or condition_keys[0]
    st.session_state.condition_key = st.sidebar.selectbox(
        "Condition",
        condition_keys,
        index=condition_keys.index(current_condition),
        disabled=st.session_state.condition_assignment_mode == "random",
    )

    max_trials = max(1, min(3, len(scenarios)))
    default_trials = min(st.session_state.num_trials or 1, max_trials)
    if max_trials == 1:
        st.session_state.num_trials = 1
        st.sidebar.caption("Number of scenarios: 1 (Appendix B prototype)")
    else:
        st.session_state.num_trials = st.sidebar.slider(
            "Number of scenarios",
            1,
            max_trials,
            default_trials,
        )

    st.sidebar.markdown("---")
    if st.sidebar.button("Start New Session", type="primary", use_container_width=True):
        if not st.session_state.participant_id.strip():
            st.sidebar.error("Enter a participant ID first.")
        else:
            start_session(scenarios)
            st.rerun()



def render_study_header() -> None:
    participant_value = st.session_state.participant_id or "STANDBY"
    condition_value = st.session_state.condition_key or "Awaiting start"
    group_value = current_subject_group() if st.session_state.session_started else "Pending assignment"
    trial_value = f"{current_trial_number()}/{total_trials()}" if st.session_state.session_started else "0/0"

    st.markdown(
        f"""
        <div class="hf-masthead">
            <div class="hf-masthead-eyebrow">GNC Recovery Testbed</div>
            <div class="hf-masthead-title">Navigation Fault Recovery Experiment</div>
            <div class="hf-masthead-subtitle">
                Appendix B prototype for comparing linear and branching checklist designs under time pressure.
                The interface is styled as a compact mission-control board while preserving the study flow.
            </div>
            <div class="hf-chip-row">
                <div class="hf-chip hf-chip-blue">
                    <div class="hf-chip-label">Participant</div>
                    <div class="hf-chip-value">{escape_text(participant_value)}</div>
                </div>
                <div class="hf-chip hf-chip-amber">
                    <div class="hf-chip-label">Condition</div>
                    <div class="hf-chip-value">{escape_text(condition_value)}</div>
                </div>
                <div class="hf-chip hf-chip-green">
                    <div class="hf-chip-label">Group</div>
                    <div class="hf-chip-value">{escape_text(group_value)}</div>
                </div>
                <div class="hf-chip hf-chip-red">
                    <div class="hf-chip-label">Trial</div>
                    <div class="hf-chip-value">{escape_text(trial_value)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_instructions() -> None:
    render_notice(
        "Use the sidebar to enter a participant ID and start a session. "
        "This prototype uses the Appendix B navigation fault recovery scenario. "
        "Linear runs use the fixed procedure; branching runs require mode, cause, recovery, and final-mode verification gates.",
        "info",
    )



def render_console() -> None:
    scenario = st.session_state.scenario
    render_panel_heading(
        "Spacecraft Console",
        "NAV-CONSOLE",
        "Live anomaly state, spacecraft mode, timing, and operator action matrix.",
    )

    render_telemetry_row(
        [
            {
                "label": "Current Mode",
                "value": st.session_state.mode,
                "tone": "blue",
                "note": "Displayed spacecraft control mode",
            },
            {
                "label": "Target Mode",
                "value": scenario["correct_mode"],
                "tone": "green",
                "note": "Desired end state after recovery",
            },
            {
                "label": "Auto Transition",
                "value": f"{scenario['auto_transition']['new_mode']} @ {scenario['auto_transition']['time']} s",
                "tone": "amber",
                "note": "Automatic fault response trigger",
            },
            {
                "label": "Subject Group",
                "value": current_subject_group(),
                "tone": "cyan",
                "note": "Analysis partition for exports",
            },
        ]
    )

    render_mode_badge(st.session_state.mode)

    st.markdown(
        f"""
        <div class="hf-fault">
            <div class="hf-fault-label">Fault Channel</div>
            <div class="hf-fault-value">{escape_text(scenario['fault'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_telemetry_row(
        [
            {
                "label": "Checklist Type",
                "value": checklist_type().upper(),
                "tone": "cyan",
                "note": "Assigned procedure architecture",
            },
            {
                "label": "Time Limit",
                "value": f"{current_time_limit()} s",
                "tone": "amber",
                "note": "Urgency condition timer",
            },
            {
                "label": "Wrong-Mode Actions",
                "value": str(st.session_state.wrong_mode_actions),
                "tone": "red",
                "note": "Actions inconsistent with expected mode",
            },
        ]
    )

    render_notice(
        f"Reason cue // {scenario.get('transition_reason', 'Not shown')}",
        "info",
    )
    render_timer(remaining_time(), current_time_limit())

    render_panel_heading(
        "Action Matrix",
        "EXECUTE",
        "Select the next operator action. Disabled controls indicate checklist or mode gating.",
    )
    allowed_actions = scenario.get("allowed_actions", [])

    if checklist_type() == "branching" and not st.session_state.branch_gate_open:
        render_notice(
            "Recovery actions unlock after the mode and transition-cause checks are completed.",
            "warn",
        )

    if checklist_type() == "branching" and st.session_state.branch_gate_open and not st.session_state.recovery_verified:
        render_notice(
            "Run the recovery actions, then complete the navigation-data verification step in the checklist.",
            "info",
        )

    if checklist_type() == "branching" and st.session_state.recovery_verified and not st.session_state.final_mode_verified:
        render_notice(
            "Complete the intended-final-mode check before the final AUTO recovery actions.",
            "info",
        )

    if checklist_type() == "linear":
        render_notice("Linear condition // complete the displayed checklist steps in order.", "info")

    cols = st.columns(2)
    for i, action in enumerate(allowed_actions):
        with cols[i % 2]:
            if st.button(action, use_container_width=True, disabled=action_disabled(action)):
                execute_action(action)
                st.rerun()
            render_action_help(ACTION_HELP.get(action, ""))



def render_linear_checklist() -> None:
    scenario = st.session_state.scenario
    render_panel_heading(
        "Linear Checklist",
        "SEQ-LINEAR",
        "Appendix B fixed-sequence navigation fault recovery procedure.",
    )

    expected = current_expected_step()

    render_telemetry_row(
        [
            {
                "label": "Next Required Step",
                "value": expected or "Procedure complete",
                "tone": "blue",
                "note": "Current fixed-sequence checkpoint",
            },
            {
                "label": "Order Errors",
                "value": str(st.session_state.order_errors),
                "tone": "red",
                "note": "Out-of-sequence attempts recorded",
            },
        ]
    )

    for i, step in enumerate(scenario["linear_actions"], start=1):
        done = step in st.session_state.completed_actions

        if done:
            css_class = "hf-step-done"
            label = f"STEP {i:02d} // {step}"
        elif step == expected:
            css_class = "hf-step-current"
            label = f"STEP {i:02d} // {step}"
        else:
            css_class = "hf-step-upcoming"
            label = f"STEP {i:02d} // {step}"

        st.markdown(f'<div class="{css_class}">{label}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="hf-inline-stat">ORDER ERRORS // {st.session_state.order_errors}</div>',
        unsafe_allow_html=True,
    )



def render_branching_checklist() -> None:
    scenario = st.session_state.scenario
    render_panel_heading(
        "Branching Checklist",
        "SEQ-BRANCH",
        "Appendix B branching recovery procedure with explicit verification checkpoints.",
    )

    unique_modes = list(dict.fromkeys([
        scenario["initial_mode"],
        scenario["expected_transition_mode"],
        scenario["correct_mode"],
        "MANUAL",
        "SAFE",
        "HOLD",
        "NOMINAL",
    ]))

    render_telemetry_row(
        [
            {
                "label": "Mode Check",
                "value": "Verified" if st.session_state.mode_verified else "Pending",
                "tone": "blue",
                "note": f"Errors: {st.session_state.mode_check_errors}",
            },
            {
                "label": "Fault Check",
                "value": "Verified" if st.session_state.diagnosis_verified else "Pending",
                "tone": "amber",
                "note": f"Errors: {st.session_state.diagnosis_errors}",
            },
            {
                "label": "Recovery Check",
                "value": "Verified" if st.session_state.recovery_verified else "Pending",
                "tone": "green",
                "note": f"Errors: {st.session_state.recovery_check_errors}",
            },
            {
                "label": "Final Mode Check",
                "value": "Verified" if st.session_state.final_mode_verified else "Pending",
                "tone": "cyan",
                "note": f"Errors: {st.session_state.final_mode_check_errors}",
            },
        ]
    )

    render_section_header("Step 1", "Acknowledge alarm and open status panel")
    for action in scenario["branch_opening_actions"]:
        done = action in st.session_state.completed_actions
        css_class = "hf-step-done" if done else "hf-step-current"
        st.markdown(f'<div class="{css_class}">OPENING // {escape_text(action)}</div>', unsafe_allow_html=True)

    render_section_header("Step 2", "Verify current spacecraft mode")
    mode_guess = st.radio("Select current mode", unique_modes, key="mode_guess")
    if st.button(
        "Submit Mode Check",
        use_container_width=True,
        disabled=not completed_all(scenario["branch_opening_actions"]),
    ):
        submit_mode_check(mode_guess)
        st.rerun()

    render_section_header("Step 3", "Confirm reason for transition")
    diagnosis_guess = st.radio(
        scenario["diagnosis_prompt"],
        scenario["diagnosis_options"],
        key="diagnosis_guess",
    )
    if st.button(
        "Submit Diagnosis",
        use_container_width=True,
        disabled=not st.session_state.mode_verified,
    ):
        submit_diagnosis(diagnosis_guess)
        st.rerun()

    render_section_header("Step 4", "Stabilize affected subsystem")
    for action in scenario["branch_recovery_actions"]:
        done = action in st.session_state.completed_actions
        css_class = "hf-step-done" if done else "hf-step-current"
        st.markdown(f'<div class="{css_class}">RECOVERY // {escape_text(action)}</div>', unsafe_allow_html=True)

    render_section_header("Step 5", "Confirm recovery conditions")
    recovery_guess = st.radio(
        "Is navigation data restored and valid?",
        ["Yes", "No"],
        key="recovery_guess",
    )
    if st.button(
        "Submit Recovery Check",
        use_container_width=True,
        disabled=not completed_all(scenario["branch_recovery_actions"]),
    ):
        submit_recovery_check(recovery_guess)
        st.rerun()

    render_section_header("Step 6", "Verify intended final mode")
    final_mode_guess = st.radio(
        "Select intended recovery mode",
        ["AUTO", "HOLD", "SAFE", "MANUAL"],
        key="final_mode_guess",
    )
    if st.button(
        "Submit Final Mode Check",
        use_container_width=True,
        disabled=not st.session_state.recovery_verified,
    ):
        submit_final_mode_check(final_mode_guess)
        st.rerun()

    render_section_header("Step 7", "Confirm outcome")
    for action in scenario["branch_final_actions"]:
        done = action in st.session_state.completed_actions
        css_class = "hf-step-done" if done else "hf-step-current"
        st.markdown(f'<div class="{css_class}">OUTCOME // {escape_text(action)}</div>', unsafe_allow_html=True)

    render_section_header("Verification Wall", "Branch status summary")
    st.markdown(
        f'<div class="{"hf-step-done" if st.session_state.mode_verified else "hf-step-upcoming"}">'
        f'MODE CHECK // Current mode confirmed as HOLD'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="{"hf-step-done" if st.session_state.diagnosis_verified else "hf-step-upcoming"}">'
        f'FAULT CHECK // Transition cause confirmed'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="{"hf-step-done" if st.session_state.recovery_verified else "hf-step-upcoming"}">'
        f'RECOVERY CHECK // Navigation data restored and valid'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="{"hf-step-done" if st.session_state.final_mode_verified else "hf-step-upcoming"}">'
        f'FINAL MODE CHECK // Intended final mode verified as AUTO'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.recovery_verified and st.session_state.final_mode_verified:
        render_notice(
            "Final recovery branch unlocked. Complete the AUTO restoration steps in the console.",
            "success",
        )
    elif st.session_state.branch_gate_open:
        render_notice(
            "Recovery branch unlocked. Complete the subsystem recovery actions in the console.",
            "success",
        )
    else:
        render_notice(
            "Recovery actions stay disabled until the early verification steps are correct.",
            "warn",
        )



def render_post_run_survey() -> None:
    render_panel_heading(
        "Post-Run Workload Survey",
        "NASA-TLX",
        "Capture subjective workload after the navigation fault recovery run.",
    )
    st.session_state.nasa_tlx_mental = st.slider("Mental Demand", 1, 10, 5)
    st.session_state.nasa_tlx_temporal = st.slider("Temporal Demand", 1, 10, 5)
    st.session_state.nasa_tlx_effort = st.slider("Effort", 1, 10, 5)
    st.session_state.nasa_tlx_frustration = st.slider("Frustration", 1, 10, 5)

    if st.button("Submit Survey", use_container_width=True):
        st.session_state.survey_submitted = True
        log_event("SURVEY SUBMITTED")
        st.rerun()

    if st.session_state.survey_submitted:
        okay, message = can_finish_trial()
        if not okay and remaining_time() > 0:
            render_notice(message, "info")
        else:
            if st.button("Finish Trial", type="primary", use_container_width=True):
                finish_trial(timeout=remaining_time() <= 0)
                st.rerun()



def render_summary() -> None:
    s = st.session_state.summary
    render_panel_heading(
        "Trial Summary",
        "POST-RUN",
        "Run complete. Review key performance metrics before advancing or exporting data.",
    )
    render_notice("Trial complete", "success")
    render_telemetry_row(
        [
            {
                "label": "Group",
                "value": s["subject_group"],
                "tone": "cyan",
                "note": "Current export partition",
            },
            {
                "label": "Completion Time",
                "value": f"{s['completion_time_s']} s",
                "tone": "blue",
                "note": "Elapsed scenario time",
            },
            {
                "label": "Wrong-Mode Actions",
                "value": str(s["wrong_mode_actions"]),
                "tone": "red",
                "note": "Mode-inconsistent actions",
            },
            {
                "label": "Step Omissions",
                "value": str(s["step_omissions"]),
                "tone": "amber",
                "note": "Required steps not completed",
            },
        ]
    )
    render_telemetry_row(
        [
            {
                "label": "Order Errors",
                "value": str(s["order_errors"]),
                "tone": "red",
                "note": "Linear sequence deviations",
            },
            {
                "label": "Mode Check Errors",
                "value": str(s["mode_check_errors"]),
                "tone": "blue",
                "note": "Branch verification misses",
            },
            {
                "label": "Diagnosis Errors",
                "value": str(s["diagnosis_errors"]),
                "tone": "amber",
                "note": "Fault-cause verification misses",
            },
            {
                "label": "Recovery / Final Errors",
                "value": f"{s['recovery_check_errors']} / {s['final_mode_check_errors']}",
                "tone": "green",
                "note": "Late-branch verification misses",
            },
        ]
    )
    render_notice(
        f"Completed all required steps // {s['completed_all_required']}. Data sink // {st.session_state.data_sink}",
        "info",
    )
    st.caption(f"Data saved to: {st.session_state.data_sink}")

    if current_trial_number() < total_trials():
        if st.button("Start Next Trial", type="primary"):
            st.session_state.trial_index += 1
            load_current_trial()
            st.rerun()
    else:
        st.balloons()
        render_notice("Session complete. You can export or analyze your logged data.", "success")


st.set_page_config(page_title="Navigation Fault Recovery Experiment", layout="wide")
init_state()
inject_styles()
all_scenarios = load_scenarios()

render_sidebar_setup(all_scenarios)
render_study_header()

if not st.session_state.session_started:
    render_instructions()
    st.stop()

maybe_auto_transition()

if remaining_time() <= 0 and not st.session_state.finished:
    render_notice("Time expired. Submit the workload survey, then finish the trial.", "danger")

left, right = st.columns([1.2, 1])
with left:
    render_console()
with right:
    if checklist_type() == "linear":
        render_linear_checklist()
    else:
        render_branching_checklist()

if not st.session_state.finished:
    render_post_run_survey()
else:
    render_summary()
