"""Tests for registration and login — the basic multi-tenant auth flow."""


def test_register_creates_org_and_user(client):
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "founder@acmeshipping.com",
            "password": "supersecret123",
            "full_name": "Jane Founder",
            "organization_name": "Acme Shipping",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "founder@acmeshipping.com"
    assert body["is_org_admin"] is True


def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "dup@acmeshipping.com",
        "password": "supersecret123",
        "full_name": "Jane",
        "organization_name": "Acme Shipping",
    }
    first = client.post("/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/v1/auth/register", json=payload)
    assert second.status_code == 400


def test_login_success_and_failure(client):
    client.post(
        "/v1/auth/register",
        json={
            "email": "login@acmeshipping.com",
            "password": "correctpassword",
            "full_name": "Jane",
            "organization_name": "Acme Shipping",
        },
    )

    good = client.post(
        "/v1/auth/login",
        data={"username": "login@acmeshipping.com", "password": "correctpassword"},
    )
    assert good.status_code == 200
    assert "access_token" in good.json()

    bad = client.post(
        "/v1/auth/login",
        data={"username": "login@acmeshipping.com", "password": "wrongpassword"},
    )
    assert bad.status_code == 401


def test_protected_route_requires_auth(client):
    response = client.get("/v1/lanes")
    assert response.status_code == 401
