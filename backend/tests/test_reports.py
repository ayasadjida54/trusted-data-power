"""
test_reports.py

Phase 6 tests: authenticated PDF/CSV report downloads, and the public
share-link flow (create, view without auth, revoke, confirm 404 after
revocation).
"""

import os

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "engine", "tests", "sample_messy_data.csv"
)


def _sample_csv_bytes() -> bytes:
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return f.read()


def _upload(client, headers):
    files = {"file": ("sample_messy_data.csv", _sample_csv_bytes(), "text/csv")}
    return client.post("/api/datasets/upload", files=files, headers=headers)


def test_download_pdf_report(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    response = client.get(f"/api/runs/{run_id}/report.pdf", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
    assert len(response.content) > 1000  # a real, non-trivial PDF


def test_download_csv_report(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    response = client.get(f"/api/runs/{run_id}/report.csv", headers=auth_headers)

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    text = response.content.decode("utf-8")
    assert "sample_messy_data.csv" in text
    assert "Category,Severity,Column(s)" in text
    assert "Missing Values" in text


def test_report_downloads_require_auth(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    pdf_response = client.get(f"/api/runs/{run_id}/report.pdf")
    csv_response = client.get(f"/api/runs/{run_id}/report.csv")
    assert pdf_response.status_code == 401
    assert csv_response.status_code == 401


def test_report_download_for_other_orgs_run_returns_404(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]

    other_register = client.post(
        "/api/auth/register",
        json={"email": "report-other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    response = client.get(f"/api/runs/{run_id}/report.pdf", headers=other_headers)
    assert response.status_code == 404


def test_create_share_link_and_view_publicly(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]

    share_response = client.post(f"/api/runs/{run_id}/share", headers=auth_headers)
    assert share_response.status_code == 200
    token = share_response.json()["share_token"]
    assert share_response.json()["share_path"] == f"/public/reports/{token}"

    # No Authorization header - this must work anonymously.
    public_response = client.get(f"/api/public/reports/{token}")
    assert public_response.status_code == 200
    assert public_response.json()["id"] == run_id


def test_share_link_is_idempotent(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    first = client.post(f"/api/runs/{run_id}/share", headers=auth_headers)
    second = client.post(f"/api/runs/{run_id}/share", headers=auth_headers)
    assert first.json()["share_token"] == second.json()["share_token"]


def test_public_pdf_download_works_without_auth(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    token = client.post(f"/api/runs/{run_id}/share", headers=auth_headers).json()["share_token"]

    response = client.get(f"/api/public/reports/{token}/report.pdf")
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


def test_unshared_run_returns_404_on_public_route(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    # Never shared - a made-up token should behave identically to a
    # real-but-revoked one: 404 either way.
    response = client.get("/api/public/reports/not-a-real-token")
    assert response.status_code == 404


def test_revoked_share_link_returns_404(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]
    token = client.post(f"/api/runs/{run_id}/share", headers=auth_headers).json()["share_token"]

    revoke_response = client.delete(f"/api/runs/{run_id}/share", headers=auth_headers)
    assert revoke_response.status_code == 204

    public_response = client.get(f"/api/public/reports/{token}")
    assert public_response.status_code == 404


def test_share_link_for_other_orgs_run_returns_404(client, auth_headers):
    run_id = _upload(client, auth_headers).json()["id"]

    other_register = client.post(
        "/api/auth/register",
        json={"email": "share-other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    response = client.post(f"/api/runs/{run_id}/share", headers=other_headers)
    assert response.status_code == 404
