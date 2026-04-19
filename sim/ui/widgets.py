import html
from typing import Any, Dict, List

import streamlit as st


MODE_COLORS = {
    "AUTO": "#1565c0",
    "NOMINAL": "#2e7d32",
    "HOLD": "#ef6c00",
    "SAFE": "#c62828",
    "MANUAL": "#455a64",
}
MODE_GLOWS = {
    "AUTO": "rgba(21, 101, 192, 0.42)",
    "NOMINAL": "rgba(46, 125, 50, 0.36)",
    "HOLD": "rgba(239, 108, 0, 0.34)",
    "SAFE": "rgba(198, 40, 40, 0.36)",
    "MANUAL": "rgba(69, 90, 100, 0.3)",
}


def esc(value: Any) -> str:
    return html.escape(str(value))


def mode_color(mode: str) -> str:
    return MODE_COLORS.get(mode, "#424242")


def mode_glow(mode: str) -> str:
    return MODE_GLOWS.get(mode, "rgba(148, 163, 184, 0.24)")


def render_notice(message: str, tone: str = "info") -> None:
    st.markdown(
        f'<div class="hf-notice hf-notice-{esc(tone)}">{esc(message)}</div>',
        unsafe_allow_html=True,
    )


def render_section_header(kicker: str, title: str) -> None:
    st.markdown(
        f'<div class="hf-section-header">'
        f'<div class="hf-section-kicker">{esc(kicker)}</div>'
        f'<div class="hf-section-title">{esc(title)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_mode_badge(mode: str) -> None:
    st.markdown(
        f'<div class="hf-mode-shell">'
        f'<div class="hf-mode-label">Spacecraft Mode</div>'
        f'<div class="hf-mode-value" style="--mode-color:{mode_color(mode)};'
        f' --mode-glow:{mode_glow(mode)};">{esc(mode)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_fault(fault: str) -> None:
    st.markdown(
        f'<div class="hf-fault">'
        f'<div class="hf-fault-label">Fault</div>'
        f'<div class="hf-fault-value">{esc(fault)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_trigger_cues(cues: List[Dict[str, str]]) -> None:
    if not cues:
        return
    inner = "".join(
        f'<div class="hf-cue">'
        f'<div class="hf-cue-label">{esc(c["label"])}</div>'
        f'<div class="hf-cue-value">{esc(c["value"])}</div>'
        f'</div>'
        for c in cues
    )
    st.markdown(f'<div class="hf-cues">{inner}</div>', unsafe_allow_html=True)


def render_live_timer(remaining: float, total: int) -> None:
    total_safe = max(total, 1)
    frac = max(0.0, min(1.0, remaining / total_safe))
    if remaining <= 10:
        color = "var(--hf-red)"
    elif remaining <= 20:
        color = "var(--hf-amber)"
    else:
        color = "var(--hf-blue)"
    st.markdown(
        f'<div style="--timer-color:{color};">'
        f'<div class="hf-timer">'
        f'<div class="hf-timer-label">Time Remaining</div>'
        f'<div class="hf-timer-value">{int(remaining):d}s</div>'
        f'</div>'
        f'<div class="hf-timer-bar">'
        f'<div class="hf-timer-bar-fill" style="width:{frac*100:.1f}%;"></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_action_help(text: str) -> None:
    st.markdown(
        f'<div class="hf-action-help">{esc(text)}</div>',
        unsafe_allow_html=True,
    )


def render_rocket_celebration() -> None:
    st.markdown(
        '<div class="hf-rocket-stage">'
        '<div class="hf-rocket">🚀</div>'
        '<div class="hf-rocket">🚀</div>'
        '<div class="hf-rocket">🚀</div>'
        '<div class="hf-rocket">🚀</div>'
        '<div class="hf-rocket">🚀</div>'
        '</div>',
        unsafe_allow_html=True,
    )
