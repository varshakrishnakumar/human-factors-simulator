"""Pre-session briefing screen. Shown before any session starts. If you need
to update participant instructions (study description, interface explanation,
consent language), this is the only file to edit."""
import streamlit as st

from sim.ui.widgets import render_notice


def render() -> None:
    render_notice(
        "Welcome. Before starting, please read the full briefing below. If any part is "
        "unclear, ask the study coordinator before clicking Start session.",
        "info",
    )
    st.markdown(
        """
        <div class="hf-brief">
        <h3>What this study is about</h3>
        <p>You will operate a simplified spacecraft console and recover the spacecraft
        from three injected faults. We are comparing two checklist styles (linear and
        branching) under two levels of time pressure.</p>

        <h3>How the session is structured</h3>
        <ol>
          <li><strong>Practice trial (Trial 0).</strong> One-button warm-up. No timer, no scoring.</li>
          <li><strong>Three recovery trials.</strong> Each trial injects one fault. A
          sticky timer at the top of the page shows how long you have.
          Trials end automatically when you reach the desired end state <em>or</em> when
          the timer hits zero — you do not need to click a "finish" button.</li>
          <li><strong>Workload survey.</strong> A single NASA-TLX questionnaire about the
          whole session. Full-sentence comments are welcome.</li>
        </ol>

        <h3>How to read the screen</h3>
        <ul>
          <li>The <strong>blue-bordered Console</strong> on the left shows the fault, the
          spacecraft's current mode, the trigger cues that are currently annunciating,
          and all available action buttons.</li>
          <li>The <strong>teal-bordered Checklist</strong> on the right shows the procedure
          you should be following. In linear trials you will see three candidate checklists
          and must pick the one that matches the trigger cues on the Console. In branching
          trials you will see one checklist with decision points — read each step carefully
          and choose the right branch.</li>
          <li>Action buttons are always enabled. Clicking a button out of order, or while
          the spacecraft is in the wrong mode, is logged as an error — so think before
          you click.</li>
        </ul>

        <h3>Display and seating</h3>
        <p>This interface is designed for a desktop or laptop monitor. If any critical
        information is cut off or requires scrolling, raise it with the coordinator so we
        can note it — the timer, mode, and fault should stay pinned at the top of the
        screen at all times.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_notice(
        "When you're ready: enter a Participant ID and Experience level in the sidebar, "
        "then click Start session.",
        "success",
    )
