"""HTTP client for calling tuJanalyst API from StockPulse."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TUJANALYST_BASE_URL = os.getenv("TUJANALYST_BASE_URL", "")
TUJANALYST_TIMEOUT = int(os.getenv("TUJANALYST_TIMEOUT", "5"))


class TuJanalystClient:
    """Synchronous HTTP client for tuJanalyst REST API."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or TUJANALYST_BASE_URL).rstrip("/")
        self.timeout = timeout or TUJANALYST_TIMEOUT
        self._client = httpx.Client(headers={"Accept": "application/json"}, timeout=self.timeout)

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def get_investigations(self, symbol: str, limit: int = 5) -> list[dict[str, Any]]:
        """GET /api/v1/investigations?company_symbol={symbol}&limit={limit}"""
        if not self.is_configured:
            return []
        data = self._request("GET", "/api/v1/investigations", params={"company_symbol": symbol, "limit": limit})
        if isinstance(data, dict):
            return data.get("items", [])
        if isinstance(data, list):
            return data
        return []

    def get_latest_investigation(self, symbol: str) -> dict[str, Any] | None:
        """Get the most recent investigation for a symbol."""
        items = self.get_investigations(symbol, limit=1)
        return items[0] if items else None

    def get_position(self, symbol: str) -> dict[str, Any] | None:
        """GET /api/v1/positions/{symbol}"""
        if not self.is_configured:
            return None
        return self._request("GET", f"/api/v1/positions/{symbol}")

    def get_reports(self, limit: int = 10, symbol: str | None = None) -> list[dict[str, Any]]:
        """GET /api/v1/reports?limit={limit}"""
        if not self.is_configured:
            return []
        params: dict[str, Any] = {"limit": limit}
        if symbol:
            params["company_symbol"] = symbol
        data = self._request("GET", "/api/v1/reports", params=params)
        if isinstance(data, dict):
            return data.get("items", [])
        if isinstance(data, list):
            return data
        return []

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        """GET /api/v1/reports/{report_id}"""
        if not self.is_configured:
            return None
        return self._request("GET", f"/api/v1/reports/{report_id}")

    def get_performance_summary(self) -> dict[str, Any] | None:
        """GET /api/v1/performance/summary"""
        if not self.is_configured:
            return None
        return self._request("GET", "/api/v1/performance/summary")

    def get_performance_recommendations(self, limit: int = 50) -> list[dict[str, Any]]:
        """GET /api/v1/performance/recommendations"""
        if not self.is_configured:
            return []
        data = self._request("GET", "/api/v1/performance/recommendations", params={"limit": limit})
        if isinstance(data, dict):
            return data.get("items", [])
        if isinstance(data, list):
            return data
        return []

    def get_performance_outcomes(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """GET /api/v1/performance/outcomes"""
        if not self.is_configured:
            return []
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        data = self._request("GET", "/api/v1/performance/outcomes", params=params)
        if isinstance(data, dict):
            return data.get("items", [])
        if isinstance(data, list):
            return data
        return []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        url = f"{self.base_url}{path}"
        try:
            resp = self._client.request(method, url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("tuJanalyst request timed out: path=%s", path)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("tuJanalyst API error: path=%s status=%s", path, exc.response.status_code)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("tuJanalyst request failed: path=%s error=%s", path, exc)
            return None
