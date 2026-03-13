"""Tests for the screener engine."""

from datetime import date
from decimal import Decimal

import pytest

from stockpulse.engine.screener_engine import ScreenerEngine, _build_condition_clause
from stockpulse.models.event import Event
from stockpulse.models.screener import Screener, ScreenerCondition, ScreenerHistory
from tests.conftest import _make_indicator


class TestBuildConditionClause:
    """Test the condition → SQLAlchemy clause translation."""

    def test_is_true(self):
        cond = ScreenerCondition(field="is_volume_breakout", operator="is_true")
        clause = _build_condition_clause(cond)
        assert clause is not None

    def test_is_false(self):
        cond = ScreenerCondition(field="is_gap_up", operator="is_false")
        clause = _build_condition_clause(cond)
        assert clause is not None

    def test_gt(self):
        cond = ScreenerCondition(field="current_price", operator="gt", value=100)
        clause = _build_condition_clause(cond)
        assert clause is not None

    def test_gt_field(self):
        cond = ScreenerCondition(field="current_price", operator="gt_field", value="dma_50")
        clause = _build_condition_clause(cond)
        assert clause is not None

    def test_unknown_field_returns_none(self):
        cond = ScreenerCondition(field="nonexistent", operator="gt", value=100)
        clause = _build_condition_clause(cond)
        assert clause is None

    def test_unknown_operator_returns_none(self):
        cond = ScreenerCondition(field="current_price", operator="magic", value=100)
        clause = _build_condition_clause(cond)
        assert clause is None

    def test_in_with_list(self):
        cond = ScreenerCondition(field="dma_10_signal", operator="in", value=["Hold", "Reverse"])
        clause = _build_condition_clause(cond)
        assert clause is not None

    def test_color_eq(self):
        cond = ScreenerCondition(field="color", operator="eq", value="Green")
        clause = _build_condition_clause(cond)
        assert clause is not None


class TestScreenerEvaluate:
    """Integration tests for ScreenerEngine.evaluate()."""

    def _create_screener(self, db_session, conditions):
        """Helper to create a screener with conditions."""
        screener = Screener(
            name="Test Screener",
            slug="test-screener",
            is_builtin=False,
            is_active=True,
        )
        db_session.add(screener)
        db_session.flush()

        for i, (field, operator, value) in enumerate(conditions):
            db_session.add(ScreenerCondition(
                screener_id=screener.id,
                field=field,
                operator=operator,
                value=value,
                ordinal=i,
            ))
        db_session.flush()
        return screener

    def test_evaluate_volume_breakout(self, db_session, sample_stock, second_stock):
        """Screener for volume breakouts should match only the right stock."""
        as_of = date(2026, 3, 11)

        _make_indicator(db_session, sample_stock.id, as_of, is_volume_breakout=True)
        _make_indicator(db_session, second_stock.id, as_of, is_volume_breakout=False)

        screener = self._create_screener(db_session, [
            ("is_volume_breakout", "is_true", None),
        ])

        engine = ScreenerEngine(db_session)
        results = engine.evaluate(screener.id, as_of)

        assert len(results) == 1
        assert results[0]["stock_id"] == sample_stock.id

    def test_evaluate_price_gt(self, db_session, sample_stock):
        as_of = date(2026, 3, 11)
        _make_indicator(db_session, sample_stock.id, as_of, current_price=Decimal("1500.00"))

        screener = self._create_screener(db_session, [
            ("current_price", "gt", 1000),
        ])

        engine = ScreenerEngine(db_session)
        results = engine.evaluate(screener.id, as_of)
        assert len(results) == 1

    def test_evaluate_price_gt_no_match(self, db_session, sample_stock):
        as_of = date(2026, 3, 11)
        _make_indicator(db_session, sample_stock.id, as_of, current_price=Decimal("500.00"))

        screener = self._create_screener(db_session, [
            ("current_price", "gt", 1000),
        ])

        engine = ScreenerEngine(db_session)
        results = engine.evaluate(screener.id, as_of)
        assert len(results) == 0

    def test_evaluate_multiple_conditions_and(self, db_session, sample_stock):
        """Multiple conditions are ANDed together."""
        as_of = date(2026, 3, 11)
        _make_indicator(
            db_session, sample_stock.id, as_of,
            is_volume_breakout=True,
            is_52w_closing_high=True,
        )

        screener = self._create_screener(db_session, [
            ("is_volume_breakout", "is_true", None),
            ("is_52w_closing_high", "is_true", None),
        ])

        engine = ScreenerEngine(db_session)
        results = engine.evaluate(screener.id, as_of)
        assert len(results) == 1

    def test_evaluate_and_partial_match_fails(self, db_session, sample_stock):
        """If one AND condition fails, stock is excluded."""
        as_of = date(2026, 3, 11)
        _make_indicator(
            db_session, sample_stock.id, as_of,
            is_volume_breakout=True,
            is_52w_closing_high=False,
        )

        screener = self._create_screener(db_session, [
            ("is_volume_breakout", "is_true", None),
            ("is_52w_closing_high", "is_true", None),
        ])

        engine = ScreenerEngine(db_session)
        results = engine.evaluate(screener.id, as_of)
        assert len(results) == 0

    def test_evaluate_gt_field(self, db_session, sample_stock):
        """Relative comparison: current_price > dma_50."""
        as_of = date(2026, 3, 11)
        _make_indicator(
            db_session, sample_stock.id, as_of,
            current_price=Decimal("1200.00"),
            dma_50=Decimal("1100.00"),
        )

        screener = self._create_screener(db_session, [
            ("current_price", "gt_field", "dma_50"),
        ])

        engine = ScreenerEngine(db_session)
        results = engine.evaluate(screener.id, as_of)
        assert len(results) == 1

    def test_evaluate_nonexistent_screener(self, db_session):
        engine = ScreenerEngine(db_session)
        results = engine.evaluate(99999)
        assert results == []

    def test_preview(self, db_session, sample_stock):
        """Preview with ad-hoc conditions."""
        as_of = date(2026, 3, 11)
        _make_indicator(db_session, sample_stock.id, as_of, is_gap_up=True)

        engine = ScreenerEngine(db_session)
        results = engine.preview([{"field": "is_gap_up", "operator": "is_true"}], as_of)
        assert len(results) == 1


class TestRecordHistory:
    """Test screener history tracking and event generation."""

    def _create_screener(self, db_session, conditions):
        screener = Screener(
            name="History Test",
            slug="history-test",
            is_builtin=False,
            is_active=True,
        )
        db_session.add(screener)
        db_session.flush()

        for i, (field, operator, value) in enumerate(conditions):
            db_session.add(ScreenerCondition(
                screener_id=screener.id,
                field=field,
                operator=operator,
                value=value,
                ordinal=i,
            ))
        db_session.flush()
        return screener

    def test_first_run_all_entries(self, db_session, sample_stock):
        """First run with no history — all matches are entries."""
        as_of = date(2026, 3, 11)
        _make_indicator(db_session, sample_stock.id, as_of, is_volume_breakout=True)

        screener = self._create_screener(db_session, [
            ("is_volume_breakout", "is_true", None),
        ])

        engine = ScreenerEngine(db_session)
        result = engine.record_history(screener.id, as_of)

        assert result["entered"] == 1
        assert result["exited"] == 0
        assert result["events"] == 1

        # Verify Event was created
        events = db_session.query(Event).filter(
            Event.stock_id == sample_stock.id,
            Event.event_type == "SCREENER_ENTRY",
        ).all()
        assert len(events) == 1
        assert events[0].payload["screener_name"] == "History Test"

    def test_exit_generates_event(self, db_session, sample_stock):
        """Stock leaving a screener should generate SCREENER_EXIT."""
        day1 = date(2026, 3, 10)
        day2 = date(2026, 3, 11)

        screener = self._create_screener(db_session, [
            ("is_volume_breakout", "is_true", None),
        ])

        # Day 1: stock matches
        _make_indicator(db_session, sample_stock.id, day1, is_volume_breakout=True)
        engine = ScreenerEngine(db_session)
        engine.record_history(screener.id, day1)
        db_session.flush()

        # Day 2: stock no longer matches
        _make_indicator(db_session, sample_stock.id, day2, is_volume_breakout=False)
        result = engine.record_history(screener.id, day2)

        assert result["entered"] == 0
        assert result["exited"] == 1
        assert result["events"] == 1

        exit_events = db_session.query(Event).filter(
            Event.stock_id == sample_stock.id,
            Event.event_type == "SCREENER_EXIT",
        ).all()
        assert len(exit_events) == 1

    def test_no_change_no_events(self, db_session, sample_stock):
        """Stock staying in screener should not generate new events."""
        day1 = date(2026, 3, 10)
        day2 = date(2026, 3, 11)

        screener = self._create_screener(db_session, [
            ("is_volume_breakout", "is_true", None),
        ])

        _make_indicator(db_session, sample_stock.id, day1, is_volume_breakout=True)
        engine = ScreenerEngine(db_session)
        engine.record_history(screener.id, day1)
        db_session.flush()

        _make_indicator(db_session, sample_stock.id, day2, is_volume_breakout=True)
        result = engine.record_history(screener.id, day2)

        assert result["entered"] == 0
        assert result["exited"] == 0
        assert result["events"] == 0

    def test_nonexistent_screener(self, db_session):
        engine = ScreenerEngine(db_session)
        result = engine.record_history(99999, date(2026, 3, 11))
        assert result == {"entered": 0, "exited": 0, "events": 0}
