# Refactor Framework Design — human-factors-simulator

**Date:** 2026-04-18
**Branch:** `refactor/cleanup-2026-04`
**Author:** Irfan
**Reviewer:** Varsha (repo owner)

## Goal

Restructure the codebase so future changes requested by the data team (see data team feedback 2026-04-12) are localized, low-risk, and fast to apply. **This refactor does not change app behavior.** Every user-visible feature, data output, and on-screen element works identically before and after.

## Scope

- **In scope:** module structure, typed domain models, engine/UI separation, per-screen files, a registry for scenarios, survey-as-data, unit tests for the extracted engine, a smoke test, an IO layer split.
- **Out of scope:** any of the data team's actual feature requests (live timer fix, interface trim, rocketship stretch, 4th scenario, etc.). Those are follow-up work enabled by this refactor, not part of it.
- **Frozen:** output schemas for the `assignments`, `events`, and `summaries` worksheets/CSVs — column names and semantics stay identical so existing analysis scripts don't break. Column sets:
  - `assignments`: `session_id`, `participant_id`, `experience`, `condition`, `checklist_type`, `time_limit`, `assignment_mode`, `scenario_order`, `ts`
  - `events`: `session_id`, `participant_id`, `experience`, `condition`, `checklist_type`, `is_familiarization`, `trial_number`, `scenario_id`, `timestamp_s`, `mode`, `action`, plus event-type-specific extras (`from_mode`, `to_mode`, `wrong_mode`, `attempted`, `expected`, `choice`, `correct`, `end_reason`, `completion_time`, etc.) which Google Sheets reconciles by name — existing behavior
  - `summaries`: see the `TrialResult` field list below, plus the survey fields merged in at submission

## Non-goals

- No new dependencies beyond `pytest` (added to a new `requirements-dev.txt`).
- No CI setup.
- No CSS changes — `styles.py` moves but its contents are untouched.
- No changes to `simulator.py`'s CLI invocation — `streamlit run simulator.py` still works. Its internal imports do get updated as files move; that's not a user-visible change.

## Target architecture

Shape 1 — layered. Domain layer is pure Python, UI layer is Streamlit-only, IO layer wraps persistence.

**Streamlit import rule.** `import streamlit as st` is allowed in exactly two places: `sim/ui/**` (the UI layer) and `sim/state.py` (the bridge — it has to touch `st.session_state`). Every file under `sim/domain/` and `sim/io/` must import-clean without Streamlit installed. Smoke test enforces this by importing each domain/io module in isolation.

**`__init__.py`.** Every directory under `sim/` is a package — each gets an `__init__.py` (empty unless it needs to re-export). Missing ones break imports silently under some Python setups.

```
sim/
  domain/            # pure Python — no streamlit import anywhere in this tree
    models.py        # @dataclass schemas
    engine.py        # TrialEngine — trial lifecycle, pure
    scoring.py       # end-reason classification, error aggregation
    scenarios/       # one file per scenario + registry
      __init__.py
      familiarization.py
      nav.py
      thermal.py
      comm.py
      registry.py
    survey.py        # NASA-TLX questions as data
    conditions.py    # Condition catalog + pure balanced_condition(counts, ...)
    action_help.py   # shared ACTION_HELP dict (many actions are cross-scenario)
  ui/                # streamlit-only
    screens/
      __init__.py
      intro.py
      sidebar.py
      masthead.py
      status_bar.py
      console.py
      linear.py
      branching.py
      familiarization_done.py
      survey.py
      summary.py
    widgets.py       # primitives (replaces components.py)
    styles.py        # unchanged contents, new location
  io/
    sinks.py         # persist(), record_assignment(), read_assignment_counts(), balanced_condition() wrapper
    _sheets.py       # internal: gspread auth + worksheet plumbing
  state.py           # phase-scoped dataclasses + bridge to st.session_state
simulator.py         # entry point — unchanged behavior
tests/
  __init__.py
  conftest.py
  test_engine.py
  test_scoring.py
  test_registry.py
  test_conditions.py
  test_smoke.py
requirements.txt     # prod deps (unchanged)
requirements-dev.txt # pytest
```

## Domain layer (`sim/domain/`)

### `models.py`

Frozen dataclasses for every shape flowing through the app.

- `TriggerCue(label: str, value: str)`
- `LinearChecklist(title: str, steps: tuple[str, ...])`
- `ActionStep(id: int, text: str, next: Optional[int], note: str = "")`
- `DecisionOption(label: str, next: Optional[int], correct: bool, note: str = "")`
- `DecisionStep(id: int, prompt: str, options: tuple[DecisionOption, ...])`
- `TerminalStep(id: int, text: str, note: str = "")`
- `BranchingStep = Union[ActionStep, DecisionStep, TerminalStep]`
- `BranchingChecklist(title: str, steps: tuple[BranchingStep, ...])`
- `AutoTransition(time: float, new_mode: str)`
- `Scenario(id: int, title: str, fault: str, initial_mode: str, auto_transition: AutoTransition, correct_mode: str, trigger_cues: tuple[TriggerCue, ...], linear_checklist: LinearChecklist, branching_checklist: BranchingChecklist, action_expected_modes: dict[str, str], is_familiarization: bool = False)`
- `LinearCandidate(scenario_id: int, title: str, steps: tuple[str, ...], trigger_cues: tuple[TriggerCue, ...])` — view-model returned by `linear_candidates()` for the linear picker.
- `Condition(key: str, checklist_type: Literal["linear", "branching"], time_limit: int, label: str)` — `key` is kept on the dataclass (slight duplication with the `CONDITIONS` dict key) so a `Condition` is self-describing and round-trips to output rows without the bridge having to look it up.
- `TrialContext(session_id: str, participant_id: str, experience: str, trial_number: int)` — identity/session data the engine needs to build a complete `TrialResult`. Passed in at engine construction time so `result()` can return a fully-populated record.
- `SurveyQuestion(key: str, label: str, question: str, low_anchor: str, high_anchor: str, min: int = 1, max: int = 10, default: int = 5)`
- `TrialEvent(timestamp_s: float, mode: Optional[str], action: str, extra: dict[str, Any] = field(default_factory=dict))` — engine-produced event. Only carries fields the engine knows. `extra` holds event-type-specific keys (`from_mode`, `to_mode`, `wrong_mode`, `choice`, `correct`, etc.). The bridge **flattens `extra` into the output row** and prepends the identity fields (`session_id`, `participant_id`, `experience`, `condition`, `checklist_type`, `trial_number`, `scenario_id`, `is_familiarization`) so the resulting dict matches today's `events` worksheet schema exactly.
- `TrialResult` — typed version of the summary dict built in `finish_trial`. Fields must match the current `summaries` output schema exactly (the frozen column set):
  - `session_id: str`, `participant_id: str`, `experience: str`, `condition: str`, `checklist_type: str`, `time_limit: int`, `trial_number: int`, `scenario_id: int`, `scenario_title: str`, `fault: str`, `completion_time_s: float`, `end_reason: str`, `completed: bool`, `timed_out: bool`, `wrong_mode_actions: int`, `order_errors: int`, `branch_decision_errors: int`, `checklist_selection_error: int`, `selected_checklist_id: Optional[int]`
  - Survey fields are merged in at submission time by `submit_session_survey`, not on the engine's `result()` — same as today.
- `EndReason = Literal["completed", "timeout", "wrong_branch", "procedure_end"]`

### `scenarios/`

One file per scenario. Each exports a module-level `SCENARIO: Scenario`.

`registry.py` exposes:

- `get_all() -> tuple[Scenario, ...]` — the three real scenarios in declaration order
- `get_by_id(scenario_id: int) -> Scenario` — raises `KeyError` on miss
- `get_familiarization() -> Scenario`
- `linear_candidates() -> tuple[LinearCandidate, ...]` — adapter for the linear picker UI

Adding a 4th scenario = create `sim/domain/scenarios/new_fault.py` and add one import in `registry.py`.

### `survey.py`

```python
QUESTIONS: tuple[SurveyQuestion, ...] = (
    SurveyQuestion(key="nasa_tlx_mental", label="Mental demand", ...),
    SurveyQuestion(key="nasa_tlx_temporal", label="Temporal demand", ...),
    SurveyQuestion(key="nasa_tlx_effort", label="Effort", ...),
    SurveyQuestion(key="nasa_tlx_frustration", label="Frustration", ...),
)
COMMENT_KEYS: tuple[str, ...] = ("tlx_mental_comment", "tlx_temporal_comment", "tlx_effort_comment", "tlx_frustration_comment", "general_comment")
```

UI renders by iterating `QUESTIONS`. Changing wording = data edit in this file.

### `conditions.py`

```python
CONDITIONS: dict[str, Condition] = { ... }  # same content as today's config.py
BACKGROUND_OPTIONS: tuple[str, ...] = ("None", "Some aviation", "Some spacecraft ops", "Professional")
NUM_REAL_TRIALS: int = 3
FAMILIARIZATION_TIME_LIMIT: int = 600

def balanced_condition(experience: str, counts: dict[tuple[str, str], int], condition_keys: list[str]) -> str:
    """Pure — takes counts as arg. No I/O."""
```

### `action_help.py`

Global `ACTION_HELP: dict[str, str]` keyed by action text. Kept global (not per-scenario) because `ACK ALARM`, `SILENCE CAUTION TONE`, `SELECT AUTO MODE`, `VERIFY ATTITUDE STABLE`, and `REPORT PROCEDURE COMPLETE` appear in every scenario — per-scenario would duplicate them. Scenario-specific actions (e.g. `CYCLE RADIATOR BYPASS VALVE`) go in the same dict. UI reads via `action_help.get(action, "")`.

### `engine.py`

`TrialEngine` class. State lives in instance attributes; no `st.session_state` access.

**Constructor:** `TrialEngine(scenario: Scenario, condition: Condition, context: TrialContext, start_time: float)` — `is_familiarization` is read off `scenario.is_familiarization`, not passed separately. For familiarization scenarios the engine auto-sets `selected_checklist_id = scenario.id` at construction so the action buttons appear immediately (matches today's behavior in `_start_familiarization`).

**Public methods (all take explicit `now: float` where time matters — this is what makes them testable):**

- `execute_action(action: str, now: float) -> None`
- `submit_decision(option_index: int, now: float) -> None`
- `select_linear_checklist(scenario_id: int, now: float) -> None`
- `tick(now: float) -> None` — checks timeout + auto-transition; mutates state
- `elapsed(now: float) -> float`
- `remaining(now: float) -> float`
- `current_action_buttons() -> tuple[str, ...]`
- `current_branching_step() -> Optional[BranchingStep]`
- `picked_linear_checklist() -> Optional[LinearChecklist]`
- `is_finished() -> bool`
- `end_reason() -> Optional[EndReason]`
- `result() -> TrialResult` — only valid after `is_finished()`
- `event_log() -> tuple[TrialEvent, ...]` — list of per-action log rows the bridge pushes to sinks

### `scoring.py`

Pure classification rules — the engine delegates to these so "how do we decide the trial is over" can change without touching engine mechanics.

- `classify_end(engine: TrialEngine, now: float) -> Optional[EndReason]` — inspects engine state + scenario after every action/decision/tick and returns a reason if the trial should finish, else `None`. Engine calls it inside `execute_action`, `submit_decision`, and `tick`, passing the current `now`; when a reason comes back, engine marks itself finished with that reason. Covers:
  - Familiarization: `"completed"` when the practice action has been clicked.
  - Linear: `"completed"` when all steps of the picked checklist are done AND mode equals `scenario.correct_mode`.
  - Branching: `"wrong_branch"` when current step is a terminal, `"completed"` when branch_step_id becomes `None` AND mode is correct, `"procedure_end"` when branch ends without target mode.
  - Timeout: `"timeout"` when `elapsed >= condition.time_limit` (non-familiarization only).
- `aggregate_errors(result: TrialResult) -> int` — sum of `order_errors + wrong_mode_actions + branch_decision_errors + checklist_selection_error`. Used by `summary.py` screen.

**Circular-import note:** `scoring.py` type-hints `TrialEngine` as a forward reference via `TYPE_CHECKING`, since engine calls into scoring. Scoring reads only `engine.scenario`, `engine.condition`, `engine.mode`, `engine.completed_actions`, `engine.branch_step_id`, `engine.branch_path`, and `engine.elapsed(now)` — a narrow surface that makes the dependency easy to reason about.

## UI layer (`sim/ui/`)

### `screens/`

One file per screen, each exporting a single `render()` function. Breakdown of today's `views.py` (654 lines):

| File | Current function(s) | Approx lines |
|---|---|---|
| `intro.py` | `render_intro_instructions` | 60 |
| `sidebar.py` | `render_sidebar_setup` | 60 |
| `masthead.py` | `render_study_header` | 35 |
| `status_bar.py` | `render_status_bar` | 50 |
| `console.py` | `render_console` | 40 |
| `linear.py` | `render_linear_checklist`, `_render_linear_picker`, `_render_linear_progress`, `_render_practice_checklist` | 110 |
| `branching.py` | `render_branching_checklist` | 95 |
| `familiarization_done.py` | `render_familiarization_complete` | 10 |
| `survey.py` | `render_final_survey`, `_tlx_slider` | 85 — now ~40, iterating `domain.survey.QUESTIONS` |
| `summary.py` | `render_session_summary` | 40 |

### `widgets.py`

Replaces `components.py`. Pure render functions, no state. `esc`, `notice`, `section_header`, `trigger_cue_row`, `mode_badge`, `mode_color`, `mode_glow`, `rocket_celebration`, `tlx_slider`.

### `styles.py`

File relocates to `sim/ui/styles.py`; contents and `inject_styles()` function unchanged.

### Screen ↔ engine rule

Screens never mutate `st.session_state` directly. They call `engine.execute_action(...)`, `engine.submit_decision(...)`, etc. The state bridge persists engine state across Streamlit reruns.

## State bridge (`sim/state.py`)

Replaces today's flat dict of ~35 keys with phase-scoped dataclasses stored under namespaced keys in `st.session_state`.

```python
@dataclass
class IdentityState:
    participant_id: str = ""
    experience: str = "None"
    condition_key: Optional[str] = None
    assignment_mode: Literal["auto", "manual"] = "auto"
    session_id: Optional[str] = None
    session_started: bool = False

@dataclass
class SessionState:
    trial_order: tuple[int, ...] = ()
    trial_index: int = 0
    did_familiarization: bool = False
    in_familiarization: bool = False
    all_summaries: list[TrialResult] = field(default_factory=list)
    session_finished: bool = False
    session_survey_submitted: bool = False
    data_sink: Optional[str] = None  # "google_sheets" or a local CSV path, matching today's `persist()` return value

@dataclass
class TrialEngineSnapshot:
    # Serialized form of a TrialEngine — rehydrated at the start of each rerun.
    scenario_id: Optional[int]
    is_familiarization: bool
    mode: Optional[str]
    completed_actions: list[str]
    wrong_mode_actions: int
    order_errors: int
    selected_checklist_id: Optional[int]
    checklist_selection_error: bool
    branch_step_id: Optional[int]
    branch_path: list[int]
    branch_decision_errors: int
    start_time: Optional[float]
    completion_time: Optional[float]
    end_reason: Optional[EndReason]
    finished: bool
    trial_events: list[TrialEvent]
```

**Bridge functions:**

- `init_state()` — installs defaults on first run (same behavior as today).
- `identity() -> IdentityState`, `session() -> SessionState` — typed accessors.
- `load_engine() -> Optional[TrialEngine]` — rebuilds from snapshot at the start of each rerun. Returns `None` if no trial is active.
- `save_engine(engine: TrialEngine) -> None` — serializes snapshot before rerun.
- `reset_trial_state()` — clears the snapshot and deletes dynamic widget keys (`branch_decision_*`, `checklist_pick_*`). Same behavior as today.

Streamlit's own widget state (`tlx_mental`, `branch_decision_3`, etc.) stays in `st.session_state` raw — widget keys are Streamlit's territory.

**Derived flags.** Today's `st.session_state.trial_started`, `st.session_state.scenario`, `st.session_state.mode`, `st.session_state.completion_time`, `st.session_state.end_reason`, and `st.session_state.finished` are eliminated as stored flags and become derivations off the loaded engine:

- `trial_started` → `engine is not None`
- `scenario` → `engine.scenario` when engine exists
- `mode` → `engine.mode`
- `completion_time` / `end_reason` / `finished` → `engine.result().completion_time_s` / `engine.end_reason()` / `engine.is_finished()`

Screens read these off the engine directly; nothing extra is stored.

**Assignment emission.** `io.sinks.record_assignment(...)` is called once per session from the session-start path (what `start_session` does today in `trial.py:117`), not per trial. The bridge assembles the assignment row from `IdentityState` + `Condition` + `SessionState.trial_order` at that moment.

**Serialization for sinks.**

- **Events:** engine produces `TrialEvent` objects with only engine-level data (timestamp, mode, action, extras). The bridge exposes `serialize_events(events, context: TrialContext, condition: Condition, scenario: Scenario) -> list[dict]` which enriches each event with the frozen `events`-worksheet columns (`session_id`, `participant_id`, `experience`, `condition`, `checklist_type`, `is_familiarization`, `trial_number`, `scenario_id`, `timestamp_s`, `mode`, `action`, plus event-specific extras from `event.extra`). Dicts go to `io.sinks.persist("events", ...)`.
  - **Familiarization quirk:** when `scenario.is_familiarization`, `checklist_type` in the row is `"practice"`, not `condition.checklist_type`. Matches today's `_log_event` at `trial.py:180`.
- **Summaries:** `TrialResult` field names match the `summaries` column set exactly, so the bridge serializes with `dataclasses.asdict(result)`. The survey submission step merges in the NASA-TLX fields before calling `io.sinks.persist("summaries", rows)` — same behavior as today's `submit_session_survey`.
- Google Sheets' `_append_sheet` already reconciles columns by name (existing behavior), so new output fields added in the future simply append as new columns; frozen fields never rename or drop.

## IO layer (`sim/io/`)

- `sim/sinks.py` → `sim/io/sinks.py`. Public surface unchanged: `persist(name, rows)`, `record_assignment(assignment)`, `read_assignment_counts()`, and a `balanced_condition(experience, condition_keys)` wrapper that reads counts from Sheets and delegates to the pure version in `domain/conditions.py`.
  - Two functions share the name `balanced_condition` — the pure one in `sim.domain.conditions` (takes counts as an arg, unit-testable) and the I/O wrapper in `sim.io.sinks` (reads counts, then delegates). UI imports from `sim.io.sinks`; tests import from `sim.domain.conditions`. Same name, different modules — intentional.
- Auth and worksheet plumbing (`_get_sheet_client`, `_get_spreadsheet`, `_get_worksheet`, `_append_sheet`) move to `sim/io/_sheets.py`. Mechanical split, no behavior change.
- `LOG_DIR` and `GOOGLE_SCOPES` move into `sim/io/_sheets.py`.
- Output column sets for `assignments`, `events`, `summaries` are preserved byte-for-byte.
- `sim/config.py` is deleted once all constants have been moved out.

## Testing (`tests/`)

New top-level `tests/` directory. `pytest` added to a new `requirements-dev.txt` (keeps prod deps clean).

### `conftest.py`

Shared fixtures the engine tests rely on. Provides factory functions that build:

- A minimal linear `Scenario` with 3 steps, one with an `action_expected_modes` entry.
- A minimal branching `Scenario` with one decision and a terminal step.
- A `Condition` with `time_limit=60`.
- A `TrialContext` with dummy identity fields.

Each test composes these into a `TrialEngine` with an explicit `start_time=0.0` so `now` is always an ordinal.

### `test_engine.py`

Drives `TrialEngine` with small inline scenario fixtures (not the real scenarios — keeps tests readable).

Cases:

- **Familiarization:** single-step completion → `end_reason == "completed"`
- **Linear, correct order:** all steps in order → completed; `order_errors == 0`
- **Linear, wrong step in position 3:** `order_errors` increments; action still records
- **Linear, wrong mode:** action with `expected_mode = "HOLD"` clicked while in "AUTO" → `wrong_mode_actions` increments
- **Linear, wrong checklist picked:** `checklist_selection_error == True`, trial continues with chosen procedure
- **Branching, correct path:** decision routes to correct next; `branch_path` matches expected sequence
- **Branching, wrong critical decision:** routes to terminal step 99 → `end_reason == "wrong_branch"`
- **Branching, retry loop:** wrong decision with `next` pointing back → `branch_decision_errors` increments, path loops
- **Timeout:** `tick(now=start+time_limit)` → `end_reason == "timeout"`
- **Auto-transition:** `tick(now=start+auto_transition.time)` → mode changes, event logged
- **Output schema lock:** call `result()` after a completed trial and assert `set(dataclasses.asdict(result).keys()) == FROZEN_SUMMARY_KEYS` where `FROZEN_SUMMARY_KEYS` is a module-level constant. Same assertion for `TrialEvent` via the bridge's `serialize_events` output against `FROZEN_EVENT_KEYS`. This is the safety net that catches any drift in the `summaries` / `events` worksheet columns.

### `test_scoring.py`

- `classify_end` for each EndReason input (parameterized)
- `aggregate_errors` sums all four error kinds

### `test_registry.py`

- `get_all()` returns 3 real scenarios
- `get_by_id(999)` raises `KeyError`
- Every real `SCENARIO` constructs cleanly (catches dataclass regressions when scenarios are edited)

### `test_conditions.py`

- `balanced_condition` with empty counts → first key
- Ties broken by overall count
- Unknown experience → treated as zero

### `test_smoke.py`

- Imports every module under `sim/` (catches broken imports, circular deps, syntax errors)
- Constructs a `TrialEngine` for each real scenario and runs it to completion programmatically using fabricated `now` values — verifies domain end-to-end without Streamlit

### What is NOT tested

- UI rendering (screens, widgets)
- Streamlit state bridge rehydration
- Google Sheets IO (real network)

These are integration concerns. Manual click-through before merge covers the UI; Sheets IO is exercised by actual sessions during trials.

## Migration sequence

Each commit lands on `refactor/cleanup-2026-04`, leaves the app runnable, and can be reviewed on its own.

1. **Introduce `tests/` scaffold** — pytest config, `requirements-dev.txt`, one trivial passing test. No app changes.
2. **Extract domain models + populate registry** — `sim/domain/models.py` with all dataclasses; convert today's `NAV`/`THERMAL`/`COMM`/`FAMILIARIZATION` dicts into `Scenario` instances in `sim/domain/scenarios/*.py`; add `registry.py`. `sim/scenarios.py` becomes a thin re-export shim so callers (`sim/trial.py`, `sim/views.py`) keep working with no changes. `test_registry.py` lands with this step.
3. **Extract conditions + survey + action_help** — `sim/domain/conditions.py`, `sim/domain/survey.py`, `sim/domain/action_help.py`. `sim/config.py` shrinks to just `LOG_DIR`/`GOOGLE_SCOPES` pending step 5. `test_conditions.py` lands with this step.
4. **Extract `TrialEngine` + scoring** — biggest commit. Logic moves out of `sim/trial.py` into `sim/domain/engine.py` and `sim/domain/scoring.py`. `sim/trial.py` becomes the bridge to `st.session_state`, using the new engine. `test_engine.py` + `test_scoring.py` land with this step.
5. **Relocate IO** — `sim/sinks.py` → `sim/io/sinks.py` + `sim/io/_sheets.py`. Move `LOG_DIR` and `GOOGLE_SCOPES` into `sim/io/_sheets.py`. Wire `balanced_condition` wrapper. Delete `sim/config.py`.
6. **Split `views.py` into `ui/screens/`** — one screen per file. `sim/components.py` → `sim/ui/widgets.py`. `sim/styles.py` → `sim/ui/styles.py`. Update `simulator.py` imports.
7. **Finalize state bridge** — phase-scoped dataclasses in `sim/state.py`. Add `serialize_events(...)`. Remove any backwards-compat shims from earlier steps (e.g. the re-export shim in `sim/scenarios.py`, the shim in `sim/trial.py`).
8. **Add smoke test** — `tests/test_smoke.py`: imports every module + drives every real scenario through the engine to completion.
9. **Cleanup** — delete dead imports, dead files. `pytest` passes. App boots. One linear trial and one branching trial completed end-to-end in a browser — either by Irfan before pushing, or by Varsha during review.

Each commit's diff is reviewable in under 10 minutes. Varsha can merge incrementally if she prefers, or wait for the final PR.

## Risks and mitigations

- **Risk:** state-bridge rehydration has a subtle bug that unit tests miss → trial state corrupts mid-session.
  **Mitigation:** smoke test runs a full scenario through the engine in-process (catches engine/scoring drift). Browser-level click-through by Irfan or Varsha catches bridge drift — this is the one step that can't be automated without adding a Streamlit-level integration test, which is out of scope.

- **Risk:** output schema accidentally drifts → breaks data team analysis.
  **Mitigation:** `TrialResult` dataclass field names match current `summaries` columns exactly; `dataclasses.asdict(result)` is the serialization path. `test_engine.py` asserts the result dict keys against a frozen constant. Event-row columns are asserted the same way against a frozen list in `test_engine.py`.

- **Risk:** one of the 9 commits leaves the app broken for a reviewer checking out mid-sequence.
  **Mitigation:** each step keeps old call sites working via temporary shims; final cleanup commit removes them.

- **Risk:** refactor drags scope (tempting to fix data team items along the way).
  **Mitigation:** explicit non-goal in this spec. If a data team item is touched during refactor, it ships unchanged and is fixed in a follow-up PR.

## What this enables (post-refactor)

Not committing to timing — just noting where future data team items will land:

- **Live timer fix:** check `streamlit-autorefresh` install, one-line fix in `ui/screens/status_bar.py`.
- **Auto-terminate on timeout:** already works; will be covered by `test_engine.py::test_timeout` afterwards.
- **Interface trim (only buttons/checklist/timer/spacecraft state):** edit screen files individually; no engine touch.
- **Group balancing refinement:** edit pure `domain/conditions.balanced_condition`, add test case.
- **4th scenario:** new file in `domain/scenarios/`, one line in `registry.py`.
- **Static checklist stretch:** add an optional `static_checklist: Optional[LinearChecklist]` field on `Scenario` and a new screen file to render it (reference-only, no engine interaction). Engine and scoring untouched.
- **Rocketships instead of balloons:** swap `widgets.rocket_celebration` contents.
- **Survey rewording / new questions:** edit `domain/survey.QUESTIONS`, no UI change needed.
