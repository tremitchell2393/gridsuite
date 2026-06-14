"""
Tests for the signal schema and lane watchlist — exercises the core
"signals + lane limit" mechanics.
"""
from datetime import datetime, timezone

from app.models.signal import Signal


def _register_and_login(client, email="org@acmeshipping.com"):
    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret123",
            "full_name": "Jane Founder",
            "organization_name": "Acme Shipping",
        },
    )
    login = client.post("/v1/auth/login", data={"username": email, "password": "supersecret123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_signal_model_roundtrip(db_session):
    """Sanity check: a Signal row can be written and read back with the
    universal schema fields intact."""
    signal = Signal(
        signal_id="customs_velocity_index",
        entity_type="lane",
        entity_id="SHSE-LAX",
        timestamp=datetime.now(timezone.utc),
        value=1.18,
        unit="ratio_to_30d_avg",
        source="customs_velocity",
        confidence=1.0,
        metadata_json={"filing_count_today": 412},
    )
    db_session.add(signal)
    db_session.commit()

    fetched = db_session.query(Signal).filter_by(entity_id="SHSE-LAX").first()
    assert fetched.signal_id == "customs_velocity_index"
    assert fetched.value == 1.18
    assert fetched.metadata_json["filing_count_today"] == 412


def test_watch_lane_within_limit(client):
    headers = _register_and_login(client)

    # Core tier defaults to lane_limit=3
    for lane_id in ["SHSE-LAX", "SHSE-HOU", "SHSE-RTM"]:
        response = client.post("/v1/lanes", json={"lane_id": lane_id}, headers=headers)
        assert response.status_code == 201

    listing = client.get("/v1/lanes", headers=headers)
    assert len(listing.json()) == 3


def test_watch_lane_exceeds_limit(client):
    headers = _register_and_login(client, email="limit@acmeshipping.com")

    for lane_id in ["SHSE-LAX", "SHSE-HOU", "SHSE-RTM"]:
        client.post("/v1/lanes", json={"lane_id": lane_id}, headers=headers)

    # 4th lane should be rejected on Core tier (lane_limit=3)
    response = client.post("/v1/lanes", json={"lane_id": "BUSAN-LAX"}, headers=headers)
    assert response.status_code == 403
    assert "Lane limit reached" in response.json()["detail"]


def test_list_signals_endpoint(client, db_session):
    headers = _register_and_login(client, email="signals@acmeshipping.com")

    db_session.add(
        Signal(
            signal_id="port_dwell_time",
            entity_type="port",
            entity_id="SHSE",
            timestamp=datetime.now(timezone.utc),
            value=4.2,
            unit="days",
            source="port_dwell",
            confidence=1.0,
            metadata_json={},
        )
    )
    db_session.commit()

    response = client.get(
        "/v1/signals",
        params={"entity_type": "port", "entity_id": "SHSE"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == "SHSE"
    assert len(body["signals"]) == 1
    assert body["signals"][0]["signal_id"] == "port_dwell_time"
