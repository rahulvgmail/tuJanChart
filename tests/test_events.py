"""Tests for event detection engine."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from stockpulse.engine.events import detect_events
from stockpulse.models.event import Event
from tests.conftest import _make_indicator


class TestDetectEvents:
    """Tests for detect_events() comparing current vs previous indicators."""

    def test_52w_closing_high_event(self, db_session, sample_stock):
        """New 52W closing high should generate an event."""
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, is_52w_closing_high=False)
        _make_indicator(db_session, sample_stock.id, today, is_52w_closing_high=True, high_52w=Decimal("1250.00"))

        events = detect_events(db_session, sample_stock.id, today)

        assert len(events) == 1
        assert events[0].event_type == "52W_CLOSING_HIGH"
        assert events[0].stock_id == sample_stock.id

    def test_no_event_if_already_52w_high(self, db_session, sample_stock):
        """Consecutive 52W highs should not re-fire."""
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, is_52w_closing_high=True)
        _make_indicator(db_session, sample_stock.id, today, is_52w_closing_high=True)

        events = detect_events(db_session, sample_stock.id, today)

        assert not any(e.event_type == "52W_CLOSING_HIGH" for e in events)

    def test_volume_breakout_event(self, db_session, sample_stock):
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, is_volume_breakout=False)
        _make_indicator(
            db_session, sample_stock.id, today,
            is_volume_breakout=True,
            today_volume=5_000_000,
            max_vol_21d=3_000_000,
            avg_vol_140d=2_000_000,
        )

        events = detect_events(db_session, sample_stock.id, today)

        vol_events = [e for e in events if e.event_type == "VOLUME_BREAKOUT"]
        assert len(vol_events) == 1
        assert vol_events[0].payload["volume"] == 5_000_000

    def test_gap_up_event(self, db_session, sample_stock):
        today = date(2026, 3, 11)

        _make_indicator(
            db_session, sample_stock.id, today,
            is_gap_up=True,
            gap_pct=Decimal("5.20"),
            today_open=Decimal("1260.00"),
            prev_close=Decimal("1197.00"),
        )

        events = detect_events(db_session, sample_stock.id, today)

        gap_events = [e for e in events if e.event_type == "GAP_UP"]
        assert len(gap_events) == 1
        assert gap_events[0].payload["gap_pct"] == pytest.approx(5.20, abs=0.01)

    def test_gap_down_event(self, db_session, sample_stock):
        today = date(2026, 3, 11)

        _make_indicator(
            db_session, sample_stock.id, today,
            is_gap_down=True,
            gap_pct=Decimal("-4.10"),
            today_open=Decimal("1140.00"),
            prev_close=Decimal("1190.00"),
        )

        events = detect_events(db_session, sample_stock.id, today)

        gap_events = [e for e in events if e.event_type == "GAP_DOWN"]
        assert len(gap_events) == 1

    def test_dma_crossover_event(self, db_session, sample_stock):
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, dma_10_signal=None)
        _make_indicator(
            db_session, sample_stock.id, today,
            dma_10_signal="Hold",
            dma_10_touch=True,
            dma_10=Decimal("1195.00"),
        )

        events = detect_events(db_session, sample_stock.id, today)

        dma_events = [e for e in events if e.event_type == "DMA_CROSSOVER"]
        assert len(dma_events) >= 1
        match = [e for e in dma_events if e.payload["period"] == 10]
        assert len(match) == 1
        assert match[0].payload["signal"] == "Hold"

    def test_dma_signal_change_fires_event(self, db_session, sample_stock):
        """Signal changing from Hold to Reverse should fire."""
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, dma_20_signal="Hold")
        _make_indicator(db_session, sample_stock.id, today, dma_20_signal="Reverse")

        events = detect_events(db_session, sample_stock.id, today)

        dma_events = [e for e in events if e.event_type == "DMA_CROSSOVER" and e.payload["period"] == 20]
        assert len(dma_events) == 1
        assert dma_events[0].payload["signal"] == "Reverse"
        assert dma_events[0].payload["prev_signal"] == "Hold"

    def test_90d_high_event(self, db_session, sample_stock):
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, is_90d_high=False)
        _make_indicator(
            db_session, sample_stock.id, today,
            is_90d_high=True,
            today_high=Decimal("1300.00"),
            high_90d=Decimal("1290.00"),
        )

        events = detect_events(db_session, sample_stock.id, today)

        assert any(e.event_type == "90D_HIGH" for e in events)

    def test_result_approaching_event(self, db_session, sample_stock):
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday, result_within_7d=False)
        _make_indicator(
            db_session, sample_stock.id, today,
            result_within_7d=True,
            days_to_result=5,
        )

        events = detect_events(db_session, sample_stock.id, today)

        result_events = [e for e in events if e.event_type == "RESULT_APPROACHING"]
        assert len(result_events) == 1
        assert result_events[0].payload["days_to_result"] == 5
        assert result_events[0].payload["window"] == 7

    def test_no_events_for_empty_stock(self, db_session, sample_stock):
        """No indicators = no events."""
        events = detect_events(db_session, sample_stock.id, date(2026, 3, 11))
        assert events == []

    def test_single_indicator_no_previous(self, db_session, sample_stock):
        """First day's data — events fire for any True flags."""
        today = date(2026, 3, 11)
        _make_indicator(
            db_session, sample_stock.id, today,
            is_52w_closing_high=True,
            is_volume_breakout=True,
            is_gap_up=True,
            gap_pct=Decimal("4.00"),
        )

        events = detect_events(db_session, sample_stock.id, today)

        types = {e.event_type for e in events}
        assert "52W_CLOSING_HIGH" in types
        assert "VOLUME_BREAKOUT" in types
        assert "GAP_UP" in types

    def test_multiple_events_same_day(self, db_session, sample_stock):
        """Multiple events can fire on the same day."""
        yesterday = date(2026, 3, 10)
        today = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, yesterday)
        _make_indicator(
            db_session, sample_stock.id, today,
            is_52w_closing_high=True,
            is_volume_breakout=True,
            is_gap_up=True,
            gap_pct=Decimal("6.00"),
            today_open=Decimal("1270.00"),
            prev_close=Decimal("1197.00"),
            high_52w=Decimal("1250.00"),
            today_volume=5_000_000,
            max_vol_21d=3_000_000,
        )

        events = detect_events(db_session, sample_stock.id, today)

        types = {e.event_type for e in events}
        assert len(types) >= 3
