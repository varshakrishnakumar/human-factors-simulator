import streamlit as st


_DEFAULTS = {
    # Identity
    "participant_id": "",
    "experience": "None",
    "session_started": False,
    "session_id": None,
    "condition_assignment_mode": "auto",  # "auto" (balanced) or "manual"
    "condition_key": None,
    # Trial flow
    "trial_order": [],
    "trial_index": 0,
    "did_familiarization": False,
    "in_familiarization": False,
    "scenario": None,
    "trial_started": False,
    "start_time": None,
    "completion_time": None,
    "end_reason": None,
    # Per-trial
    "mode": None,
    "completed_actions": [],
    "wrong_mode_actions": 0,
    "order_errors": 0,
    "selected_checklist_id": None,
    "checklist_selection_error": False,
    "branch_step_id": 1,
    "branch_path": [],
    "branch_decision_errors": 0,
    "finished": False,
    "summary": None,
    "trial_event_rows": [],
    # Session-end
    "all_summaries": [],
    "session_survey_submitted": False,
    "session_finished": False,
    "data_sink": None,
}


_TRIAL_RESET_KEYS = {
    "mode": None,
    "completed_actions": [],
    "wrong_mode_actions": 0,
    "order_errors": 0,
    "selected_checklist_id": None,
    "checklist_selection_error": False,
    "branch_step_id": 1,
    "branch_path": [],
    "branch_decision_errors": 0,
    "finished": False,
    "summary": None,
    "trial_event_rows": [],
    "trial_started": False,
    "start_time": None,
    "completion_time": None,
    "end_reason": None,
}


def init_state() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_trial_state() -> None:
    for key, value in _TRIAL_RESET_KEYS.items():
        if isinstance(value, list):
            st.session_state[key] = []
        else:
            st.session_state[key] = value
    for key in list(st.session_state.keys()):
        if key.startswith("branch_decision_") or key.startswith("checklist_pick_"):
            del st.session_state[key]
