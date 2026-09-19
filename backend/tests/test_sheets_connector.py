"""
test_sheets_connector.py

Unit tests for services.sheets_connector. All HTTP calls are mocked -
this sandbox's network egress doesn't include docs.google.com, so
these tests simulate Google's responses (success, private-sheet HTML
redirect, 404, network failure) rather than hitting the real endpoint.
The connector is written against the well-documented public CSV-export
URL format, so these mocks are a faithful stand-in for what a real
deployment (which has no such network restriction) will actually see.
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

from backend.services.sheets_connector import (
    InvalidSheetUrl,
    SheetFetchError,
    build_csv_export_url,
    fetch_sheet_as_dataframe,
    parse_sheet_url,
)

VALID_URL = "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOp/edit#gid=42"
VALID_URL_NO_GID = "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOp/edit?usp=sharing"


def test_parse_sheet_url_extracts_id_and_gid():
    sheet_id, gid = parse_sheet_url(VALID_URL)
    assert sheet_id == "1AbCdEfGhIjKlMnOp"
    assert gid == "42"


def test_parse_sheet_url_defaults_gid_to_zero(): 
    sheet_id, gid = parse_sheet_url(VALID_URL_NO_GID)
    assert sheet_id == "1AbCdEfGhIjKlMnOp"
    assert gid == "0"


def test_parse_sheet_url_rejects_non_sheets_url():
    with pytest.raises(InvalidSheetUrl):
        parse_sheet_url("https://example.com/not-a-sheet")


def test_parse_sheet_url_rejects_empty_string():
    with pytest.raises(InvalidSheetUrl):
        parse_sheet_url("")


def test_build_csv_export_url_format():
    url = build_csv_export_url("ABC123", "5")
    assert url == "https://docs.google.com/spreadsheets/d/ABC123/export?format=csv&gid=5"


def _mock_response(status_code=200, content_type="text/csv", text=""):
    response = Mock()
    response.status_code = status_code
    response.headers = {"content-type": content_type}
    response.text = text
    return response


def test_fetch_sheet_as_dataframe_success():
    csv_text = "product,price\nWidget,10.0\nGadget,25.5\n"
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(200, "text/csv; charset=utf-8", csv_text)
        df = fetch_sheet_as_dataframe(VALID_URL)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["product", "price"]
    assert len(df) == 2
    # Confirms the real export URL (with the parsed id/gid) was called.
    called_url = mock_get.call_args[0][0]
    assert "1AbCdEfGhIjKlMnOp" in called_url
    assert "gid=42" in called_url


def test_fetch_sheet_as_dataframe_rejects_bad_url():
    with pytest.raises(InvalidSheetUrl):
        fetch_sheet_as_dataframe("not a url at all")


def test_fetch_sheet_as_dataframe_404():
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(404, "text/html", "")
        with pytest.raises(SheetFetchError, match="wasn't found"):
            fetch_sheet_as_dataframe(VALID_URL)


def test_fetch_sheet_as_dataframe_private_sheet_returns_html():
    # Google's real behavior for a private sheet: 200 status, but an
    # HTML login/error page instead of CSV - status code alone can't
    # detect this, which is exactly why the connector checks content-type.
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(200, "text/html; charset=utf-8", "<html>...</html>")
        with pytest.raises(SheetFetchError, match="Anyone with the link"):
            fetch_sheet_as_dataframe(VALID_URL)


def test_fetch_sheet_as_dataframe_network_error():
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("DNS failure")
        with pytest.raises(SheetFetchError, match="Couldn't reach"):
            fetch_sheet_as_dataframe(VALID_URL)


def test_fetch_sheet_as_dataframe_empty_csv():
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(200, "text/csv", "")
        with pytest.raises(SheetFetchError):
            fetch_sheet_as_dataframe(VALID_URL)
