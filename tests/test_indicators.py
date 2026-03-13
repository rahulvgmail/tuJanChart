"""Unit tests for indicator computation functions."""

import numpy as np
import pytest

from stockpulse.engine.indicators import (
    compute_dma,
    compute_gap,
    compute_volume_metrics,
    compute_wma,
)
from stockpulse.engine.signals import compute_touch_and_signal


# ── DMA / WMA ────────────────────────────────────────────────


class TestComputeDMA:
    def test_basic_average(self):
        closes = np.array([100.0, 102.0, 98.0, 104.0, 96.0])
        result = compute_dma(closes, 5)
        assert result == pytest.approx(100.0)

    def test_period_greater_than_data(self):
        closes = np.array([100.0, 102.0, 98.0])
        result = compute_dma(closes, 10)
        assert result == pytest.approx(100.0)

    def test_empty_array(self):
        assert compute_dma(np.array([]), 10) is None

    def test_single_value(self):
        assert compute_dma(np.array([42.0]), 10) == pytest.approx(42.0)

    def test_uses_first_n_values(self):
        # closes are ordered most-recent-first (from DB query)
        closes = np.array([110.0, 105.0, 100.0, 95.0, 90.0])
        result = compute_dma(closes, 3)
        assert result == pytest.approx(np.mean([110.0, 105.0, 100.0]))


class TestComputeWMA:
    def test_identical_to_dma_for_same_input(self):
        closes = np.array([50.0, 55.0, 60.0, 65.0, 70.0])
        assert compute_wma(closes, 5) == compute_dma(closes, 5)

    def test_empty(self):
        assert compute_wma(np.array([]), 5) is None


# ── Touch & Signal ───────────────────────────────────────────


class TestTouchAndSignal:
    def test_hold_signal(self):
        # Price straddles MA, close >= MA → Hold
        touch, signal = compute_touch_and_signal(
            current_price=105.0, today_high=110.0, today_low=95.0, ma_value=100.0
        )
        assert touch is True
        assert signal == "Hold"

    def test_reverse_signal(self):
        # Price straddles MA, close < MA → Reverse
        touch, signal = compute_touch_and_signal(
            current_price=95.0, today_high=110.0, today_low=90.0, ma_value=100.0
        )
        assert touch is True
        assert signal == "Reverse"

    def test_no_touch_above(self):
        # Entire range above MA → no touch
        touch, signal = compute_touch_and_signal(
            current_price=120.0, today_high=125.0, today_low=115.0, ma_value=100.0
        )
        assert touch is False
        assert signal is None

    def test_no_touch_below(self):
        # Entire range below MA → no touch
        touch, signal = compute_touch_and_signal(
            current_price=80.0, today_high=85.0, today_low=75.0, ma_value=100.0
        )
        assert touch is False
        assert signal is None

    def test_none_ma(self):
        touch, signal = compute_touch_and_signal(100.0, 110.0, 90.0, None)
        assert touch is False
        assert signal is None

    def test_none_high_low(self):
        touch, signal = compute_touch_and_signal(100.0, None, None, 100.0)
        assert touch is False
        assert signal is None

    def test_exact_touch_at_low(self):
        # low == MA, high > MA → touch (low < MA is False here)
        touch, signal = compute_touch_and_signal(
            current_price=105.0, today_high=110.0, today_low=100.0, ma_value=100.0
        )
        # low < ma_value → 100 < 100 is False, so no touch
        assert touch is False

    def test_touch_just_below_ma(self):
        touch, signal = compute_touch_and_signal(
            current_price=100.5, today_high=101.0, today_low=99.9, ma_value=100.0
        )
        assert touch is True
        assert signal == "Hold"


# ── Gap ──────────────────────────────────────────────────────


class TestComputeGap:
    def test_gap_up(self):
        result = compute_gap(today_open=106.0, prev_close=100.0, threshold=3.0)
        assert result["gap_pct"] == pytest.approx(6.0)
        assert result["is_gap_up"] is True
        assert result["is_gap_down"] is False

    def test_gap_down(self):
        result = compute_gap(today_open=95.0, prev_close=100.0, threshold=3.0)
        assert result["gap_pct"] == pytest.approx(-5.0)
        assert result["is_gap_up"] is False
        assert result["is_gap_down"] is True

    def test_no_gap(self):
        result = compute_gap(today_open=101.0, prev_close=100.0, threshold=3.0)
        assert result["gap_pct"] == pytest.approx(1.0)
        assert result["is_gap_up"] is False
        assert result["is_gap_down"] is False

    def test_none_values(self):
        result = compute_gap(None, 100.0)
        assert result["gap_pct"] is None
        assert result["is_gap_up"] is False

    def test_zero_prev_close(self):
        result = compute_gap(100.0, 0.0)
        assert result["gap_pct"] is None

    def test_custom_threshold(self):
        result = compute_gap(today_open=102.0, prev_close=100.0, threshold=1.0)
        assert result["is_gap_up"] is True

    def test_exactly_at_threshold(self):
        result = compute_gap(today_open=103.0, prev_close=100.0, threshold=3.0)
        # 3.0 > 3.0 is False
        assert result["is_gap_up"] is False


# ── Volume Metrics ───────────────────────────────────────────


class TestComputeVolumeMetrics:
    def _make_daily_prices(self, volumes):
        """Create mock DailyPrice objects with just volumes."""
        from unittest.mock import MagicMock

        prices = []
        for v in volumes:
            p = MagicMock()
            p.volume = v
            prices.append(p)
        return prices

    def test_breakout_above_max_21d(self):
        volumes = [100000] * 25
        data = self._make_daily_prices(volumes)
        result = compute_volume_metrics(data, today_volume=200000, max_period=21)
        assert result["is_volume_breakout"] is True
        assert result["max_vol_21d"] == 100000

    def test_no_breakout(self):
        volumes = [100000] * 25
        data = self._make_daily_prices(volumes)
        result = compute_volume_metrics(data, today_volume=50000, max_period=21)
        assert result["is_volume_breakout"] is False

    def test_none_volume(self):
        volumes = [100000] * 25
        data = self._make_daily_prices(volumes)
        result = compute_volume_metrics(data, today_volume=None)
        assert result["is_volume_breakout"] is False

    def test_empty_data(self):
        result = compute_volume_metrics([], today_volume=100000)
        assert result["max_vol_21d"] is None
        assert result["is_volume_breakout"] is False
