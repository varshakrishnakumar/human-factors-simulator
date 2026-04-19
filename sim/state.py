"""Phase-scoped state bridge between Streamlit session_state and domain."""
from dataclasses import asdict, dataclass, field
from typing import List, Literal, Optional

import streamlit as st


@dataclass
class IdentityState:
    participant_id: str = ""
    experience: str = "None"
    condition_key: Optional[str] = None
    assignment_mode: Literal["auto", "manual"] = "auto"
    session_id: Optional[str] = None


@dataclass
class SessionState:
    session_started: bool = False
    trial_order: List[int] = field(default_factory=list)
    trial_index: int = 0
    did_familiarization: bool = False
    in_familiarization: bool = False
    all_summaries: List[dict] = field(default_factory=list)
    session_finished: bool = False
    session_survey_submitted: bool = False
    data_sink: Optional[str] = None


_SESSION_KEYS = {f.name for f in SessionState.__dataclass_fields__.values()}


def init_state() -> None:
    """Install default values for every session/identity field if missing.
    Widget-state keys (tlx_*, branch_decision_*, checklist_pick_*) are managed
    by Streamlit itself and not touched here."""
    defaults = {**asdict(IdentityState()), **asdict(SessionState())}
    # condition_assignment_mode is the legacy UI key used by sidebar.py; map from
    # IdentityState.assignment_mode so both names stay consistent.
    defaults["condition_assignment_mode"] = defaults.pop("assignment_mode")
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def session() -> SessionState:
    return SessionState(**{k: st.session_state[k] for k in _SESSION_KEYS})


def reset_trial_state() -> None:
    """Clear engine + dynamic widget keys. Called at trial transitions."""
    st.session_state["trial_engine"] = None
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and (key.startswith("branch_decision_") or key.startswith("checklist_pick_")):
            del st.session_state[key]
