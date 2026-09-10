from datetime import date

import pytest

from alm_hedge_lab.sample import MarketSnapshot, bundled_market, sample_balance_sheet
from alm_hedge_lab.validation import ValidationError, validate_market


def test_current_complete_curve_passes_validation() -> None:
    market = bundled_market()
    results = validate_market(market, sample_balance_sheet(), today=market.as_of)
    assert all(item.passed for item in results)


def test_stale_curve_stops_the_run() -> None:
    market = bundled_market()
    with pytest.raises(ValidationError, match="Curve freshness"):
        validate_market(market, sample_balance_sheet(), today=date(2025, 2, 1))


def test_missing_tenor_stops_the_run() -> None:
    market = bundled_market()
    incomplete = MarketSnapshot(market.as_of, market.curve.__class__([2, 5, 10, 30], market.curve.rates[:4]), "test")
    with pytest.raises(ValidationError, match="Required tenors"):
        validate_market(incomplete, sample_balance_sheet(), today=market.as_of)
