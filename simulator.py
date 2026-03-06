import json
import random
import time
from pathlib import Path

import pandas as pd
import streamlit as st

SCENARIO_DIR = Path("scenarios")
EVENT_LOG = Path("event_log.csv")
SUMMARY_LOG = Path("summary_log.csv")

SAMPLE_SCENARIOS = [
    {
        "scenario_id": 1,
        "title": "Relative navigation degraded",
        "initial_mode": "AUTO_APPROACH",
        "fault": "Relative navigation degraded",
        "auto_transition": {"time": 10, "new_mode": "HOLD"},
        "correct_mode": "HOLD",
        "correct_actions": ["ACK ALARM", "ENTER HOLD MODE", "RESET NAVIGATION"],
    },
    {
        "scenario_id": 2,
        "title": "Attitude control instability",
        "initial_mode": "NOMINAL",
        "fault": "Attitude controller saturation",
        "auto_transition": {"time": 8, "new_mode": "SAFE"},
        "correct_mode": "SAFE",
        "correct_actions": ["ACK ALARM", "ENTER SAFE MODE", "ISOLATE ACS"],
    },
    {
        "scenario_id": 3,
        "title": "Thermal sensor disagreement",
        "initial_mode": "AUTO_THERMAL",
        "fault": "Thermal sensor disagreement",
        "auto_transition": {"time": 12, "new_mode": "HOLD"},
        "correct_mode": "HOLD",
        "correct_actions": ["ACK ALARM", "ENTER HOLD MODE", "CYCLE SENSOR BUS"],
    },
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
}


def ensure_scenario_files():
    SCENARIO_DIR.mkdir(exist_ok=True)
    for s in SAMPLE_SCENARIOS:
        out = SCENARIO_DIR / f"scenario_{s['scenario_id']}.json"
        if not out.exists():
            out.write_text(json.dumps(s, indent=2))


def load_scenarios():
    ensure_scenario_files()
    scenarios = []
    for p in sorted(SCENARIO_DIR.glob("*.json")):
        with open(p, "r") as f:
            scenarios.append(json.load(f))
    return scenarios


def init_state():
    defaults = {
        "participant_id": "",
        "experience": "None",
        "condition_key": None,
        "scenario": None,
        "scenario_started": False,
        "start_time": None,
        "mode": None,
        "event_rows": [],
        "completed_actions": [],
        "wrong_mode_actions": 0,
        "checklist_errors": 0,
        "mode_checks": 0,
        "mode_check_errors": 0,
        "finished": False,
        "summary": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value



def elapsed_time():
    if not st.session_state.start_time:
        return 0.0
    return time.time() - st.session_state.start_time



def current_time_limit():
    return CONDITIONS[st.session_state.condition_key]["time_limit"]



def remaining_time():
    return max(0, current_time_limit() - elapsed_time())



def maybe_auto_transition():
    scenario = st.session_state.scenario
    if not scenario or not st.session_state.start_time:
        return
    t = elapsed_time()
    auto_t = scenario["auto_transition"]["time"]
    new_mode = scenario["auto_transition"]["new_mode"]
    if t >= auto_t and st.session_state.mode != new_mode:
        old_mode = st.session_state.mode
        st.session_state.mode = new_mode
        log_event("AUTO TRANSITION", {
            "from_mode": old_mode,
            "to_mode": new_mode,
            "note": f"Automatic transition at {auto_t}s",
        })



def log_event(action, extra=None):
    row = {
        "participant_id": st.session_state.participant_id,
        "condition": st.session_state.condition_key,
        "scenario_id": st.session_state.scenario["scenario_id"],
        "timestamp_s": round(elapsed_time(), 3),
        "mode": st.session_state.mode,
        "action": action,
    }
    if extra:
        row.update(extra)
    st.session_state.event_rows.append(row)



def append_csv(path, rows):
    if not rows:
        return
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False)



def execute_action(action):
    scenario = st.session_state.scenario
    correct_mode = scenario["correct_mode"]
    correct_actions = scenario["correct_actions"]

    if action not in st.session_state.completed_actions:
        st.session_state.completed_actions.append(action)

    wrong_mode = False
    if action in correct_actions[1:] and st.session_state.mode != correct_mode:
        st.session_state.wrong_mode_actions += 1
        wrong_mode = True

    if action == "SWITCH TO MANUAL":
        prev = st.session_state.mode
        st.session_state.mode = "MANUAL"
        log_event(action, {"wrong_mode": wrong_mode, "from_mode": prev, "to_mode": "MANUAL"})
        return

    if action == "ENTER HOLD MODE":
        prev = st.session_state.mode
        st.session_state.mode = "HOLD"
        log_event(action, {"wrong_mode": wrong_mode, "from_mode": prev, "to_mode": "HOLD"})
        return

    if action == "ENTER SAFE MODE":
        prev = st.session_state.mode
        st.session_state.mode = "SAFE"
        log_event(action, {"wrong_mode": wrong_mode, "from_mode": prev, "to_mode": "SAFE"})
        return

    log_event(action, {"wrong_mode": wrong_mode})



def finish_scenario(timeout=False):
    if st.session_state.finished:
        return

    scenario = st.session_state.scenario
    required = scenario["correct_actions"]
    completed = st.session_state.completed_actions
    omissions = [a for a in required if a not in completed]
    extra_actions = [a for a in completed if a not in required]
    completion_time = round(elapsed_time(), 3)

    summary = {
        "participant_id": st.session_state.participant_id,
        "experience": st.session_state.experience,
        "condition": st.session_state.condition_key,
        "checklist_type": CONDITIONS[st.session_state.condition_key]["checklist_type"],
        "time_limit": current_time_limit(),
        "scenario_id": scenario["scenario_id"],
        "fault": scenario["fault"],
        "completion_time_s": completion_time,
        "timed_out": timeout,
        "wrong_mode_actions": st.session_state.wrong_mode_actions,
        "mode_check_errors": st.session_state.mode_check_errors,
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

    log_event("SCENARIO FINISH", {"timeout": timeout, "omissions": len(omissions)})
    append_csv(EVENT_LOG, st.session_state.event_rows)
    append_csv(SUMMARY_LOG, [summary])

    st.session_state.summary = summary
    st.session_state.finished = True



def reset_run():
    for key in [
        "scenario_started", "start_time", "mode", "event_rows", "completed_actions",
        "wrong_mode_actions", "checklist_errors", "mode_checks", "mode_check_errors",
        "finished", "summary", "nasa_tlx_mental", "nasa_tlx_temporal",
        "nasa_tlx_effort", "nasa_tlx_frustration"
    ]:
        if key in ["event_rows", "completed_actions"]:
            st.session_state[key] = []
        elif key in ["scenario_started", "finished"]:
            st.session_state[key] = False
        else:
            st.session_state[key] = None if key in ["start_time", "summary"] else 0



def render_setup(scenarios):
    st.sidebar.header("Experiment Setup")
    st.session_state.participant_id = st.sidebar.text_input(
        "Participant ID", value=st.session_state.participant_id
    )
    st.session_state.experience = st.sidebar.selectbox(
        "Relevant experience",
        ["None", "Some aviation", "Some spacecraft ops", "Professional"],
        index=["None", "Some aviation", "Some spacecraft ops", "Professional"].index(st.session_state.experience),
    )

    condition_labels = list(CONDITIONS.keys())
    default_idx = 0 if st.session_state.condition_key is None else condition_labels.index(st.session_state.condition_key)
    st.session_state.condition_key = st.sidebar.selectbox("Condition", condition_labels, index=default_idx)

    scenario_titles = {f"{s['scenario_id']}: {s['title']}": s for s in scenarios}
    choice = st.sidebar.selectbox("Scenario", list(scenario_titles.keys()))
    st.session_state.scenario = scenario_titles[choice]

    if st.sidebar.button("Randomize Scenario"):
        st.session_state.scenario = random.choice(scenarios)
        st.rerun()

    if st.sidebar.button("Start / Restart Scenario"):
        reset_run()
        st.session_state.scenario_started = True
        st.session_state.start_time = time.time()
        st.session_state.mode = st.session_state.scenario["initial_mode"]
        log_event("SCENARIO START")
        st.rerun()



def render_console():
    scenario = st.session_state.scenario
    st.subheader("Spacecraft Console")
    st.metric("Current Mode", st.session_state.mode)
    st.write(f"**Fault:** {scenario['fault']}")
    st.write(f"**Auto-transition:** {scenario['auto_transition']['new_mode']} at {scenario['auto_transition']['time']} s")

    remaining = remaining_time()
    if remaining <= 10:
        st.error(f"Time Remaining: {int(remaining)} s")
    else:
        st.info(f"Time Remaining: {int(remaining)} s")

    st.write("### Available Actions")
    action_order = [
        "ACK ALARM", "ENTER HOLD MODE", "ENTER SAFE MODE",
        "RESET NAVIGATION", "ISOLATE ACS", "CYCLE SENSOR BUS", "SWITCH TO MANUAL"
    ]

    cols = st.columns(2)
    for i, action in enumerate(action_order):
        with cols[i % 2]:
            if st.button(action, use_container_width=True):
                execute_action(action)
                st.rerun()
            st.caption(ACTION_HELP[action])

    if st.button("Finish Scenario", type="primary", use_container_width=True):
        finish_scenario(timeout=False)
        st.rerun()



def render_linear_checklist():
    scenario = st.session_state.scenario
    st.subheader("Linear Checklist")
    for i, step in enumerate(scenario["correct_actions"], start=1):
        done = "✅" if step in st.session_state.completed_actions else "⬜"
        st.write(f"{done} Step {i}: {step}")

    st.markdown("---")
    st.caption("Linear condition: participants follow a fixed sequence without explicit mode verification.")



def render_branching_checklist():
    scenario = st.session_state.scenario
    st.subheader("Branching Checklist")
    st.write("**Step 1: Verify current operating mode**")

    mode_guess = st.radio(
        "Select current mode",
        [scenario["initial_mode"], scenario["correct_mode"], "MANUAL", "SAFE", "HOLD", "NOMINAL"],
        index=0,
        key="mode_guess",
    )

    if st.button("Submit Mode Check", use_container_width=True):
        st.session_state.mode_checks += 1
        correct = mode_guess == st.session_state.mode
        if not correct:
            st.session_state.mode_check_errors += 1
        log_event("MODE CHECK", {"guess": mode_guess, "correct": correct})
        st.rerun()

    st.markdown("---")
    st.write("**Step 2: Branch based on verified mode**")
    if st.session_state.mode == scenario["correct_mode"]:
        st.success(f"Verified mode is {scenario['correct_mode']}. Proceed with recovery actions:")
        for action in scenario["correct_actions"]:
            done = "✅" if action in st.session_state.completed_actions else "⬜"
            st.write(f"{done} {action}")
    else:
        st.warning(
            f"Current mode is not yet the target recovery mode ({scenario['correct_mode']}). "
            "A participant should wait, monitor, and verify mode before continuing."
        )

    st.caption("Branching condition: explicit mode identification before executing recovery actions.")



def render_checklist():
    checklist_type = CONDITIONS[st.session_state.condition_key]["checklist_type"]
    if checklist_type == "linear":
        render_linear_checklist()
    else:
        render_branching_checklist()



def render_post_run():
    st.markdown("---")
    st.subheader("Post-Run Workload Survey")
    st.session_state.nasa_tlx_mental = st.slider("Mental Demand", 1, 10, 5)
    st.session_state.nasa_tlx_temporal = st.slider("Temporal Demand", 1, 10, 5)
    st.session_state.nasa_tlx_effort = st.slider("Effort", 1, 10, 5)
    st.session_state.nasa_tlx_frustration = st.slider("Frustration", 1, 10, 5)

    if st.button("Save Survey + Finish", use_container_width=True):
        finish_scenario(timeout=remaining_time() <= 0)
        st.rerun()



def render_summary():
    s = st.session_state.summary
    st.success("Scenario complete")
    st.write(f"**Completion time:** {s['completion_time_s']} s")
    st.write(f"**Wrong-mode actions:** {s['wrong_mode_actions']}")
    st.write(f"**Mode-check errors:** {s['mode_check_errors']}")
    st.write(f"**Step omissions:** {s['step_omissions']}")
    st.write(f"**Completed all required steps:** {s['completed_all_required']}")
    st.caption(f"Logs written to {EVENT_LOG} and {SUMMARY_LOG}")



st.set_page_config(page_title="Checklist Design Experiment", layout="wide")
init_state()
scenarios = load_scenarios()

st.title("Spacecraft Anomaly Response Experiment")
st.caption("Prototype for comparing linear vs. branching checklist designs under time pressure.")

render_setup(scenarios)

if not st.session_state.scenario_started:
    st.info("Use the sidebar to choose a participant, condition, and scenario, then click Start / Restart Scenario.")
    st.stop()

maybe_auto_transition()

if remaining_time() <= 0 and not st.session_state.finished:
    st.error("Time expired. Complete the workload survey and save the run.")

left, right = st.columns([1.15, 1])
with left:
    render_console()
with right:
    render_checklist()

if not st.session_state.finished:
    render_post_run()
else:
    render_summary()
