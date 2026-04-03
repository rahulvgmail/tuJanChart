"""Tests for the screeners API endpoints."""

from datetime import date
from decimal import Decimal

from tests.conftest import _make_indicator


class TestListScreeners:
    def test_returns_screeners(self, client, auth_header, sample_screener):
        resp = client.get("/api/screeners", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        names = [s["name"] for s in data["items"]]
        assert "52W Closing High" in names

    def test_requires_auth(self, client):
        resp = client.get("/api/screeners")
        assert resp.status_code == 401


class TestScreenerResults:
    def test_returns_results(
        self, client, auth_header, db_session, sample_stock, sample_screener
    ):
        _make_indicator(
            db_session, sample_stock.id, date.today(),
            is_52w_closing_high=True,
            current_price=Decimal("1300.00"),
        )
        resp = client.get(
            f"/api/screeners/{sample_screener.id}/results",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["screener"]["name"] == "52W Closing High"
        assert data["total"] >= 1

    def test_not_found(self, client, auth_header):
        resp = client.get("/api/screeners/99999/results", headers=auth_header)
        assert resp.status_code == 404


class TestCreateScreener:
    def test_success(self, client, auth_header):
        resp = client.post(
            "/api/screeners",
            json={
                "name": "My Custom Screener",
                "category": "Custom",
                "conditions": [
                    {"field": "is_volume_breakout", "operator": "is_true"},
                ],
            },
            headers=auth_header,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "My Custom Screener"
        assert data["slug"] == "my-custom-screener"

    def test_missing_fields(self, client, auth_header):
        resp = client.post(
            "/api/screeners",
            json={"name": "Missing conditions"},
            headers=auth_header,
        )
        assert resp.status_code == 400


class TestPreviewScreener:
    def test_preview(self, client, auth_header, db_session, sample_stock):
        _make_indicator(
            db_session, sample_stock.id, date.today(),
            is_gap_up=True,
            current_price=Decimal("1250.00"),
        )
        resp = client.post(
            "/api/screeners/preview",
            json={
                "conditions": [
                    {"field": "is_gap_up", "operator": "is_true"},
                ],
            },
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1

    def test_missing_conditions(self, client, auth_header):
        resp = client.post(
            "/api/screeners/preview",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400


class TestDeleteScreener:
    def test_delete_custom(self, client, auth_header, sample_screener):
        resp = client.delete(
            f"/api/screeners/{sample_screener.id}",
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deleted"

    def test_delete_builtin_forbidden(self, client, auth_header, builtin_screener):
        resp = client.delete(
            f"/api/screeners/{builtin_screener.id}",
            headers=auth_header,
        )
        assert resp.status_code == 403

    def test_delete_not_found(self, client, auth_header):
        resp = client.delete("/api/screeners/99999", headers=auth_header)
        assert resp.status_code == 404
