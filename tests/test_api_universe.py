"""Tests for the universe API endpoints."""

from unittest.mock import patch


class TestListUniverse:
    def test_returns_stocks(self, client, auth_header, sample_stock):
        resp = client.get("/api/universe", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        assert data["active"] >= 1

    def test_requires_auth(self, client):
        resp = client.get("/api/universe")
        assert resp.status_code == 401


class TestAddStock:
    @patch("stockpulse.ingestion.tasks.backfill_stock.delay")
    def test_success(self, mock_backfill, client, auth_header):
        resp = client.post(
            "/api/universe",
            json={
                "symbol": "532540",
                "nse_symbol": "TCS",
                "company_name": "Tata Consultancy Services Ltd",
                "sector": "IT",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "created"
        assert data["symbol"] == "532540"
        mock_backfill.assert_called_once()

    def test_duplicate(self, client, auth_header, sample_stock):
        resp = client.post(
            "/api/universe",
            json={
                "symbol": "500325",
                "company_name": "Reliance Industries Ltd",
            },
            headers=auth_header,
        )
        assert resp.status_code == 409

    @patch("stockpulse.ingestion.tasks.backfill_stock.delay")
    def test_reactivate(self, mock_backfill, client, auth_header, db_session, sample_stock):
        # Deactivate first
        sample_stock.is_active = False
        db_session.flush()

        resp = client.post(
            "/api/universe",
            json={
                "symbol": "500325",
                "company_name": "Reliance Industries Ltd",
            },
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "reactivated"

    def test_missing_fields(self, client, auth_header):
        resp = client.post(
            "/api/universe",
            json={"symbol": "999999"},
            headers=auth_header,
        )
        assert resp.status_code == 400


class TestDeactivateStock:
    def test_success(self, client, auth_header, sample_stock):
        resp = client.delete("/api/universe/RELIANCE", headers=auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deactivated"

    def test_not_found(self, client, auth_header):
        resp = client.delete("/api/universe/NOPE", headers=auth_header)
        assert resp.status_code == 404
