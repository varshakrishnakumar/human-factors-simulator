from typing import Any, Dict, List

FAMILIARIZATION: Dict[str, Any] = {
    "scenario_id": 0,
    "title": "Familiarization",
    "fault": "Practice alert (no real fault)",
    "initial_mode": "AUTO",
    "auto_transition": {"time": 99999, "new_mode": "AUTO"},
    "correct_mode": "AUTO",
    "trigger_cues": [
        {"label": "MODE", "value": "AUTO"},
        {"label": "STATUS", "value": "PRACTICE"},
    ],
    "linear_checklist": {
        "title": "Practice",
        "steps": ["ACK PRACTICE ALERT"],
    },
    "branching_checklist": {
        "title": "Practice",
        "steps": [
            {"id": 1, "type": "action", "text": "ACK PRACTICE ALERT", "next": None},
        ],
    },
    "action_expected_modes": {},
    "is_familiarization": True,
}

NAV: Dict[str, Any] = {
    "scenario_id": 1,
    "title": "Navigation Fault Recovery",
    "fault": "Loss of navigation data",
    "initial_mode": "AUTO",
    "auto_transition": {"time": 5, "new_mode": "HOLD"},
    "correct_mode": "AUTO",
    "trigger_cues": [
        {"label": "MODE", "value": "HOLD"},
        {"label": "STAR TRACKER", "value": "FAILED"},
        {"label": "NAV DATA", "value": "INVALID"},
    ],
    "linear_checklist": {
        "title": "Navigation Fault Recovery",
        "steps": [
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN GNC STATUS PANEL",
            "RESET NAVIGATION FILTER",
            "REINITIALIZE STAR TRACKER",
            "CONFIRM NAVIGATION DATA RESTORED",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ],
    },
    "branching_checklist": {
        "title": "Navigation Fault Recovery",
        "steps": [
            {"id": 1, "type": "action", "text": "ACK ALARM", "next": 2,
             "note": "Acknowledge the caution before proceeding."},
            {"id": 2, "type": "action", "text": "OPEN GNC STATUS PANEL", "next": 3,
             "note": "Then check the star-tracker indicator on the GNC panel."},
            {"id": 3, "type": "decision",
             "prompt": "Is the star tracker reporting FAILED?",
             "options": [
                 {"label": "Yes — star tracker failed", "next": 4, "correct": True,
                  "note": "If YES, proceed to STEP 4."},
                 {"label": "No — star tracker nominal", "next": 99, "correct": False,
                  "note": "If NO, this checklist does not apply."},
             ]},
            {"id": 4, "type": "action", "text": "RESET NAVIGATION FILTER", "next": 5,
             "note": "Reset the navigation filter while spacecraft stays in HOLD."},
            {"id": 5, "type": "action", "text": "REINITIALIZE STAR TRACKER", "next": 6,
             "note": "Reinitialize the star tracker to recover nav data."},
            {"id": 6, "type": "decision",
             "prompt": "Is NAV DATA now valid?",
             "options": [
                 {"label": "Yes — nav data valid", "next": 7, "correct": True,
                  "note": "If YES, proceed to STEP 7."},
                 {"label": "No — still invalid", "next": 4, "correct": False,
                  "note": "If NO, return to STEP 4 and retry."},
             ]},
            {"id": 7, "type": "action", "text": "SELECT AUTO MODE", "next": 8},
            {"id": 8, "type": "action", "text": "VERIFY ATTITUDE STABLE", "next": 9},
            {"id": 9, "type": "action", "text": "REPORT PROCEDURE COMPLETE", "next": None},
            {"id": 99, "type": "terminal", "text": "WRONG BRANCH — STOP", "next": None,
             "note": "Incorrect diagnosis path. Trial ends."},
        ],
    },
    "action_expected_modes": {
        "RESET NAVIGATION FILTER": "HOLD",
        "REINITIALIZE STAR TRACKER": "HOLD",
        "CONFIRM NAVIGATION DATA RESTORED": "HOLD",
        "SELECT AUTO MODE": "HOLD",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    },
}

THERMAL: Dict[str, Any] = {
    "scenario_id": 2,
    "title": "Thermal Loop Recovery",
    "fault": "Radiator bypass valve stuck, thermal loop out of spec",
    "initial_mode": "AUTO",
    "auto_transition": {"time": 5, "new_mode": "SAFE"},
    "correct_mode": "AUTO",
    "trigger_cues": [
        {"label": "MODE", "value": "SAFE"},
        {"label": "THERMAL LOOP", "value": "OVERTEMP"},
        {"label": "RADIATOR", "value": "VALVE FAULT"},
    ],
    "linear_checklist": {
        "title": "Thermal Loop Recovery",
        "steps": [
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN THERMAL STATUS PANEL",
            "CYCLE RADIATOR BYPASS VALVE",
            "ENGAGE BACKUP HEATER",
            "CONFIRM THERMAL LOOP STABLE",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ],
    },
    "branching_checklist": {
        "title": "Thermal Loop Recovery",
        "steps": [
            {"id": 1, "type": "action", "text": "ACK ALARM", "next": 2,
             "note": "Acknowledge the thermal caution before proceeding."},
            {"id": 2, "type": "action", "text": "OPEN THERMAL STATUS PANEL", "next": 3,
             "note": "Then check the radiator bypass valve indicator."},
            {"id": 3, "type": "decision",
             "prompt": "Is the radiator bypass valve reporting a FAULT?",
             "options": [
                 {"label": "Yes — valve fault", "next": 4, "correct": True,
                  "note": "If YES, proceed to STEP 4."},
                 {"label": "No — valve nominal", "next": 99, "correct": False,
                  "note": "If NO, this checklist does not apply."},
             ]},
            {"id": 4, "type": "action", "text": "CYCLE RADIATOR BYPASS VALVE", "next": 5,
             "note": "Cycle the valve while in SAFE mode."},
            {"id": 5, "type": "action", "text": "ENGAGE BACKUP HEATER", "next": 6,
             "note": "Bring the redundant heater online."},
            {"id": 6, "type": "decision",
             "prompt": "Is the thermal loop back within spec?",
             "options": [
                 {"label": "Yes — loop stable", "next": 7, "correct": True,
                  "note": "If YES, proceed to STEP 7."},
                 {"label": "No — still out of spec", "next": 4, "correct": False,
                  "note": "If NO, return to STEP 4 and retry."},
             ]},
            {"id": 7, "type": "action", "text": "SELECT AUTO MODE", "next": 8},
            {"id": 8, "type": "action", "text": "VERIFY ATTITUDE STABLE", "next": 9},
            {"id": 9, "type": "action", "text": "REPORT PROCEDURE COMPLETE", "next": None},
            {"id": 99, "type": "terminal", "text": "WRONG BRANCH — STOP", "next": None,
             "note": "Incorrect diagnosis path. Trial ends."},
        ],
    },
    "action_expected_modes": {
        "CYCLE RADIATOR BYPASS VALVE": "SAFE",
        "ENGAGE BACKUP HEATER": "SAFE",
        "CONFIRM THERMAL LOOP STABLE": "SAFE",
        "SELECT AUTO MODE": "SAFE",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    },
}

COMM: Dict[str, Any] = {
    "scenario_id": 3,
    "title": "Communications Loss Recovery",
    "fault": "Primary downlink failure, ground link lost",
    "initial_mode": "AUTO",
    "auto_transition": {"time": 5, "new_mode": "HOLD"},
    "correct_mode": "AUTO",
    "trigger_cues": [
        {"label": "MODE", "value": "HOLD"},
        {"label": "DOWNLINK", "value": "LOST"},
        {"label": "RF TRANSCEIVER", "value": "DEGRADED"},
    ],
    "linear_checklist": {
        "title": "Communications Loss Recovery",
        "steps": [
            "ACK ALARM",
            "SILENCE CAUTION TONE",
            "OPEN COMM STATUS PANEL",
            "SWITCH TO BACKUP DOWNLINK",
            "REINITIALIZE RF TRANSCEIVER",
            "CONFIRM GROUND LINK RESTORED",
            "SELECT AUTO MODE",
            "VERIFY ATTITUDE STABLE",
            "REPORT PROCEDURE COMPLETE",
        ],
    },
    "branching_checklist": {
        "title": "Communications Loss Recovery",
        "steps": [
            {"id": 1, "type": "action", "text": "ACK ALARM", "next": 2,
             "note": "Acknowledge the comm caution before proceeding."},
            {"id": 2, "type": "action", "text": "OPEN COMM STATUS PANEL", "next": 3,
             "note": "Then check the downlink status indicator."},
            {"id": 3, "type": "decision",
             "prompt": "Is the primary downlink reporting LOST?",
             "options": [
                 {"label": "Yes — downlink lost", "next": 4, "correct": True,
                  "note": "If YES, proceed to STEP 4."},
                 {"label": "No — downlink nominal", "next": 99, "correct": False,
                  "note": "If NO, this checklist does not apply."},
             ]},
            {"id": 4, "type": "action", "text": "SWITCH TO BACKUP DOWNLINK", "next": 5,
             "note": "Hand over to the redundant downlink."},
            {"id": 5, "type": "action", "text": "REINITIALIZE RF TRANSCEIVER", "next": 6,
             "note": "Reinitialize the RF transceiver to re-acquire ground."},
            {"id": 6, "type": "decision",
             "prompt": "Is the ground link active and stable?",
             "options": [
                 {"label": "Yes — ground link restored", "next": 7, "correct": True,
                  "note": "If YES, proceed to STEP 7."},
                 {"label": "No — still lost", "next": 4, "correct": False,
                  "note": "If NO, return to STEP 4 and retry."},
             ]},
            {"id": 7, "type": "action", "text": "SELECT AUTO MODE", "next": 8},
            {"id": 8, "type": "action", "text": "VERIFY ATTITUDE STABLE", "next": 9},
            {"id": 9, "type": "action", "text": "REPORT PROCEDURE COMPLETE", "next": None},
            {"id": 99, "type": "terminal", "text": "WRONG BRANCH — STOP", "next": None,
             "note": "Incorrect diagnosis path. Trial ends."},
        ],
    },
    "action_expected_modes": {
        "SWITCH TO BACKUP DOWNLINK": "HOLD",
        "REINITIALIZE RF TRANSCEIVER": "HOLD",
        "CONFIRM GROUND LINK RESTORED": "HOLD",
        "SELECT AUTO MODE": "HOLD",
        "VERIFY ATTITUDE STABLE": "AUTO",
        "REPORT PROCEDURE COMPLETE": "AUTO",
    },
}

_SCENARIOS = [NAV, THERMAL, COMM]


def get_scenarios() -> List[Dict[str, Any]]:
    return _SCENARIOS


def get_familiarization() -> Dict[str, Any]:
    return FAMILIARIZATION


def scenario_by_id(scenario_id: int) -> Dict[str, Any]:
    for s in _SCENARIOS:
        if s["scenario_id"] == scenario_id:
            return s
    raise KeyError(f"No scenario with id {scenario_id}")


def linear_candidates() -> List[Dict[str, Any]]:
    """Every scenario's linear checklist, exposed as the 3 choices offered to the subject."""
    return [
        {
            "scenario_id": s["scenario_id"],
            "title": s["linear_checklist"]["title"],
            "steps": s["linear_checklist"]["steps"],
            "trigger_cues": s["trigger_cues"],
        }
        for s in _SCENARIOS
    ]
