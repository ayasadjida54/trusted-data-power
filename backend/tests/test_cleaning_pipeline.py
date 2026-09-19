"""
test_cleaning_pipeline.py

Backend integration tests for POST /api/runs/{run_id}/clean - the real
"Execute DataScore Pipeline" action.
"""

import os

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "engine", "tests", "sample_messy_data.csv"
)


def _sample_csv_bytes() -> bytes:
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return f.read()


def _upload(client, headers, content=None, **params):
    files = {"file": ("sample_messy_data.csv", content or _sample_csv_bytes(), "text/csv")}
    return client.post("/api/datasets/upload", files=files, params=params, headers=headers)


def test_clean_run_produces_a_new_run_with_a_real_higher_score(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="Clean Pipeline Test")

    response = client.post(f"/api/runs/{original.json()['id']}/clean", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["id"] != original.json()["id"]
    assert body["dataset_id"] == original.json()["dataset_id"]
    assert body["score"] >= original.json()["score"]
    assert body["cleaned_from_run_id"] == original.json()["id"]
    assert isinstance(body["cleaning_actions"], list) and len(body["cleaning_actions"]) > 0
    assert "cleaned" in body["filename"].lower()


def test_cleaned_run_appears_in_dataset_history(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="Clean History Test")
    dataset_id = original.json()["dataset_id"]

    clean_response = client.post(f"/api/runs/{original.json()['id']}/clean", headers=auth_headers)

    runs = client.get(f"/api/datasets/{dataset_id}/runs", headers=auth_headers).json()
    run_ids = [r["id"] for r in runs]
    assert original.json()["id"] in run_ids
    assert clean_response.json()["id"] in run_ids
    assert len(runs) == 2


def test_cleaned_run_can_be_compared_against_the_original(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="Clean Compare Test")
    dataset_id = original.json()["dataset_id"]
    cleaned = client.post(f"/api/runs/{original.json()['id']}/clean", headers=auth_headers)

    compare = client.get(
        f"/api/datasets/{dataset_id}/compare",
        params={"run_a": original.json()["id"], "run_b": cleaned.json()["id"]},
        headers=auth_headers,
    )
    assert compare.status_code == 200
    assert compare.json()["score_delta"] >= 0


def test_clean_a_dataset_with_no_issues_reports_no_op(client, auth_headers):
    clean_csv = b"product,price,in_stock\nWidget,10.0,true\nGadget,25.5,true\n"
    original = _upload(client, auth_headers, content=clean_csv, dataset_name="Already Clean Test")

    response = client.post(f"/api/runs/{original.json()['id']}/clean", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["score"] == original.json()["score"]
    assert "no automatic fixes" in response.json()["cleaning_actions"][0].lower()


def test_clean_nonexistent_run_returns_404(client, auth_headers):
    response = client.post("/api/runs/999999/clean", headers=auth_headers)
    assert response.status_code == 404


def test_clean_another_orgs_run_returns_404(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="Clean Org Scope Test")

    other_register = client.post(
        "/api/auth/register",
        json={"email": "clean-other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    response = client.post(f"/api/runs/{original.json()['id']}/clean", headers=other_headers)
    assert response.status_code == 404


def test_clean_requires_auth(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="Clean Auth Test")
    response = client.post(f"/api/runs/{original.json()['id']}/clean")
    assert response.status_code == 401


def test_cleaning_a_cleaned_run_again_works_and_finds_nothing_left(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="Double Clean Test")
    first_clean = client.post(f"/api/runs/{original.json()['id']}/clean", headers=auth_headers)

    second_clean = client.post(f"/api/runs/{first_clean.json()['id']}/clean", headers=auth_headers)
    assert second_clean.status_code == 200
    assert second_clean.json()["score"] == first_clean.json()["score"]
    assert second_clean.json()["cleaned_from_run_id"] == first_clean.json()["id"]


def test_ordinary_runs_have_no_cleaning_lineage(client, auth_headers):
    original = _upload(client, auth_headers, dataset_name="No Lineage Test")
    assert original.json()["cleaned_from_run_id"] is None
    assert original.json()["cleaning_actions"] is None
