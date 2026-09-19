"""
test_datasources.py

Phase 8 integration tests: linking a dataset to a (mocked) Google
Sheet, syncing, unlinking, error handling, and confirming a sheet sync
that drops the score feeds into Phase 7's alert detection exactly like
a file upload does.
"""

from unittest.mock import Mock, patch

VALID_URL = "https://docs.google.com/spreadsheets/d/1TestSheetId/edit#gid=0"
CLEAN_CSV = "product,price,in_stock\nWidget,10.0,true\nGadget,25.5,true\nGizmo,7.25,false\n"
BROKEN_CSV = "product,price,in_stock\n,,\n,,\n,25.5,true\n"


def _mock_response(text, status_code=200, content_type="text/csv"):
    response = Mock()
    response.status_code = status_code
    response.headers = {"content-type": content_type}
    response.text = text
    return response


def test_connect_sheet_creates_dataset_and_run(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        response = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Sheet Test"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 100.0
    assert "Google Sheet" in body["filename"]


def test_connect_sheet_with_bad_url_returns_400_and_creates_nothing(client, auth_headers):
    response = client.post(
        "/api/datasets/connect-sheet",
        json={"sheet_url": "not-a-real-url", "dataset_name": "Bad URL Test"},
        headers=auth_headers,
    )
    assert response.status_code == 400

    datasets = client.get("/api/datasets", headers=auth_headers).json()
    assert all(d["name"] != "Bad URL Test" for d in datasets)


def test_connect_sheet_with_private_sheet_returns_400(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response("<html>login</html>", 200, "text/html")
        response = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Private Sheet Test"},
            headers=auth_headers,
        )
    assert response.status_code == 400
    assert "Anyone with the link" in response.json()["detail"]


def test_get_datasource_after_linking(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        connect = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Datasource Status Test"},
            headers=auth_headers,
        )
    dataset_id = connect.json()["dataset_id"]

    response = client.get(f"/api/datasets/{dataset_id}/datasource", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "google_sheets"
    assert body["source_url"] == VALID_URL
    assert body["last_sync_status"] == "success"
    assert body["last_synced_at"] is not None


def test_sync_now_creates_a_new_run(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        connect = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Sync Now Test"},
            headers=auth_headers,
        )
    dataset_id = connect.json()["dataset_id"]
    first_run_id = connect.json()["id"]

    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        sync_response = client.post(f"/api/datasets/{dataset_id}/sync-now", headers=auth_headers)

    assert sync_response.status_code == 200
    assert sync_response.json()["id"] != first_run_id

    runs = client.get(f"/api/datasets/{dataset_id}/runs", headers=auth_headers).json()
    assert len(runs) == 2


def test_sync_now_without_a_linked_source_returns_400(client, auth_headers):
    files = {"file": ("data.csv", CLEAN_CSV.encode(), "text/csv")}
    upload = client.post(
        "/api/datasets/upload",
        files=files,
        params={"dataset_name": "No Source Test"},
        headers=auth_headers,
    )
    dataset_id = upload.json()["dataset_id"]

    response = client.post(f"/api/datasets/{dataset_id}/sync-now", headers=auth_headers)
    assert response.status_code == 400


def test_sync_now_with_unreachable_sheet_records_error_and_returns_502(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        connect = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Sync Failure Test"},
            headers=auth_headers,
        )
    dataset_id = connect.json()["dataset_id"]

    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response("", 404, "text/html")
        sync_response = client.post(f"/api/datasets/{dataset_id}/sync-now", headers=auth_headers)

    assert sync_response.status_code == 502

    datasource = client.get(f"/api/datasets/{dataset_id}/datasource", headers=auth_headers).json()
    assert datasource["last_sync_status"] == "error"
    assert datasource["last_sync_error"] is not None


def test_unlink_datasource(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        connect = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Unlink Test"},
            headers=auth_headers,
        )
    dataset_id = connect.json()["dataset_id"]

    delete_response = client.delete(f"/api/datasets/{dataset_id}/datasource", headers=auth_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/datasets/{dataset_id}/datasource", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json() is None


def test_reconnecting_a_sheet_to_an_existing_dataset_updates_the_url(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        first = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Relink Test"},
            headers=auth_headers,
        )
    dataset_id = first.json()["dataset_id"]

    new_url = "https://docs.google.com/spreadsheets/d/1DifferentSheetId/edit#gid=0"
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": new_url, "dataset_id": dataset_id},
            headers=auth_headers,
        )

    datasource = client.get(f"/api/datasets/{dataset_id}/datasource", headers=auth_headers).json()
    assert datasource["source_url"] == new_url


def test_datasource_endpoints_are_org_scoped(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        connect = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Org Scope Sheet Test"},
            headers=auth_headers,
        )
    dataset_id = connect.json()["dataset_id"]

    other_register = client.post(
        "/api/auth/register",
        json={"email": "sheet-other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    response = client.get(f"/api/datasets/{dataset_id}/datasource", headers=other_headers)
    assert response.status_code == 404


def test_sheet_sync_score_drop_triggers_phase_7_alert(client, auth_headers):
    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(CLEAN_CSV)
        connect = client.post(
            "/api/datasets/connect-sheet",
            json={"sheet_url": VALID_URL, "dataset_name": "Sheet Alert Test"},
            headers=auth_headers,
        )
    dataset_id = connect.json()["dataset_id"]

    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 5.0},
        headers=auth_headers,
    )

    with patch("backend.services.sheets_connector.requests.get") as mock_get:
        mock_get.return_value = _mock_response(BROKEN_CSV)
        sync_response = client.post(f"/api/datasets/{dataset_id}/sync-now", headers=auth_headers)

    assert sync_response.json()["score"] < connect.json()["score"]

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    matching = [a for a in alerts if a["dataset_id"] == dataset_id]
    assert len(matching) == 1
    assert matching[0]["score_delta"] < 0
