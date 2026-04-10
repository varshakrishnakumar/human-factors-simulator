# Analysis Data

The deployed Streamlit app should keep writing study data to Google Sheets.
This folder is for pulling that data down into local CSV files for analysis.

## Current sheet

- Spreadsheet ID: `1ahDKB4ljOU2U8iP-GQBJTZHrXz1Xm2sMZI0Kab769Ok`
- Worksheets: `events`, `summaries`

## Pull the latest data

If you already use `.streamlit/secrets.toml` for the deployed app credentials, the script will reuse it locally.

```bash
python3 analysis/fetch_google_sheets.py
```

That writes:

- `analysis/events.csv`
- `analysis/summaries.csv`

## Credential options

The script looks for credentials in this order:

1. `.streamlit/secrets.toml`
2. `GOOGLE_SERVICE_ACCOUNT_JSON`
3. `GOOGLE_SERVICE_ACCOUNT_FILE`
