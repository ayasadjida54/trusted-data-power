"""
services.sheets_connector

Fetches a Google Sheet's data WITHOUT OAuth: Google Sheets exposes a
public CSV export endpoint for any sheet shared as "Anyone with the
link can view" (or fully public). This is deliberately the first
ingestion method (Phase 8) rather than a full OAuth integration -
OAuth would need a registered Google Cloud project, client
secret, and consent-screen review, none of which is something this
codebase can supply on a user's behalf. The CSV-export approach works
today, for any publicly-viewable sheet, with zero external setup - the
trade-off is that it can't read a PRIVATE sheet. Full OAuth (reading
private sheets on a user's behalf) is future work if this connector
proves useful and private-sheet access becomes a real request.

URL formats accepted:
    https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=<GID>
    https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit?usp=sharing
    https://docs.google.com/spreadsheets/d/<SHEET_ID>
A missing gid defaults to 0 (the first tab).
"""

import io
import re

import pandas as pd
import requests

SHEET_ID_PATTERN = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")
GID_PATTERN = re.compile(r"[#&?]gid=(\d+)")

REQUEST_TIMEOUT_SECONDS = 15


class InvalidSheetUrl(ValueError):
    pass


class SheetFetchError(ValueError):
    pass


def parse_sheet_url(url: str) -> tuple[str, str]:
    """Returns (spreadsheet_id, gid). Raises InvalidSheetUrl if `url`
    doesn't look like a Google Sheets URL at all."""
    id_match = SHEET_ID_PATTERN.search(url or "")
    if not id_match:
        raise InvalidSheetUrl(
            "That doesn't look like a Google Sheets URL. Expected something like "
            "https://docs.google.com/spreadsheets/d/.../edit"
        )
    gid_match = GID_PATTERN.search(url)
    gid = gid_match.group(1) if gid_match else "0"
    return id_match.group(1), gid


def build_csv_export_url(spreadsheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"


def fetch_sheet_as_dataframe(sheet_url: str) -> pd.DataFrame:
    """
    Fetch a public Google Sheet and parse it into a DataFrame.

    Raises InvalidSheetUrl if the URL isn't a recognizable Sheets link,
    or SheetFetchError (with a message meant to be shown to the user
    directly) if the request fails, the sheet isn't publicly viewable,
    or the response isn't parseable CSV.
    """
    spreadsheet_id, gid = parse_sheet_url(sheet_url)
    export_url = build_csv_export_url(spreadsheet_id, gid)

    try:
        response = requests.get(export_url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise SheetFetchError(f"Couldn't reach Google Sheets: {exc}")

    if response.status_code == 404:
        raise SheetFetchError("This sheet wasn't found. Check the link and try again.")

    # A private sheet's export request doesn't 401/403 - Google
    # redirects to an HTML login/error page and returns 200, so a
    # content-type check is the reliable signal here, not status code.
    content_type = response.headers.get("content-type", "")
    if response.status_code != 200 or "text/csv" not in content_type:
        raise SheetFetchError(
            "Couldn't read this sheet. Make sure it's shared as "
            "\"Anyone with the link can view\" and try again."
        )

    try:
        return pd.read_csv(io.StringIO(response.text))
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise SheetFetchError(f"This sheet's data couldn't be parsed: {exc}")
