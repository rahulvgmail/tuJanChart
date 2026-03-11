"""Pydantic v2 response schemas for the REST API.

These schemas are designed to be directly deserializable by the DSPy
agentic app (Python/Pydantic).
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class StockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    nse_symbol: str | None = None
    company_name: str
    sector: str | None = None
    industry: str | None = None
    is_active: bool = True
    color: str | None = None


class IndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_id: int
    symbol: str
    nse_symbol: str | None = None
    company_name: str
    sector: str | None = None
    date: str
    current_price: float | None = None
    prev_close: float | None = None
    pct_change: float | None = None
    pe: float | None = None
    market_cap_cr: float | None = None
    today_high: float | None = None
    today_low: float | None = None
    today_volume: int | None = None

    # DMAs
    dma_10: float | None = None
    dma_20: float | None = None
    dma_50: float | None = None
    dma_100: float | None = None
    dma_200: float | None = None
    dma_10_touch: bool = False
    dma_20_touch: bool = False
    dma_50_touch: bool = False
    dma_100_touch: bool = False
    dma_200_touch: bool = False
    dma_10_signal: str | None = None
    dma_20_signal: str | None = None
    dma_50_signal: str | None = None
    dma_100_signal: str | None = None
    dma_200_signal: str | None = None

    # WMAs
    wma_5: float | None = None
    wma_10: float | None = None
    wma_20: float | None = None
    wma_30: float | None = None
    wma_5_touch: bool = False
    wma_10_touch: bool = False
    wma_20_touch: bool = False
    wma_5_signal: str | None = None
    wma_10_signal: str | None = None
    wma_20_signal: str | None = None

    # 52W
    high_52w: float | None = None
    is_52w_high_intraday: bool = False
    is_52w_closing_high: bool = False
    was_52w_high_yesterday: bool = False
    high_52w_date: str | None = None

    # Volume
    max_vol_21d: int | None = None
    avg_vol_140d: int | None = None
    avg_vol_280d: int | None = None
    is_volume_breakout: bool = False

    # Biweek/Week
    biweek_high: float | None = None
    is_biweek_bo: bool = False
    week_high: float | None = None
    is_week_bo: bool = False

    # Gap
    gap_pct: float | None = None
    is_gap_up: bool = False
    is_gap_down: bool = False

    # 90D
    high_90d: float | None = None
    low_90d: float | None = None
    is_90d_high: bool = False
    is_90d_low_touch: bool = False

    # Result
    days_to_result: int | None = None
    result_within_7d: bool = False
    result_within_10d: bool = False
    result_within_15d: bool = False
    result_declared_10d: bool = False


class IndicatorTimeSeriesPoint(BaseModel):
    date: str
    current_price: float | None = None
    dma_10: float | None = None
    dma_20: float | None = None
    dma_50: float | None = None
    dma_100: float | None = None
    dma_200: float | None = None
    wma_5: float | None = None
    wma_10: float | None = None
    wma_20: float | None = None
    today_volume: int | None = None
    is_52w_closing_high: bool = False
    is_volume_breakout: bool = False


class ScreenerResponse(BaseModel):
    id: int
    name: str
    slug: str
    category: str | None = None
    is_builtin: bool = False
    is_active: bool = True
    condition_count: int = 0


class ScreenerConditionSchema(BaseModel):
    field: str
    operator: str
    value: object = None


class ScreenerCreateRequest(BaseModel):
    name: str
    category: str | None = None
    conditions: list[ScreenerConditionSchema]


class ScreenerPreviewRequest(BaseModel):
    conditions: list[ScreenerConditionSchema]


class NoteCreateRequest(BaseModel):
    content: str
    author_type: str = "human"


class NoteResponse(BaseModel):
    id: int
    stock_id: int
    author_id: int | None = None
    author_type: str
    content: str
    created_at: str


class EventResponse(BaseModel):
    id: int
    stock_id: int
    symbol: str | None = None
    event_type: str
    payload: dict | None = None
    created_at: str


class WebhookCreateRequest(BaseModel):
    url: str
    secret: str | None = None
    event_types: list[str]


class WebhookResponse(BaseModel):
    id: int
    url: str
    event_types: list[str]
    is_active: bool = True
    created_at: str


class UniverseAddRequest(BaseModel):
    symbol: str
    nse_symbol: str | None = None
    company_name: str
    sector: str | None = None
    industry: str | None = None
    isin: str | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int = 1
    per_page: int = 50


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
