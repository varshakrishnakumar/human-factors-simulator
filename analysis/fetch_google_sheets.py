import argparse
import json
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

DEFAULT_SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1ahDKB4ljOU2U8iP-GQBJTZHrXz1Xm2sMZI0Kab769Ok/edit"
)
DEFAULT_WORKSHEETS = ("events", "summaries")
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
SECRETS_PATH = REPO_DIR / ".streamlit" / "secrets.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Google Sheets experiment tabs into analysis CSV files."
    )
    parser.add_argument(
        "--spreadsheet",
        default=DEFAULT_SPREADSHEET_URL,
        help="Google Sheets URL or spreadsheet ID.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR),
        help="Directory where CSV files will be written.",
    )
    parser.add_argument(
        "--worksheets",
        nargs="+",
        default=list(DEFAULT_WORKSHEETS),
        help="Worksheet titles to download.",
    )
    return parser.parse_args()


def extract_spreadsheet_id(value: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    return match.group(1) if match else value.strip()


def load_secrets_file() -> dict:
    if tomllib is None or not SECRETS_PATH.exists():
        return {}
    with SECRETS_PATH.open("rb") as handle:
        return tomllib.load(handle)


def load_service_account_info() -> dict:
    secrets = load_secrets_file()
    if "gcp_service_account" in secrets:
        return secrets["gcp_service_account"]

    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        return json.loads(raw_json)

    json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if json_path:
        with open(json_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    raise RuntimeError(
        "No Google service account credentials found. "
        "Add .streamlit/secrets.toml or set GOOGLE_SERVICE_ACCOUNT_JSON / "
        "GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def worksheet_to_frame(worksheet, pd_module):
    values = worksheet.get_all_values()
    if not values:
        return pd_module.DataFrame()

    headers = values[0]
    rows = values[1:]
    if not rows:
        return pd_module.DataFrame(columns=headers)

    return pd_module.DataFrame(rows, columns=headers)


def main() -> None:
    args = parse_args()

    try:
        import gspread
        import pandas as pd
        from google.oauth2.service_account import Credentials
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency for Google Sheets download. "
            "Install the project requirements first."
        ) from exc

    spreadsheet_id = extract_spreadsheet_id(args.spreadsheet)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    creds = Credentials.from_service_account_info(
        load_service_account_info(),
        scopes=GOOGLE_SCOPES,
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)

    for worksheet_name in args.worksheets:
        worksheet = spreadsheet.worksheet(worksheet_name)
        frame = worksheet_to_frame(worksheet, pd)
        output_path = output_dir / f"{worksheet_name}.csv"
        frame.to_csv(output_path, index=False)
        print(f"Wrote {len(frame)} rows to {output_path}")


if __name__ == "__main__":
    main()
