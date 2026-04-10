# ASTE 561 Navigation Fault Recovery Simulator

Streamlit-based experiment app for testing checklist design during off-nominal spacecraft mode transitions.

The current version implements the Appendix B navigation fault recovery scenario from the ASTE 561 project description and compares:

- `linear` vs. `branching` checklists
- `high` vs. `low` time pressure

It is designed for a deployed website workflow where participant data is written to Google Sheets, then pulled into this repo for analysis.

## What This Repo Does

- Runs a study-ready Streamlit simulator with a mission-control-style UI
- Presents one Appendix B navigation fault recovery scenario
- Logs participant actions, timing, verification checks, and summary outcomes
- Writes data to Google Sheets when secrets are configured
- Falls back to local CSV files when Sheets is unavailable
- Supports subject-group labels for split analysis outputs
- Pulls Google Sheets data into local CSVs for Python/R analysis

## Current Scenario

The simulator currently uses a single scenario:

- `AUTO` mode
- automatic transition to `HOLD` after a navigation fault
- operator must recover to `AUTO`

The scenario definition lives in [scenario_1.json](scenarios/scenario_1.json).

## Experiment Conditions

The app supports four conditions:

- `linear_high`
- `linear_low`
- `branching_high`
- `branching_low`

Time limits:

- `high`: 45 seconds
- `low`: 90 seconds

## Repo Layout

```text
ASTE561/
├── simulator.py
├── requirements.txt
├── scenarios/
│   └── scenario_1.json
├── analysis/
│   ├── README.md
│   ├── fetch_google_sheets.py
│   ├── events.csv
│   ├── summaries.csv
│   └── by_group/
│       └── <group>/
│           ├── events.csv
│           └── summaries.csv
└── .streamlit/
    └── secrets.toml   # local only, gitignored
```

## Local Setup

Install dependencies with the same Python interpreter you plan to run:

```bash
python -m pip install -r requirements.txt
```

Run the app locally:

```bash
streamlit run simulator.py
```

## Deployed App

The intended participant workflow is to use the deployed Streamlit app rather than running the repo locally.

Important distinction:

- the deployed app can write to Google Sheets
- the deployed app cannot persistently write back into this Git repo
- local `analysis/` CSV files are for analysis on your machine, not for direct storage from the deployed website

## Data Flow

### Primary Path

When Google credentials are configured, the app appends to Google Sheets tabs:

- `events`
- `summaries`

### Fallback Path

If Google Sheets is unavailable, the app writes local CSV files:

- `analysis/events.csv`
- `analysis/summaries.csv`
- `analysis/by_group/<group>/events.csv`
- `analysis/by_group/<group>/summaries.csv`

### Group-Based Logging

The sidebar includes a `Subject group` field.

- If a group is entered, that value is written to every event and summary row as `subject_group`
- If left blank, the app uses the assigned condition as the group label

This makes it easy to split outputs by cohort, treatment arm, pilot batch, or any custom label.

## Google Sheets Configuration

The app expects Streamlit secrets with:

- a Google service account under `[gcp_service_account]`
- a sheet ID under `[google_sheets]`

Example:

```toml
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[google_sheets]
spreadsheet_id = "1ahDKB4ljOU2U8iP-GQBJTZHrXz1Xm2sMZI0Kab769Ok"
```

Notes:

- `.streamlit/secrets.toml` is gitignored
- keep the `\n` escapes inside `private_key`
- the app will create/extend headers in the `events` and `summaries` sheets as needed

## Pulling Data for Analysis

To fetch the current Google Sheets data into local CSV files:

```bash
python analysis/fetch_google_sheets.py
```

That writes:

- `analysis/events.csv`
- `analysis/summaries.csv`
- `analysis/by_group/<group>/events.csv`
- `analysis/by_group/<group>/summaries.csv`

The fetch script reads credentials from:

1. `.streamlit/secrets.toml`
2. `GOOGLE_SERVICE_ACCOUNT_JSON`
3. `GOOGLE_SERVICE_ACCOUNT_FILE`

More detail is in [analysis/README.md](analysis/README.md).

## Current UI

The current interface has been refactored toward a mission-control / spacecraft-console look:

- dark HUD styling
- telemetry cards
- a prominent mode display
- fault-channel panel styling
- checklist panels for linear and branching flows

This is a visual pass only; the study logic still follows the Appendix B scenario structure.

## Metrics Logged

The app logs detailed action-level and trial-level data, including:

- participant ID
- subject group
- condition
- trial number
- timestamps
- mode changes
- wrong-mode actions
- order errors
- mode-check errors
- diagnosis errors
- recovery-check errors
- final-mode-check errors
- omissions
- NASA-TLX responses

## Analysis Notes

Typical workflow:

1. collect participant data through the deployed app
2. write data to Google Sheets
3. pull the latest data into this repo with `analysis/fetch_google_sheets.py`
4. analyze aggregate CSVs or the per-group CSVs under `analysis/by_group/`

## Troubleshooting

### `ModuleNotFoundError: No module named 'gspread'`

You likely installed with one Python and ran with another.

Use:

```bash
python -m pip install -r requirements.txt
python analysis/fetch_google_sheets.py
```

### `No Google service account credentials found`

Your local `.streamlit/secrets.toml` is missing or not populated correctly.

### `Could not deserialize key data`

The `private_key` in `secrets.toml` is malformed. Usually this means the newline formatting is wrong.

### Streamlit slider error with `min_value == max_value`

This repo currently uses one scenario, so the app automatically fixes the trial count at `1`.

## Requirements

See [requirements.txt](requirements.txt):

- `streamlit`
- `pandas`
- `gspread`
- `google-auth`
