"""Tests for the stocks API endpoints."""

from datetime import date
from decimal import Decimal

from tests.conftest import _make_indicator


class TestListStocks:
    def test_requires_auth(self, client):
        resp = client.get("/api/stocks")
        assert resp.status_code == 401

    def test_returns_stocks(self, client, auth_header, sample_stock):
        resp = client.get("/api/stocks", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        symbols = [s["symbol"] for s in data["items"]]
        assert "500325" in symbols

    def test_sector_filter(self, client, auth_header, sample_stock, second_stock):
        resp = client.get("/api/stocks?sector=Banking", headers=auth_header)
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["nse_symbol"] == "HDFCBANK"


class TestGetStock:
    def test_by_nse_symbol(self, client, auth_header, sample_stock):
        resp = client.get("/api/stocks/RELIANCE", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["nse_symbol"] == "RELIANCE"
        assert data["company_name"] == "Reliance Industries Ltd"

    def test_by_bse_code(self, client, auth_header, sample_stock):
        resp = client.get("/api/stocks/500325", headers=auth_header)
        assert resp.status_code == 200
        assert resp.get_json()["symbol"] == "500325"

    def test_not_found(self, client, auth_header):
        resp = client.get("/api/stocks/DOESNOTEXIST", headers=auth_header)
        assert resp.status_code == 404


class TestIndicatorTimeseries:
    def test_returns_series(self, client, auth_header, db_session, sample_stock):
        _make_indicator(
            db_session, sample_stock.id, date.today(),
            current_price=Decimal("1250.00"),
            is_52w_closing_high=True,
        )
        resp = client.get("/api/stocks/RELIANCE/indicators?period=30d", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["symbol"] == "RELIANCE"
        assert data["data_points"] >= 1
        assert data["series"][0]["current_price"] == 1250.0

    def test_not_found(self, client, auth_header):
        resp = client.get("/api/stocks/NOPE/indicators", headers=auth_header)
        assert resp.status_code == 404


class TestPrices:
    def test_returns_prices(self, client, auth_header, sample_prices):
        resp = client.get("/api/stocks/RELIANCE/prices?period=90d", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["symbol"] == "RELIANCE"
        assert data["data_points"] >= 1
        price = data["prices"][0]
        assert "open" in price
        assert "close" in price
        assert "volume" in price

    def test_not_found(self, client, auth_header):
        resp = client.get("/api/stocks/NOPE/prices", headers=auth_header)
        assert resp.status_code == 404


class TestSetColor:
    def test_success(self, client, auth_header, sample_stock):
        resp = client.put(
            "/api/stocks/RELIANCE/color",
            json={"color": "Green", "comment": "Looks bullish"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["color"] == "Green"
        assert data["symbol"] == "RELIANCE"

    def test_invalid_color(self, client, auth_header, sample_stock):
        resp = client.put(
            "/api/stocks/RELIANCE/color",
            json={"color": "Purple"},
            headers=auth_header,
        )
        assert resp.status_code == 400

    def test_missing_color_field(self, client, auth_header, sample_stock):
        resp = client.put(
            "/api/stocks/RELIANCE/color",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400


class TestNotes:
    def test_add_note(self, client, auth_header, sample_stock):
        resp = client.post(
            "/api/stocks/RELIANCE/notes",
            json={"content": "Test note content"},
            headers=auth_header,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["content"] == "Test note content"
        assert data["author_type"] == "human"

    def test_add_note_missing_content(self, client, auth_header, sample_stock):
        resp = client.post(
            "/api/stocks/RELIANCE/notes",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400

    def test_list_notes(self, client, auth_header, sample_stock):
        # Add a note first
        client.post(
            "/api/stocks/RELIANCE/notes",
            json={"content": "Note 1"},
            headers=auth_header,
        )
        resp = client.get("/api/stocks/RELIANCE/notes", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
