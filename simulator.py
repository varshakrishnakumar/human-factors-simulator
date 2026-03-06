import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


SCENARIO_DIR = Path("scenarios")
EVENT_LOG = Path("event_log.csv")
SUMMARY_LOG = Path("summary_log.csv")

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
    "ACK ALARM": "Acknowledge the annunciated fault.",
    "ENTER HOLD MODE": "Command the spacecraft into HOLD.",
    "ENTER SAFE MODE": "Command the spacecraft into SAFE.",
    "RESET NAVIGATION": "Reset or reinitialize navigation.",
    "ISOLATE ACS": "Isolate the attitude control subsystem.",
    "CYCLE SENSOR BUS": "Reset the thermal sensor bus.",
    "SWITCH TO MANUAL": "Manual override (usually not correct).",
    "WAIT / MONITOR": "Wait for auto-transition while monitoring status.",
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
        "title": "Relative navigation degraded",
        "initial_mode": "AUTO_APPROACH",
        "fault": "Relative navigation degraded",
        "transition_reason": "Navigation confidence dropped below threshold",
        "auto_transition": {"time": 10, "new_mode": "HOLD"},
        "correct_mode": "HOLD",
        "diagnosis_prompt": "Why did the spacecraft leave AUTO_APPROACH?",
        "diagnosis_options": [
            "Navigation degraded",
            "Power bus reset",
            "Thermal runaway",
        ],
        "correct_diagnosis": "Navigation degraded",
        "correct_actions": ["ACK ALARM", "ENTER HOLD MODE", "RESET NAVIGATION"],
        "allowed_actions": [
            "ACK ALARM",
            "ENTER HOLD MODE",
            "RESET NAVIGATION",
            "SWITCH TO MANUAL",
            "WAIT / MONITOR",
        ],
    },
    {
        "scenario_id": 2,
        "title": "Attitude control instability",
        "initial_mode": "NOMINAL",
        "fault": "Attitude controller saturation",
        "transition_reason": "Attitude error exceeded safe threshold",
        "auto_transition": {"time": 8, "new_mode": "SAFE"},
        "correct_mode": "SAFE",
        "diagnosis_prompt": "Why did the spacecraft leave NOMINAL?",
        "diagnosis_options": [
            "Attitude control instability",
            "Navigation degraded",
            "Comms dropout",
        ],
        "correct_diagnosis": "Attitude control instability",
        "correct_actions": ["ACK ALARM", "ENTER SAFE MODE", "ISOLATE ACS"],
        "allowed_actions": [
            "ACK ALARM",
            "ENTER SAFE MODE",
            "ISOLATE ACS",
            "SWITCH TO MANUAL",
            "WAIT / MONITOR",
        ],
    },
    {
        "scenario_id": 3,
        "title": "Thermal sensor disagreement",
        "initial_mode": "AUTO_THERMAL",
        "fault": "Thermal sensor disagreement",
        "transition_reason": "Sensor disagreement triggered protective hold",
        "auto_transition": {"time": 12, "new_mode": "HOLD"},
        "correct_mode": "HOLD",
        "diagnosis_prompt": "Why did the spacecraft leave AUTO_THERMAL?",
        "diagnosis_options": [
            "Thermal sensor disagreement",
            "Fuel leak",
            "Star tracker dropout",
        ],
        "correct_diagnosis": "Thermal sensor disagreement",
        "correct_actions": ["ACK ALARM", "ENTER HOLD MODE", "CYCLE SENSOR BUS"],
        "allowed_actions": [
            "ACK ALARM",
            "ENTER HOLD MODE",
            "CYCLE SENSOR BUS",
            "SWITCH TO MANUAL",
            "WAIT / MONITOR",
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
            scenarios.append(json.load(f))
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

    headers = list(rows[0].keys())
    existing_headers = target_ws.row_values(1)
    if existing_headers != headers:
        target_ws.clear()
        target_ws.append_row(headers)

    values = [[row.get(col, "") for col in headers] for row in rows]
    target_ws.append_rows(values, value_input_option="USER_ENTERED")
    return True



def append_rows_local(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header)



def persist_rows(kind: str, rows: List[Dict[str, Any]], local_path: Path) -> str:
    ok = append_rows_to_google_sheet(kind, rows)
    if ok:
        return "google_sheets"
    append_rows_local(local_path, rows)
    return "local_csv"


def init_state() -> None:
    defaults = {
        "participant_id": "",
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
    ]:
        if key in st.session_state:
            del st.session_state[key]



def start_session(scenarios: List[Dict[str, Any]]) -> None:
    st.session_state.session_started = True
    st.session_state.session_id = f"S{int(time.time())}"

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


def log_event(action: str, extra: Optional[Dict[str, Any]] = None) -> None:
    row = {
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
        "condition": st.session_state.condition_key,
        "checklist_type": checklist_type() if st.session_state.condition_key else None,
        "trial_number": current_trial_number() if st.session_state.session_started else None,
        "scenario_id": st.session_state.scenario["scenario_id"] if st.session_state.scenario else None,
        "timestamp_s": round(elapsed_time(), 3),
        "mode": st.session_state.mode,
        "action": action,
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
    scenario = st.session_state.scenario
    for step in scenario["correct_actions"]:
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
    correct_mode = scenario["correct_mode"]
    correct_actions = scenario["correct_actions"]
    checklist = checklist_type()

    # Branching condition gate: block recovery actions until mode and diagnosis are verified.
    if checklist == "branching" and action in correct_actions:
        if not st.session_state.branch_gate_open:
            log_event("BLOCKED ACTION", {"attempted_action": action, "reason": "branch_gate_closed"})
            st.warning("Complete mode verification and diagnosis before recovery actions.")
            return

    in_required_actions = action in correct_actions
    in_allowed_actions = action in scenario.get("allowed_actions", [])

    if not in_allowed_actions:
        log_event("UNAVAILABLE ACTION", {"attempted_action": action})
        st.error("That action is not available in this scenario.")
        return

    if checklist == "linear" and in_required_actions:
        in_order, expected = step_order_status(action)
        if not in_order:
            st.session_state.order_errors += 1
            log_event("ORDER ERROR", {"attempted_action": action, "expected_action": expected})

    wrong_mode = False
    if action in correct_actions[1:] and st.session_state.mode != correct_mode:
        st.session_state.wrong_mode_actions += 1
        wrong_mode = True

    if action not in st.session_state.completed_actions and in_required_actions:
        st.session_state.completed_actions.append(action)

    previous_mode = st.session_state.mode

    if action == "ENTER HOLD MODE":
        st.session_state.mode = "HOLD"
    elif action == "ENTER SAFE MODE":
        st.session_state.mode = "SAFE"
    elif action == "SWITCH TO MANUAL":
        st.session_state.mode = "MANUAL"

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
    correct = mode_guess == st.session_state.mode
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



def can_finish_trial() -> Tuple[bool, str]:
    scenario = st.session_state.scenario
    required = scenario["correct_actions"]
    missing = [a for a in required if a not in st.session_state.completed_actions]
    if missing and remaining_time() > 0:
        return False, "Complete the required procedure or let the timer expire before finishing."
    if not st.session_state.survey_submitted:
        return False, "Submit the workload survey first."
    return True, ""



def finish_trial(timeout: bool = False) -> None:
    if st.session_state.finished:
        return

    scenario = st.session_state.scenario
    required = scenario["correct_actions"]
    completed = st.session_state.completed_actions
    omissions = [a for a in required if a not in completed]
    extra_actions = [a for a in completed if a not in required]

    summary = {
        "session_id": st.session_state.session_id,
        "participant_id": st.session_state.participant_id,
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

    data_sink = persist_rows("events", st.session_state.trial_event_rows, EVENT_LOG)
    persist_rows("summaries", [summary], SUMMARY_LOG)
    st.session_state.data_sink = data_sink
    st.session_state.summary = summary
    st.session_state.finished = True


def render_sidebar_setup(scenarios: List[Dict[str, Any]]) -> None:
    st.sidebar.header("Experiment Setup")
    st.session_state.participant_id = st.sidebar.text_input(
        "Participant ID",
        value=st.session_state.participant_id,
        help="Required before starting the session.",
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

    st.session_state.num_trials = st.sidebar.slider("Number of scenarios", 1, min(3, len(scenarios)), 3)

    st.sidebar.markdown("---")
    if st.sidebar.button("Start New Session", type="primary", use_container_width=True):
        if not st.session_state.participant_id.strip():
            st.sidebar.error("Enter a participant ID first.")
        else:
            start_session(scenarios)
            st.rerun()



def render_study_header() -> None:
    st.title("Spacecraft Anomaly Response Experiment")
    st.caption("Study-ready prototype for comparing linear vs. branching checklist designs under time pressure.")

    if st.session_state.session_started:
        st.write(
            f"**Participant:** {st.session_state.participant_id}  \\n"
            f"**Condition:** {st.session_state.condition_key}  \\n"
            f"**Trial:** {current_trial_number()} / {total_trials()}"
        )



def render_instructions() -> None:
    st.info(
        "Use the sidebar to enter a participant ID and start a session. "
        "In the linear condition, follow the listed steps in order. "
        "In the branching condition, verify mode and diagnose the transition before recovery actions."
    )



def render_console() -> None:
    scenario = st.session_state.scenario
    st.subheader("Spacecraft Console")
    st.metric("Current Mode", st.session_state.mode)
    st.write(f"**Fault:** {scenario['fault']}")
    st.write(f"**Reason cue:** {scenario.get('transition_reason', 'Not shown')}")
    st.write(
        f"**Auto-transition:** {scenario['auto_transition']['new_mode']} at {scenario['auto_transition']['time']} s"
    )

    rem = remaining_time()
    if rem <= 10:
        st.error(f"Time Remaining: {int(rem)} s")
    else:
        st.info(f"Time Remaining: {int(rem)} s")

    st.write("### Available Actions")
    allowed_actions = st.session_state.scenario.get("allowed_actions", [])

    # Only show actions for the current scenario.
    cols = st.columns(2)
    for i, action in enumerate(allowed_actions):
        disabled = False
        if checklist_type() == "branching" and action in scenario["correct_actions"]:
            disabled = not st.session_state.branch_gate_open

        with cols[i % 2]:
            if st.button(action, use_container_width=True, disabled=disabled):
                execute_action(action)
                st.rerun()
            st.caption(ACTION_HELP.get(action, ""))



def render_linear_checklist() -> None:
    scenario = st.session_state.scenario
    st.subheader("Linear Checklist")
    st.caption("Fixed action sequence. No explicit verification step is required.")

    expected = current_expected_step()
    for i, step in enumerate(scenario["correct_actions"], start=1):
        done = step in st.session_state.completed_actions
        marker = "✅" if done else "➡️" if step == expected else "X"
        st.write(f"{marker} Step {i}: {step}")

    st.write(f"**Order errors:** {st.session_state.order_errors}")



def render_branching_checklist() -> None:
    scenario = st.session_state.scenario
    st.subheader("Branching Checklist")
    st.caption("Recovery actions are gated until mode and transition cause are verified.")

    unique_modes = list(dict.fromkeys([
        scenario["initial_mode"],
        scenario["correct_mode"],
        "MANUAL",
        "SAFE",
        "HOLD",
        "NOMINAL",
    ]))

    st.write("**Step 1: Verify current operating mode**")
    mode_guess = st.radio("Select current mode", unique_modes, key="mode_guess")
    if st.button("Submit Mode Check", use_container_width=True):
        submit_mode_check(mode_guess)
        st.rerun()

    st.write("**Step 2: Identify reason for transition**")
    diagnosis_guess = st.radio(
        scenario["diagnosis_prompt"],
        scenario["diagnosis_options"],
        key="diagnosis_guess",
    )
    if st.button("Submit Diagnosis", use_container_width=True):
        submit_diagnosis(diagnosis_guess)
        st.rerun()

    st.markdown("---")
    st.write(f"Mode verified: {'✅' if st.session_state.mode_verified else 'X'}")
    st.write(f"Diagnosis verified: {'✅' if st.session_state.diagnosis_verified else 'X'}")

    if st.session_state.branch_gate_open:
        st.success("Recovery branch unlocked. Proceed with the recovery actions below.")
        for action in scenario["correct_actions"]:
            done = "✅" if action in st.session_state.completed_actions else "X"
            st.write(f"{done} {action}")
    else:
        st.warning("Recovery actions stay disabled until both checks are correct.")



def render_post_run_survey() -> None:
    st.markdown("---")
    st.subheader("Post-Run Workload Survey")
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
            st.info(message)
        else:
            if st.button("Finish Trial", type="primary", use_container_width=True):
                finish_trial(timeout=remaining_time() <= 0)
                st.rerun()



def render_summary() -> None:
    s = st.session_state.summary
    st.success("Trial complete")
    st.write(f"**Completion time:** {s['completion_time_s']} s")
    st.write(f"**Wrong-mode actions:** {s['wrong_mode_actions']}")
    st.write(f"**Order errors:** {s['order_errors']}")
    st.write(f"**Mode-check errors:** {s['mode_check_errors']}")
    st.write(f"**Diagnosis errors:** {s['diagnosis_errors']}")
    st.write(f"**Step omissions:** {s['step_omissions']}")
    st.write(f"**Completed all required steps:** {s['completed_all_required']}")
    st.caption(f"Data saved to: {st.session_state.data_sink}")

    if current_trial_number() < total_trials():
        if st.button("Start Next Trial", type="primary"):
            st.session_state.trial_index += 1
            load_current_trial()
            st.rerun()
    else:
        st.balloons()
        st.info("Session complete. You can export or analyze your logged data.")



st.set_page_config(page_title="Checklist Design Experiment", layout="wide")
init_state()
all_scenarios = load_scenarios()

render_sidebar_setup(all_scenarios)
render_study_header()

if not st.session_state.session_started:
    render_instructions()
    st.stop()

maybe_auto_transition()

if remaining_time() <= 0 and not st.session_state.finished:
    st.error("Time expired. Submit the workload survey, then finish the trial.")

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
