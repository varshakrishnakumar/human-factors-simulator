"""Global action-help lookup. Keeps cross-scenario actions in one place."""
from typing import Dict

ACTION_HELP: Dict[str, str] = {
    "ACK ALARM": "Acknowledge the annunciated caution or warning.",
    "SILENCE CAUTION TONE": "Silence the audible tone after acknowledging the alarm.",
    "SELECT AUTO MODE": "Command the spacecraft back into AUTO mode.",
    "VERIFY ATTITUDE STABLE": "Confirm attitude is stable after recovery.",
    "REPORT PROCEDURE COMPLETE": "Report that the recovery procedure is complete.",
    "OPEN GNC STATUS PANEL": "Open the guidance, navigation, and control status panel.",
    "RESET NAVIGATION FILTER": "Reset the navigation filter.",
    "REINITIALIZE STAR TRACKER": "Reinitialize the star tracker to recover nav data.",
    "CONFIRM NAVIGATION DATA RESTORED": "Confirm the navigation solution is valid again.",
    "OPEN THERMAL STATUS PANEL": "Open the thermal control subsystem status panel.",
    "CYCLE RADIATOR BYPASS VALVE": "Cycle the stuck radiator bypass valve.",
    "ENGAGE BACKUP HEATER": "Bring the redundant heater online.",
    "CONFIRM THERMAL LOOP STABLE": "Confirm the thermal loop is back within spec.",
    "OPEN COMM STATUS PANEL": "Open the communications status panel.",
    "SWITCH TO BACKUP DOWNLINK": "Hand over to the redundant downlink path.",
    "REINITIALIZE RF TRANSCEIVER": "Reinitialize the RF transceiver.",
    "CONFIRM GROUND LINK RESTORED": "Confirm the ground link is active and stable.",
    "ACK PRACTICE ALERT": "Acknowledge the practice alert to complete the warm-up.",
}
