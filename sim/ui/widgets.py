"""Streamlit rendering primitives shared across screen files. Nothing in here
touches the engine or session_state — it's just HTML generators and a couple
of color-lookup helpers. If you need a new reusable component that renders
HTML (a badge, a card, a progress indicator), this is where it lives."""
import html
from typing import Any

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

_CUE_DANGER_VALUES = {
    "FAILED",
    "INVALID",
    "LOST",
    "OVERTEMP",
    "VALVE FAULT",
    "SAFE",
}
_CUE_WARN_VALUES = {
    "HOLD",
    "DEGRADED",
    "RESETTING",
    "CYCLED",
    "BACKUP",
}
_CUE_OK_VALUES = {
    "AUTO",
    "ACKNOWLEDGED",
    "NOMINAL",
    "VALID",
    "STABLE",
    "ACTIVE",
    "OK",
    "OPEN",
}


def esc(value: Any) -> str:
    return html.escape(str(value))


def mode_color(mode: str) -> str:
    return MODE_COLORS.get(mode, "#424242")


def mode_glow(mode: str) -> str:
    return MODE_GLOWS.get(mode, "rgba(148, 163, 184, 0.24)")


def cue_tone(value: str) -> str:
    """Map cue values to display status without coloring the whole panel."""
    normalized = str(value).strip().upper()
    if normalized in _CUE_DANGER_VALUES:
        return "danger"
    if normalized in _CUE_WARN_VALUES:
        return "warn"
    if normalized in _CUE_OK_VALUES:
        return "ok"
    return "neutral"


def render_notice(message: str, tone: str = "info") -> None:
    """Render a styled notice banner. `tone` maps to CSS classes:
    info (blue), warn (amber), success (green), danger (red)."""
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


def render_trigger_cues(cues) -> None:
    if not cues:
        return
    inner = "".join(
        f'<div class="hf-cue hf-cue-{cue_tone(c.value)}">'
        f'<div class="hf-cue-label">{esc(c.label)}</div>'
        f'<div class="hf-cue-value">{esc(c.value)}</div>'
        f'</div>'
        for c in cues
    )
    st.markdown(f'<div class="hf-cues">{inner}</div>', unsafe_allow_html=True)


def render_live_timer(remaining: float, total: int) -> None:
    """Render the countdown timer with a colour-coded fill bar. Red below 10s,
    amber below 20s, blue otherwise. Not used by the current status_bar (which
    inlines the same logic), but kept here for any screen that wants a
    standalone timer block."""
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


def render_practice_checklist(scenario) -> None:
    """Sandbox checklist shown during familiarization, regardless of condition."""
    from sim.trial import completed_actions
    render_section_header("Sandbox", "Practice the console/checklist loop")
    render_notice(
        "Trial 0 is a sandbox. Follow the example checklist by pressing the matching "
        "console buttons. No timer, no scoring, and no real-trial summary row.",
        "info",
    )
    done = completed_actions()
    expected_step = next((s for s in scenario.linear_checklist.steps if s not in done), None)
    for i, step in enumerate(scenario.linear_checklist.steps, start=1):
        if step in done:
            css = "hf-step-done"
        elif step == expected_step:
            css = "hf-step-current"
        else:
            css = "hf-step-upcoming"
        expected_mode = scenario.action_expected_modes.get(step)
        mode_html = (
            f'<span class="hf-step-mode">Mode {esc(expected_mode)}</span>'
            if expected_mode else ""
        )
        st.markdown(
            f'<div class="{css}">STEP {i:02d} // {esc(step)}{mode_html}</div>',
            unsafe_allow_html=True,
        )
