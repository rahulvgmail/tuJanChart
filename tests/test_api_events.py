"""Tests for the events API endpoints."""


class TestListEvents:
    def test_returns_events(self, client, auth_header, sample_event):
        resp = client.get("/api/events", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        assert data["items"][0]["event_type"] == "52W_CLOSING_HIGH"

    def test_filter_by_type(self, client, auth_header, sample_event):
        resp = client.get(
            "/api/events?event_type=52W_CLOSING_HIGH",
            headers=auth_header,
        )
        data = resp.get_json()
        assert data["total"] >= 1
        assert all(e["event_type"] == "52W_CLOSING_HIGH" for e in data["items"])

    def test_filter_by_symbol(self, client, auth_header, sample_event):
        resp = client.get("/api/events?symbol=RELIANCE", headers=auth_header)
        data = resp.get_json()
        assert data["total"] >= 1
        assert all(e["symbol"] == "RELIANCE" for e in data["items"])

    def test_requires_auth(self, client):
        resp = client.get("/api/events")
        assert resp.status_code == 401


class TestGetEvent:
    def test_returns_event(self, client, auth_header, sample_event):
        resp = client.get(f"/api/events/{sample_event.id}", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["event_type"] == "52W_CLOSING_HIGH"
        assert data["payload"]["price"] == 1250.0

    def test_not_found(self, client, auth_header):
        resp = client.get("/api/events/99999", headers=auth_header)
        assert resp.status_code == 404
