"""
test_monitoring.py

Phase 7 tests: monitoring settings CRUD, and automatic alert creation
when a monitored dataset's score drops past its threshold.
"""

import os

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "engine", "tests", "sample_messy_data.csv"
)
CLEAN_CSV = b"product,price,in_stock\nWidget,10.0,true\nGadget,25.5,true\nGizmo,7.25,false\n"
# Deliberately much worse than the sample data - many missing values -
# so uploading it after a clean run produces a large, reliable score drop.
VERY_MESSY_CSV = (
    b"product,price,in_stock\n"
    b",,\n"
    b",,\n"
    b",25.5,true\n"
    b",,\n"
)


def _sample_csv_bytes() -> bytes:
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return f.read()


def _upload(client, headers, content, filename="data.csv", **params):
    files = {"file": (filename, content, "text/csv")}
    return client.post("/api/datasets/upload", files=files, params=params, headers=headers)


def test_new_dataset_has_monitoring_disabled_by_default(client, auth_headers):
    upload = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Monitor Default Test")
    dataset_id = upload.json()["dataset_id"]

    response = client.get(f"/api/datasets/{dataset_id}/monitoring", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["monitoring_enabled"] is False
    assert response.json()["alert_threshold_points"] == 5.0


def test_update_monitoring_settings(client, auth_headers):
    upload = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Monitor Update Test")
    dataset_id = upload.json()["dataset_id"]

    response = client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 10.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["monitoring_enabled"] is True
    assert response.json()["alert_threshold_points"] == 10.0

    get_response = client.get(f"/api/datasets/{dataset_id}/monitoring", headers=auth_headers)
    assert get_response.json()["monitoring_enabled"] is True


def test_monitoring_settings_reject_non_positive_threshold(client, auth_headers):
    upload = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Monitor Validation Test")
    dataset_id = upload.json()["dataset_id"]

    response = client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_monitoring_settings_for_nonexistent_dataset_returns_404(client, auth_headers):
    response = client.get("/api/datasets/999999/monitoring", headers=auth_headers)
    assert response.status_code == 404


def test_no_alert_when_monitoring_disabled_even_on_big_drop(client, auth_headers):
    first = _upload(client, auth_headers, CLEAN_CSV, dataset_name="No Monitor Drop Test")
    dataset_id = first.json()["dataset_id"]
    # monitoring left disabled (default)
    _upload(client, auth_headers, VERY_MESSY_CSV, dataset_id=dataset_id)

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    assert all(a["dataset_id"] != dataset_id for a in alerts)


def test_no_alert_when_drop_is_below_threshold(client, auth_headers):
    first = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Small Drop Test")
    dataset_id = first.json()["dataset_id"]
    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 99.0},
        headers=auth_headers,
    )
    # Re-uploading the identical clean file: score delta is 0, well under 99.
    _upload(client, auth_headers, CLEAN_CSV, dataset_id=dataset_id)

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    assert all(a["dataset_id"] != dataset_id for a in alerts)


def test_alert_created_when_monitored_and_drop_exceeds_threshold(client, auth_headers):
    first = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Big Drop Test")
    dataset_id = first.json()["dataset_id"]
    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 5.0},
        headers=auth_headers,
    )
    second = _upload(client, auth_headers, VERY_MESSY_CSV, dataset_id=dataset_id)
    assert second.json()["score"] < first.json()["score"]

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    matching = [a for a in alerts if a["dataset_id"] == dataset_id]
    assert len(matching) == 1
    alert = matching[0]
    assert alert["previous_run_id"] == first.json()["id"]
    assert alert["current_run_id"] == second.json()["id"]
    assert alert["score_delta"] < 0
    assert alert["is_read"] is False
    assert len(alert["summary"]) > 0


def test_first_upload_never_creates_an_alert(client, auth_headers):
    # No previous run to compare against, even with monitoring enabled
    # and a terrible score - there's nothing to have "dropped" from.
    upload = _upload(client, auth_headers, VERY_MESSY_CSV, dataset_name="First Upload Test")
    dataset_id = upload.json()["dataset_id"]
    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 1.0},
        headers=auth_headers,
    )
    alerts = client.get("/api/alerts", headers=auth_headers).json()
    assert all(a["dataset_id"] != dataset_id for a in alerts)


def test_mark_alert_as_read(client, auth_headers):
    first = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Mark Read Test")
    dataset_id = first.json()["dataset_id"]
    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 5.0},
        headers=auth_headers,
    )
    _upload(client, auth_headers, VERY_MESSY_CSV, dataset_id=dataset_id)

    alerts = client.get("/api/alerts", headers=auth_headers).json()
    alert_id = [a for a in alerts if a["dataset_id"] == dataset_id][0]["id"]

    read_response = client.post(f"/api/alerts/{alert_id}/read", headers=auth_headers)
    assert read_response.status_code == 200
    assert read_response.json()["is_read"] is True

    unread = client.get("/api/alerts", headers=auth_headers, params={"unread_only": True}).json()
    assert all(a["id"] != alert_id for a in unread)


def test_alerts_are_scoped_to_organization(client, auth_headers):
    first = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Org Scope Test")
    dataset_id = first.json()["dataset_id"]
    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 5.0},
        headers=auth_headers,
    )
    _upload(client, auth_headers, VERY_MESSY_CSV, dataset_id=dataset_id)

    other_register = client.post(
        "/api/auth/register",
        json={"email": "monitor-other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    other_alerts = client.get("/api/alerts", headers=other_headers).json()
    assert all(a["dataset_id"] != dataset_id for a in other_alerts)


def test_mark_read_for_other_orgs_alert_returns_404(client, auth_headers):
    first = _upload(client, auth_headers, CLEAN_CSV, dataset_name="Cross Org Read Test")
    dataset_id = first.json()["dataset_id"]
    client.patch(
        f"/api/datasets/{dataset_id}/monitoring",
        json={"monitoring_enabled": True, "alert_threshold_points": 5.0},
        headers=auth_headers,
    )
    _upload(client, auth_headers, VERY_MESSY_CSV, dataset_id=dataset_id)
    alerts = client.get("/api/alerts", headers=auth_headers).json()
    alert_id = [a for a in alerts if a["dataset_id"] == dataset_id][0]["id"]

    other_register = client.post(
        "/api/auth/register",
        json={"email": "monitor-other-2@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    response = client.post(f"/api/alerts/{alert_id}/read", headers=other_headers)
    assert response.status_code == 404


def test_sample_messy_data_upload_still_works_with_monitoring_wired_in(client, auth_headers):
    # Regression guard: uploading the real sample CSV (no monitoring
    # involved) must be completely unaffected by Phase 7's changes to
    # the upload path.
    response = _upload(client, auth_headers, _sample_csv_bytes(), filename="sample_messy_data.csv")
    assert response.status_code == 200
    assert response.json()["score"] < 100
