"""
test_history.py

Phase 5 tests: reusing a dataset slot across repeat uploads, listing a
dataset's run history, and comparing two runs.
"""

import os

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "engine", "tests", "sample_messy_data.csv"
)
CLEAN_CSV_BYTES = b"product,price,in_stock\nWidget,10.0,true\nGadget,25.5,true\nGizmo,7.25,false\n"


def _sample_csv_bytes() -> bytes:
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return f.read()


def _upload(client, headers, content=None, filename="sample_messy_data.csv", **params):
    files = {"file": (filename, content or _sample_csv_bytes(), "text/csv")}
    return client.post("/api/datasets/upload", files=files, params=params, headers=headers)


def test_repeat_upload_with_same_dataset_name_reuses_the_slot(client, auth_headers):
    first = _upload(client, auth_headers, dataset_name="Monthly Sales Export")
    second = _upload(client, auth_headers, dataset_name="Monthly Sales Export")

    assert first.json()["dataset_id"] == second.json()["dataset_id"]
    assert first.json()["id"] != second.json()["id"]


def test_dataset_name_matching_is_case_insensitive(client, auth_headers):
    first = _upload(client, auth_headers, dataset_name="Monthly Sales Export")
    second = _upload(client, auth_headers, dataset_name="monthly sales export")
    assert first.json()["dataset_id"] == second.json()["dataset_id"]


def test_upload_with_explicit_dataset_id_appends_to_that_slot(client, auth_headers):
    first = _upload(client, auth_headers, dataset_name="Weekly Export")
    dataset_id = first.json()["dataset_id"]

    second = _upload(client, auth_headers, dataset_id=dataset_id)
    assert second.json()["dataset_id"] == dataset_id


def test_upload_with_unknown_dataset_id_returns_404(client, auth_headers):
    response = _upload(client, auth_headers, dataset_id=999999)
    assert response.status_code == 404


def test_upload_without_name_or_id_creates_a_new_slot_each_time(client, auth_headers):
    first = _upload(client, auth_headers)
    second = _upload(client, auth_headers)
    assert first.json()["dataset_id"] != second.json()["dataset_id"]


def test_run_history_lists_all_runs_chronologically(client, auth_headers):
    first = _upload(client, auth_headers, dataset_name="History Test")
    dataset_id = first.json()["dataset_id"]
    second = _upload(client, auth_headers, dataset_id=dataset_id)
    third = _upload(client, auth_headers, dataset_id=dataset_id)

    response = client.get(f"/api/datasets/{dataset_id}/runs", headers=auth_headers)
    assert response.status_code == 200
    run_ids = [run["id"] for run in response.json()]
    assert run_ids == [first.json()["id"], second.json()["id"], third.json()["id"]]


def test_compare_two_runs_of_the_same_dataset(client, auth_headers):
    messy = _upload(client, auth_headers, dataset_name="Compare Test")
    dataset_id = messy.json()["dataset_id"]
    clean = _upload(
        client, auth_headers, dataset_id=dataset_id, content=CLEAN_CSV_BYTES, filename="clean.csv"
    )

    response = client.get(
        f"/api/datasets/{dataset_id}/compare",
        params={"run_a": messy.json()["id"], "run_b": clean.json()["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previous_run_id"] == messy.json()["id"]
    assert body["current_run_id"] == clean.json()["id"]
    assert body["current_score"] == clean.json()["score"]
    assert body["previous_score"] == messy.json()["score"]
    assert isinstance(body["summary"], list) and len(body["summary"]) > 0


def test_compare_with_run_from_wrong_dataset_still_works_if_owned(client, auth_headers):
    # Comparing runs across two DIFFERENT datasets (both owned by the
    # caller) is allowed - the dataset_id in the URL is just used to
    # confirm ownership context, compare_runs itself only checks org.
    first_dataset = _upload(client, auth_headers, dataset_name="Dataset A")
    second_dataset = _upload(client, auth_headers, dataset_name="Dataset B")

    response = client.get(
        f"/api/datasets/{first_dataset.json()['dataset_id']}/compare",
        params={"run_a": first_dataset.json()["id"], "run_b": second_dataset.json()["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_compare_run_from_another_organization_returns_404(client, auth_headers):
    own_upload = _upload(client, auth_headers, dataset_name="Mine")
    dataset_id = own_upload.json()["dataset_id"]

    other_register = client.post(
        "/api/auth/register",
        json={"email": "compare-other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}
    other_upload = _upload(client, other_headers, dataset_name="Theirs")

    response = client.get(
        f"/api/datasets/{dataset_id}/compare",
        params={"run_a": own_upload.json()["id"], "run_b": other_upload.json()["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_runs_list_for_nonexistent_dataset_returns_404(client, auth_headers):
    response = client.get("/api/datasets/999999/runs", headers=auth_headers)
    assert response.status_code == 404
