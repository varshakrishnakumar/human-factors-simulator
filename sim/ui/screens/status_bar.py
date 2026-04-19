"""Sticky in-trial status bar showing time remaining, spacecraft mode, and
active fault. Renders at the top of the console layout only while a trial is
running. The colour coding (blue/amber/red) for the timer lives here; the same
thresholds are used in widgets.render_live_timer() for consistency."""
from sim.trial import current_mode, current_scenario, current_time_limit, in_familiarization, remaining_time, trial_started
from sim.ui.widgets import esc, mode_color, mode_glow

import streamlit as st


def render() -> None:
    scenario = current_scenario()
    if not scenario or not trial_started():
        return
    if in_familiarization():
        timer_html = ('<div class="hf-statusbar-cell"><div class="hf-statusbar-label">PRACTICE</div>'
                      '<div class="hf-statusbar-value" style="color:var(--hf-green);">No timer</div></div>')
    else:
        rem = int(remaining_time())
        total = max(current_time_limit(), 1)
        frac = max(0.0, min(1.0, rem / total))
        if rem <= 10:
            tcolor = "var(--hf-red)"
        elif rem <= 20:
            tcolor = "var(--hf-amber)"
        else:
            tcolor = "var(--hf-blue)"
        timer_html = (
            f'<div class="hf-statusbar-cell">'
            f'<div class="hf-statusbar-label">Time Remaining</div>'
            f'<div class="hf-statusbar-value" style="color:{tcolor};">{rem}s</div>'
            f'<div class="hf-timer-bar"><div class="hf-timer-bar-fill" style="--timer-color:{tcolor}; width:{frac*100:.1f}%;"></div></div>'
            f'</div>'
        )

    mode = current_mode() or "—"
    mode_html = (
        f'<div class="hf-statusbar-cell">'
        f'<div class="hf-statusbar-label">Mode</div>'
        f'<div class="hf-statusbar-value" '
        f'style="background:{mode_color(mode)}; color:white; padding:0.25rem 0.6rem; border-radius:8px;'
        f' box-shadow:0 0 18px {mode_glow(mode)}; display:inline-block;">{esc(mode)}</div>'
        f'</div>'
    )

    fault_html = (
        f'<div class="hf-statusbar-cell hf-statusbar-fault">'
        f'<div class="hf-statusbar-label">Fault</div>'
        f'<div class="hf-statusbar-value" style="font-size:0.95rem;">{esc(scenario.fault)}</div>'
        f'</div>'
    )

    st.markdown(
        f'<div class="hf-statusbar">{timer_html}{mode_html}{fault_html}</div>',
        unsafe_allow_html=True,
    )
