"""BSE website adapter for corporate actions data.

Fetches board meeting dates and result announcements from BSE India.
"""

import logging
from datetime import date

import httpx

from stockpulse.ingestion.adapters.base import DataAdapter

logger = logging.getLogger(__name__)

BSE_BOARD_MEETINGS_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/BoardMeetings/w"
)


class BSEAdapter:
    """Adapter for BSE India corporate actions data.

    This is NOT a full DataAdapter (no OHLCV support) — it only handles
    corporate actions that yfinance cannot provide.
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.bseindia.com/",
        }

    def fetch_board_meetings(
        self, from_date: date, to_date: date
    ) -> list[dict]:
        """Fetch board meeting announcements from BSE API."""
        results = []
        try:
            params = {
                "strFromdate": from_date.strftime("%Y%m%d"),
                "strTodate": to_date.strftime("%Y%m%d"),
                "category": "Results",
            }
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    BSE_BOARD_MEETINGS_URL,
                    params=params,
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()

            if not isinstance(data, list):
                logger.warning("Unexpected BSE response format: %s", type(data))
                return []

            for item in data:
                try:
                    meeting = {
                        "security_code": str(item.get("SCRIP_CD", "")),
                        "company_name": item.get("SLONGNAME", ""),
                        "purpose": item.get("PURPOSE", ""),
                        "meeting_date": _parse_bse_date(
                            item.get("BOARD_MEETING_DATE", "")
                        ),
                        "announcement_date": _parse_bse_date(
                            item.get("NEWS_DT", "")
                        ),
                    }
                    if meeting["security_code"] and meeting["meeting_date"]:
                        results.append(meeting)
                except Exception:
                    logger.warning("Failed to parse board meeting item: %s", item)

        except httpx.HTTPStatusError as e:
            logger.error("BSE API HTTP error: %s", e.response.status_code)
        except Exception:
            logger.exception("Failed to fetch board meetings from BSE")

        logger.info("Fetched %d board meetings from BSE", len(results))
        return results


def _parse_bse_date(date_str: str) -> date | None:
    """Parse BSE date formats like '07 Mar 2026' or ISO format."""
    if not date_str:
        return None
    # Try common BSE formats
    from datetime import datetime

    for fmt in ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse BSE date: %s", date_str)
    return None
