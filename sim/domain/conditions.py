"""The condition catalog (the four 2x2 cells) and a pure balanced-assignment
function. I kept this pure (no I/O) so it can be unit-tested without mocking
Sheets. The I/O wrapper that reads real assignment counts lives in
sim/io/sinks.py as balanced_condition() — sinks.py calls _pure_balanced_condition
here after fetching counts from Sheets."""
from typing import Dict, List, Optional, Tuple

from sim.domain.models import Condition

CONDITIONS: Dict[str, Condition] = {
    "linear_high": Condition(
        key="linear_high",
        checklist_type="linear",
        time_limit=45,
        label="Linear · High time pressure",
    ),
    "linear_low": Condition(
        key="linear_low",
        checklist_type="linear",
        time_limit=90,
        label="Linear · Low time pressure",
    ),
    "branching_high": Condition(
        key="branching_high",
        checklist_type="branching",
        time_limit=45,
        label="Branching · High time pressure",
    ),
    "branching_low": Condition(
        key="branching_low",
        checklist_type="branching",
        time_limit=90,
        label="Branching · Low time pressure",
    ),
}

BACKGROUND_OPTIONS: Tuple[str, ...] = (
    "None",
    "Some aviation",
    "Some spacecraft ops",
    "Professional",
)

NUM_REAL_TRIALS: int = 3
FAMILIARIZATION_TIME_LIMIT: int = 600


def balanced_condition(
    experience: str,
    counts: Dict[Tuple[str, str], int],
    condition_keys: List[str],
) -> str:
    """Pick the condition with the fewest prior assignments for this experience
    level (first tie-breaker: lowest overall count for that condition; second
    tie-breaker: list order). Falls back to the first condition key when
    `counts` is empty. Called by sinks.balanced_condition() after it fetches
    real counts from Sheets; also called directly by tests with fake counts."""
    if not condition_keys:
        return ""
    best_key: Optional[str] = None
    best_score: Optional[Tuple[int, int]] = None
    totals: Dict[str, int] = {
        c: sum(n for (cond, _), n in counts.items() if cond == c)
        for c in condition_keys
    }
    for c in condition_keys:
        per_exp = counts.get((c, experience), 0)
        score = (per_exp, totals[c])
        if best_score is None or score < best_score:
            best_score = score
            best_key = c
    return best_key or condition_keys[0]
