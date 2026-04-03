"""Tests for the webhooks API endpoints."""


class TestListWebhooks:
    def test_returns_webhooks(self, client, auth_header, sample_webhook):
        resp = client.get("/api/webhooks", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        assert data["items"][0]["url"] == "https://example.com/webhook"

    def test_requires_auth(self, client):
        resp = client.get("/api/webhooks")
        assert resp.status_code == 401


class TestCreateWebhook:
    def test_success(self, client, auth_header):
        resp = client.post(
            "/api/webhooks",
            json={
                "url": "https://example.com/new-hook",
                "event_types": ["GAP_UP", "GAP_DOWN"],
                "secret": "my-secret",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["url"] == "https://example.com/new-hook"
        assert data["event_types"] == ["GAP_UP", "GAP_DOWN"]
        assert data["is_active"] is True

    def test_missing_fields(self, client, auth_header):
        resp = client.post(
            "/api/webhooks",
            json={"url": "https://example.com/hook"},
            headers=auth_header,
        )
        assert resp.status_code == 400


class TestDeleteWebhook:
    def test_success(self, client, auth_header, sample_webhook):
        resp = client.delete(
            f"/api/webhooks/{sample_webhook.id}",
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deactivated"

    def test_not_found(self, client, auth_header):
        resp = client.delete("/api/webhooks/99999", headers=auth_header)
        assert resp.status_code == 404
