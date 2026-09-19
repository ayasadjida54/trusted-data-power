"""
test_auth.py

Phase 4 auth tests: registration, login, token validation, and the
organization-scoping this all exists to support.
"""

import uuid


def _unique_email():
    return f"{uuid.uuid4().hex[:10]}@example.com"


def test_register_returns_access_token(client):
    response = client.post(
        "/api/auth/register",
        json={"email": _unique_email(), "password": "correct horse battery"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_register_duplicate_email_returns_409(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    response = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register", json={"email": _unique_email(), "password": "short"}
    )
    assert response.status_code == 422


def test_register_with_custom_organization_name(client):
    email = _unique_email()
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "organization_name": "Acme Retail"},
    )
    token = register_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["organization"]["name"] == "Acme Retail"


def test_login_with_correct_credentials(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})

    response = client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_returns_401(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})

    response = client.post(
        "/api/auth/login", data={"username": email, "password": "wrong password"}
    )
    assert response.status_code == 401


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/api/auth/login", data={"username": _unique_email(), "password": "whatever123"}
    )
    assert response.status_code == 401


def test_me_without_token_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_garbage_token_returns_401(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_protected_dataset_route_requires_auth(client):
    response = client.get("/api/datasets")
    assert response.status_code == 401
