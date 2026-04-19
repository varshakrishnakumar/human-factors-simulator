"""All CSS for the dark-themed simulator UI, injected once per rerun via
inject_styles(). Keeping styles in one place means UI visual changes don't
require touching any of the screen files."""
import streamlit as st


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
            --hf-console-accent: #5fb4ff;
            --hf-checklist-accent: #facc15;
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
        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1400px;
            padding-top: 0.6rem;
            padding-bottom: 1.5rem;
        }
        .hf-masthead {
            position: relative;
            overflow: hidden;
            border-radius: 12px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(90deg, rgba(10, 16, 25, 0.98), rgba(16, 24, 38, 0.96));
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
            padding: 0.5rem 0.85rem 0.6rem;
            margin-bottom: 0.5rem;
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 0.75rem;
            align-items: center;
        }
        .hf-masthead-title {
            font-size: 1.1rem;
            line-height: 1.1;
            font-weight: 800;
            color: var(--hf-text);
            letter-spacing: 0.02em;
        }
        .hf-masthead-eyebrow {
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--hf-amber);
            margin-bottom: 0.1rem;
        }
        .hf-chip-row {
            display: flex;
            gap: 0.4rem;
            flex-wrap: wrap;
            justify-content: flex-end;
        }
        .hf-chip {
            border-radius: 8px;
            border: 1px solid var(--hf-line);
            background: rgba(14, 21, 32, 0.9);
            padding: 0.3rem 0.6rem;
            display: flex;
            gap: 0.4rem;
            align-items: baseline;
        }
        .hf-chip-label {
            font-size: 0.58rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--hf-muted);
        }
        .hf-chip-value {
            color: var(--hf-text);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.82rem;
            line-height: 1.1;
        }

        /* ----------- Console vs Checklist physical & visual split ----------- */
        .hf-console-panel,
        .hf-checklist-panel {
            position: relative;
            border-radius: 14px;
            padding: 0.75rem 0.85rem 0.9rem;
            margin-bottom: 0.6rem;
        }
        .hf-console-panel {
            border: 1px solid rgba(95, 180, 255, 0.3);
            background: linear-gradient(180deg, rgba(11, 20, 34, 0.96), rgba(7, 14, 24, 0.96));
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35), inset 0 0 0 1px rgba(95, 180, 255, 0.06);
        }
        .hf-console-panel::before {
            content: "CONSOLE";
            position: absolute; top: -10px; left: 18px;
            background: #0a1322;
            border: 1px solid rgba(95, 180, 255, 0.45);
            color: var(--hf-blue);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.68rem;
            letter-spacing: 0.26em;
            padding: 0.2rem 0.6rem;
            border-radius: 10px;
        }
        .hf-checklist-panel {
            border: 1px solid rgba(250, 204, 21, 0.3);
            background: linear-gradient(180deg, rgba(30, 25, 10, 0.45), rgba(22, 18, 8, 0.5));
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35), inset 0 0 0 1px rgba(250, 204, 21, 0.06);
        }
        .hf-checklist-panel::before {
            content: "CHECKLIST";
            position: absolute; top: -10px; left: 18px;
            background: #181308;
            border: 1px solid rgba(250, 204, 21, 0.5);
            color: var(--hf-amber);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.68rem;
            letter-spacing: 0.26em;
            padding: 0.2rem 0.6rem;
            border-radius: 10px;
        }

        /* Mode badge */
        .hf-mode-shell {
            position: relative;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            background: linear-gradient(145deg, rgba(9, 15, 23, 0.98), rgba(12, 19, 30, 0.96));
            padding: 0.75rem 0.9rem 0.9rem;
            margin-bottom: 0.75rem;
        }
        .hf-mode-label {
            color: var(--hf-muted);
            font-size: 0.66rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .hf-mode-value {
            border-radius: 14px;
            background: var(--mode-color, #424242);
            box-shadow: 0 0 28px var(--mode-glow, rgba(148,163,184,0.24)), inset 0 1px 0 rgba(255, 255, 255, 0.2);
            color: white;
            padding: 0.75rem 0.9rem;
            text-align: center;
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: clamp(1.4rem, 3vw, 2.2rem);
            letter-spacing: 0.14em;
            font-weight: 800;
        }

        /* Fault banner */
        .hf-fault {
            position: relative;
            overflow: hidden;
            border-radius: 14px;
            border: 1px solid rgba(251, 77, 61, 0.38);
            background: linear-gradient(180deg, rgba(65, 15, 15, 0.92), rgba(37, 11, 11, 0.88));
            color: #ffe6e3;
            padding: 0.7rem 0.85rem;
            margin: 0.55rem 0 0.75rem;
        }
        .hf-fault::before {
            content: "";
            position: absolute; inset: 0 auto 0 0;
            width: 6px;
            background: linear-gradient(180deg, var(--hf-red), var(--hf-orange));
        }
        .hf-fault-label {
            color: rgba(255, 226, 222, 0.76);
            font-size: 0.66rem;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-left: 0.2rem;
        }
        .hf-fault-value {
            margin-left: 0.2rem;
            margin-top: 0.25rem;
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 1rem;
            line-height: 1.3;
            color: #fff5f4;
            text-transform: uppercase;
        }

        /* Trigger cues */
        .hf-cues {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.45rem;
            margin: 0.55rem 0 0.75rem;
        }
        .hf-cue {
            border-radius: 12px;
            border: 1px solid rgba(250, 204, 21, 0.3);
            background: rgba(43, 34, 11, 0.35);
            padding: 0.45rem 0.6rem;
        }
        .hf-cue-label {
            color: rgba(250, 204, 21, 0.9);
            font-size: 0.6rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }
        .hf-cue-value {
            color: var(--hf-text);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.88rem;
            font-weight: 700;
        }

        /* Sticky status bar (timer + mode + fault) */
        .hf-statusbar {
            position: sticky;
            top: 3.5rem;
            z-index: 50;
            display: grid;
            grid-template-columns: minmax(180px, 1fr) minmax(120px, auto) 2fr;
            gap: 0.75rem;
            padding: 0.6rem 0.85rem;
            margin-bottom: 0.75rem;
            border-radius: 14px;
            border: 1px solid rgba(95, 180, 255, 0.35);
            background: linear-gradient(180deg, rgba(9, 16, 28, 0.98), rgba(6, 11, 20, 0.98));
            backdrop-filter: blur(6px);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.45);
        }
        .hf-statusbar-cell {
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-width: 0;
        }
        .hf-statusbar-label {
            font-size: 0.6rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--hf-muted);
            margin-bottom: 0.15rem;
        }
        .hf-statusbar-value {
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-weight: 800;
            font-size: 1.5rem;
            line-height: 1.1;
            color: var(--hf-text);
        }
        .hf-statusbar-fault .hf-statusbar-value {
            font-size: 0.95rem;
            font-weight: 700;
            color: #ffdcd7;
            text-transform: uppercase;
        }

        /* Timer */
        .hf-timer {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin: 0.45rem 0 0.2rem;
        }
        .hf-timer-label {
            color: var(--hf-muted);
            font-size: 0.66rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
        }
        .hf-timer-value {
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 2rem;
            font-weight: 800;
            color: var(--timer-color, var(--hf-text));
            letter-spacing: 0.05em;
        }
        .hf-timer-bar {
            height: 6px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            overflow: hidden;
        }
        .hf-timer-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--timer-color, var(--hf-blue)), var(--hf-cyan));
            transition: width 0.4s linear;
        }

        /* Checklist step cards */
        .hf-step-current,
        .hf-step-done,
        .hf-step-upcoming,
        .hf-step-terminal {
            position: relative;
            border-radius: 8px;
            border: 1px solid var(--hf-line);
            padding: 0.35rem 0.6rem;
            margin-bottom: 0.25rem;
            background: rgba(13, 20, 31, 0.6);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.82rem;
            line-height: 1.3;
            color: var(--hf-text);
        }
        .hf-step-current { border-color: rgba(95, 180, 255, 0.45); box-shadow: inset 0 0 0 1px rgba(95, 180, 255, 0.1); }
        .hf-step-done    { border-color: rgba(74, 222, 128, 0.38); color: #dcfce7; }
        .hf-step-upcoming{ color: var(--hf-muted); }
        .hf-step-terminal{ border-color: rgba(251, 77, 61, 0.4); color: #ffe4e0; }
        .hf-step-note {
            display: block;
            margin-top: 0.3rem;
            color: var(--hf-muted);
            font-size: 0.78rem;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            text-transform: none;
            letter-spacing: 0;
        }

        /* Checklist choice card (linear pick-from-3) */
        .hf-choice-card {
            border-radius: 14px;
            border: 1px solid var(--hf-line);
            background: rgba(13, 20, 31, 0.6);
            padding: 0.8rem 0.95rem 0.6rem;
            margin-bottom: 0.6rem;
        }
        .hf-choice-card.selected {
            border-color: rgba(74, 222, 128, 0.55);
            background: rgba(14, 42, 26, 0.4);
        }
        .hf-choice-card.eliminated {
            opacity: 0.45;
        }
        .hf-choice-title {
            color: var(--hf-amber);
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
            font-size: 0.88rem;
        }
        .hf-choice-step {
            color: var(--hf-text);
            font-family: "SFMono-Regular", Menlo, Consolas, monospace;
            font-size: 0.82rem;
            line-height: 1.45;
            padding: 0.12rem 0;
        }

        /* Fault notice block */
        .hf-notice {
            border-radius: 12px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(180deg, rgba(13, 20, 31, 0.98), rgba(10, 16, 25, 0.94));
            padding: 0.7rem 0.9rem;
            margin: 0.55rem 0;
            color: var(--hf-text);
            line-height: 1.45;
            font-size: 0.92rem;
        }
        .hf-notice-info { border-color: rgba(95, 180, 255, 0.32); color: #d9efff; }
        .hf-notice-warn { border-color: rgba(250, 204, 21, 0.34); color: #fff1b8; }
        .hf-notice-success { border-color: rgba(74, 222, 128, 0.34); color: #dcfce7; }
        .hf-notice-danger { border-color: rgba(251, 77, 61, 0.34); color: #ffe4e0; }

        /* Action help */
        .hf-action-help {
            min-height: 1.4rem;
            margin: 0.25rem 0.1rem 0.6rem;
            color: var(--hf-muted);
            font-size: 0.78rem;
            line-height: 1.35;
        }

        /* Section header */
        .hf-section-header {
            padding: 0.55rem 0 0.3rem;
            margin-top: 0.35rem;
            border-bottom: 1px dashed rgba(148, 163, 184, 0.18);
            margin-bottom: 0.5rem;
        }
        .hf-section-kicker {
            color: var(--hf-amber);
            font-size: 0.68rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            font-weight: 700;
        }
        .hf-section-title {
            margin-top: 0.2rem;
            color: var(--hf-text);
            font-size: 0.98rem;
            font-weight: 700;
            line-height: 1.3;
        }

        /* Form inputs — force readable text on the dark theme */
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div,
        .stApp label,
        .stApp p,
        .stMarkdown,
        .stMarkdown p,
        .stMarkdown li,
        .stCaption,
        [data-testid="stCaptionContainer"],
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] * {
            color: var(--hf-text);
        }
        .stApp .stMarkdown a {
            color: var(--hf-cyan);
        }

        /* Text inputs & text areas */
        .stApp input[type="text"],
        .stApp input[type="number"],
        .stApp input[type="password"],
        .stApp textarea,
        .stApp [data-baseweb="input"] input,
        .stApp [data-baseweb="textarea"] textarea {
            color: var(--hf-text) !important;
            -webkit-text-fill-color: var(--hf-text) !important;
            background-color: rgba(10, 16, 25, 0.85) !important;
            caret-color: var(--hf-text);
        }
        .stApp [data-baseweb="input"],
        .stApp [data-baseweb="textarea"] {
            background-color: rgba(10, 16, 25, 0.85) !important;
            border: 1px solid var(--hf-line) !important;
        }
        .stApp input::placeholder,
        .stApp textarea::placeholder {
            color: rgba(148, 167, 189, 0.55) !important;
            -webkit-text-fill-color: rgba(148, 167, 189, 0.55) !important;
        }

        /* Selectbox — closed control */
        .stApp [data-baseweb="select"] > div {
            background-color: rgba(10, 16, 25, 0.85) !important;
            border-color: var(--hf-line) !important;
            color: var(--hf-text) !important;
        }
        .stApp [data-baseweb="select"] [data-baseweb="tag"],
        .stApp [data-baseweb="select"] span,
        .stApp [data-baseweb="select"] div {
            color: var(--hf-text) !important;
        }
        /* Selectbox — open dropdown menu */
        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="menu"] {
            background-color: #0d1420 !important;
            color: var(--hf-text) !important;
            border: 1px solid var(--hf-line) !important;
        }
        [data-baseweb="popover"] li,
        [data-baseweb="menu"] li {
            color: var(--hf-text) !important;
        }
        [data-baseweb="popover"] li:hover,
        [data-baseweb="menu"] li:hover {
            background-color: rgba(95, 180, 255, 0.12) !important;
        }

        /* Radio */
        .stApp [data-baseweb="radio"] label,
        .stApp [data-baseweb="radio"] span,
        .stApp [role="radiogroup"] label,
        .stApp [role="radiogroup"] span {
            color: var(--hf-text) !important;
        }

        /* Slider — value bubble and tick labels */
        .stApp [data-testid="stSlider"] label,
        .stApp [data-testid="stSlider"] span,
        .stApp [data-testid="stSlider"] div[data-baseweb="slider"] div {
            color: var(--hf-text) !important;
        }
        .stApp [data-baseweb="slider"] [role="slider"] {
            background-color: var(--hf-blue) !important;
        }

        /* Tooltip icons next to labels */
        .stApp [data-testid="stTooltipIcon"] svg {
            color: var(--hf-muted) !important;
            fill: var(--hf-muted) !important;
        }

        /* Buttons */
        .stButton > button {
            width: 100%;
            min-height: 2.4rem;
            padding: 0.3rem 0.6rem;
            margin-bottom: 0.25rem;
            border-radius: 10px;
            border: 1px solid rgba(120, 147, 181, 0.26);
            background: linear-gradient(180deg, rgba(17, 26, 39, 0.98), rgba(10, 16, 25, 0.96));
            color: var(--hf-text);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            transition: transform 120ms ease, border-color 120ms ease;
        }
        .stButton > button p { color: inherit; font-size: 0.78rem; line-height: 1.1; margin: 0; }
        .stButton > button:hover:not(:disabled) {
            transform: translateY(-1px);
            border-color: rgba(95, 180, 255, 0.5);
        }
        .stButton > button:disabled {
            color: rgba(236, 242, 248, 0.45);
            -webkit-text-fill-color: rgba(236, 242, 248, 0.45);
            border-style: dashed;
            opacity: 0.7;
        }

        /* Intro briefing */
        .hf-brief {
            border-radius: 14px;
            border: 1px solid var(--hf-line);
            background: linear-gradient(180deg, rgba(13, 20, 31, 0.9), rgba(10, 16, 25, 0.9));
            padding: 0.85rem 1.1rem 1rem;
            margin: 0.5rem 0 0.75rem;
            color: var(--hf-text);
            line-height: 1.5;
        }
        .hf-brief h3 {
            color: var(--hf-cyan);
            font-size: 0.82rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 800;
            margin: 0.85rem 0 0.35rem;
        }
        .hf-brief h3:first-child { margin-top: 0.2rem; }
        .hf-brief p, .hf-brief li { color: var(--hf-text); font-size: 0.92rem; }
        .hf-brief ol, .hf-brief ul { padding-left: 1.2rem; margin: 0.2rem 0 0.4rem; }

        /* NASA-TLX survey blocks */
        .hf-tlx-block {
            margin-top: 0.6rem;
            margin-bottom: 0.2rem;
        }
        .hf-tlx-label {
            color: var(--hf-cyan);
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            font-weight: 800;
        }
        .hf-tlx-question {
            color: var(--hf-text);
            font-size: 1rem;
            font-weight: 600;
            margin-top: 0.15rem;
            margin-bottom: 0.25rem;
        }
        .hf-tlx-anchors {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            font-size: 0.78rem;
            color: var(--hf-muted);
            margin: 0.1rem 0 0.85rem;
        }
        .hf-tlx-anchors strong { color: var(--hf-text); }
        .hf-tlx-current { color: var(--hf-amber); font-weight: 700; }

        /* Rocket celebration */
        .hf-rocket-stage {
            position: fixed;
            inset: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 9999;
        }
        .hf-rocket {
            position: absolute;
            bottom: -80px;
            font-size: 3rem;
            animation: rocket-launch 2.8s ease-in forwards;
        }
        .hf-rocket:nth-child(1) { left: 12%; animation-delay: 0s; }
        .hf-rocket:nth-child(2) { left: 32%; animation-delay: 0.25s; font-size: 2.5rem; }
        .hf-rocket:nth-child(3) { left: 52%; animation-delay: 0.45s; font-size: 3.4rem; }
        .hf-rocket:nth-child(4) { left: 72%; animation-delay: 0.15s; font-size: 2.7rem; }
        .hf-rocket:nth-child(5) { left: 88%; animation-delay: 0.55s; font-size: 3rem; }
        @keyframes rocket-launch {
            0%   { transform: translateY(0) rotate(-8deg); opacity: 0.4; }
            20%  { opacity: 1; }
            100% { transform: translateY(-115vh) rotate(8deg); opacity: 0; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
