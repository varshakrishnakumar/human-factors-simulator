"""The only place in sim/ that directly reads or writes st.session_state for
identity/session bookkeeping. Every other module in sim/ works through either
the pure domain engine or the typed accessors in trial.py — nothing else should
be calling st.session_state directly for these keys.

I split state into two dataclasses so it's obvious which values are fixed for
the whole session (IdentityState) versus which can change as the session
progresses (SessionState). That distinction matters when you're debugging data:
identity fields should be identical across every row for a participant; session
fields describe where they are in the flow."""
from dataclasses import asdict, dataclass, field
from typing import List, Literal, Optional

import streamlit as st


@dataclass
class IdentityState:
    """Participant-level constants set at session start and never mutated again.
    These map directly onto the columns we need in every output row, so I kept
    them together here rather than scattering them across trial.py."""
    participant_id: str = ""
    experience: str = "None"
    condition_key: Optional[str] = None
    assignment_mode: Literal["auto", "manual"] = "auto"
    session_id: Optional[str] = None


@dataclass
class SessionState:
    """Mutable navigation state: where we are in the trial sequence, which
    summaries have been collected, and whether we're in the fam / survey phase.
    I keep this separate from IdentityState so trial.py can call session()
    cheaply to check flow without pulling in identity fields it doesn't need."""
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
    """Snapshot the relevant session keys out of st.session_state into a typed
    dataclass. Callers get plain Python values — no st.session_state references
    leak out — which makes the flow logic in simulator.py and trial.py easier to
    read and unit-test."""
    return SessionState(**{k: st.session_state[k] for k in _SESSION_KEYS})


def reset_trial_state() -> None:
    """Clear engine + dynamic widget keys. Called at trial transitions."""
    st.session_state["trial_engine"] = None
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and (key.startswith("branch_decision_") or key.startswith("checklist_pick_")):
            del st.session_state[key]
