"""
test_upload.py

Phase 1-4 API tests, exercising the full upload -> store -> retrieve
flow through real HTTP calls (FastAPI's TestClient), against an
isolated temp SQLite database (see conftest.py). Every request now
requires auth (see auth_headers fixture) and is scoped to the
requesting user's organization.
"""

import os

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "engine", "tests", "sample_messy_data.csv"
)


def _sample_csv_bytes() -> bytes:
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return f.read()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_returns_full_analysis(client, auth_headers):
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    response = client.post("/api/datasets/upload", files=files, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()

    assert body["filename"] == "sample_messy_data.csv"
    assert 0 <= body["score"] <= 100
    assert body["score"] < 100  # known messy sample
    assert body["score_label"] in {"Strong", "Moderate", "Weak", "Poor"}
    assert isinstance(body["issues"], list) and len(body["issues"]) > 0
    assert isinstance(body["recommendations"], list)
    assert "dataset_id" in body
    assert "id" in body

    assert isinstance(body["score_explanation"], list) and len(body["score_explanation"]) > 0
    assert isinstance(body["column_scores"], dict)
    assert set(body["column_scores"].keys()) == {
        "id", "name", "category", "amount", "signup_date", "notes"
    }
    for column_result in body["column_scores"].values():
        assert 0 <= column_result["score"] <= 100
        assert "explanation" in column_result


def test_uploaded_run_is_retrievable_by_id(client, auth_headers):
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    upload_response = client.post("/api/datasets/upload", files=files, headers=auth_headers)
    run_id = upload_response.json()["id"]

    get_response = client.get(f"/api/runs/{run_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == run_id
    assert get_response.json()["score"] == upload_response.json()["score"]


def test_dataset_latest_run_endpoint(client, auth_headers):
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    upload_response = client.post("/api/datasets/upload", files=files, headers=auth_headers)
    dataset_id = upload_response.json()["dataset_id"]

    latest_response = client.get(f"/api/datasets/{dataset_id}/latest", headers=auth_headers)
    assert latest_response.status_code == 200
    assert latest_response.json()["dataset_id"] == dataset_id
    assert latest_response.json()["id"] == upload_response.json()["id"]


def test_list_datasets_includes_uploaded_dataset(client, auth_headers):
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    upload_response = client.post("/api/datasets/upload", files=files, headers=auth_headers)
    dataset_id = upload_response.json()["dataset_id"]

    list_response = client.get("/api/datasets", headers=auth_headers)
    assert list_response.status_code == 200
    dataset_ids = [d["id"] for d in list_response.json()]
    assert dataset_id in dataset_ids


def test_upload_with_custom_dataset_name(client, auth_headers):
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    response = client.post(
        "/api/datasets/upload",
        files=files,
        params={"dataset_name": "Monthly Sales Export"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    dataset_id = response.json()["dataset_id"]

    list_response = client.get("/api/datasets", headers=auth_headers)
    named = [d for d in list_response.json() if d["id"] == dataset_id]
    assert named and named[0]["name"] == "Monthly Sales Export"


def test_unsupported_file_type_returns_400(client, auth_headers):
    files = {"file": ("data.txt", b"not a real dataset", "text/plain")}
    response = client.post("/api/datasets/upload", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_empty_csv_returns_400(client, auth_headers):
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/api/datasets/upload", files=files, headers=auth_headers)
    assert response.status_code == 400


def test_get_nonexistent_run_returns_404(client, auth_headers):
    response = client.get("/api/runs/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_latest_for_nonexistent_dataset_returns_404(client, auth_headers):
    response = client.get("/api/datasets/999999/latest", headers=auth_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Multi-tenancy: the whole point of Phase 4's organization scoping.
# ---------------------------------------------------------------------

def test_users_in_different_organizations_do_not_see_each_others_datasets(
    client, auth_headers
):
    # auth_headers belongs to organization A.
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    upload_response = client.post("/api/datasets/upload", files=files, headers=auth_headers)
    dataset_id = upload_response.json()["dataset_id"]
    run_id = upload_response.json()["id"]

    # A second, independent user registers into their OWN new organization.
    other_register = client.post(
        "/api/auth/register",
        json={"email": "other-org-user@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    # Organization B's list of datasets must not include organization A's.
    list_response = client.get("/api/datasets", headers=other_headers)
    assert dataset_id not in [d["id"] for d in list_response.json()]

    # Direct access to organization A's dataset/run from organization B
    # must 404, not 200 and not 403 (existence shouldn't be confirmed).
    latest_response = client.get(f"/api/datasets/{dataset_id}/latest", headers=other_headers)
    assert latest_response.status_code == 404

    run_response = client.get(f"/api/runs/{run_id}", headers=other_headers)
    assert run_response.status_code == 404
