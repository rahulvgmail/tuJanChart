"""Tests for the API root endpoint."""


def test_api_root_returns_200(client):
    resp = client.get("/api/")
    assert resp.status_code == 200


def test_api_root_returns_name_and_version(client):
    data = client.get("/api/").get_json()
    assert data["name"] == "StockPulse API"
    assert data["version"] == "0.1.0"
