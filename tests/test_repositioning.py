import pytest

from alm_hedge_lab.instruments import CashflowPosition, fixed_rate_bond
from alm_hedge_lab.portfolio import BalanceSheet, Portfolio
from alm_hedge_lab.repositioning import TradeCandidate, recommend_long_end_trade
from alm_hedge_lab.sample import bundled_market, sample_balance_sheet


def treasury_candidates() -> tuple[TradeCandidate, ...]:
    return (
        TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=5.0, lot_size=100_000),
        TradeCandidate("30Y Treasury", 30, 0.0475, transaction_cost_bp=5.0, lot_size=100_000),
    )


def test_recommendation_closes_long_end_gap_to_limit() -> None:
    recommendation = recommend_long_end_trade(
        sample_balance_sheet(), bundled_market().curve, 5_000, treasury_candidates()
    )
    assert recommendation is not None
    assert abs(recommendation.after_pv01) <= 5_000
    assert recommendation.face_value != 0
    assert abs(recommendation.face_value) % 100_000 == pytest.approx(0)


def test_recommendation_reports_turnover_and_cost() -> None:
    candidates = treasury_candidates()
    recommendation = recommend_long_end_trade(
        sample_balance_sheet(), bundled_market().curve, 5_000, candidates
    )
    assert recommendation is not None
    assert recommendation.turnover == pytest.approx(abs(recommendation.face_value))
    winning_cost_bp = next(
        candidate.transaction_cost_bp
        for candidate in candidates
        if candidate.name == recommendation.instrument
    )
    assert recommendation.transaction_cost == pytest.approx(
        recommendation.turnover * winning_cost_bp / 10_000
    )


def test_no_trade_when_book_is_inside_limit() -> None:
    recommendation = recommend_long_end_trade(
        sample_balance_sheet(), bundled_market().curve, 1_000_000, treasury_candidates()
    )
    assert recommendation is None


def test_no_trade_when_cost_exceeds_repair() -> None:
    recommendation = recommend_long_end_trade(
        sample_balance_sheet(),
        bundled_market().curve,
        5_000,
        candidates=(
            TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=10_000.0, lot_size=100_000),
        ),
    )
    assert recommendation is None


def test_cost_guard_binds_at_the_capital_value_of_the_repair() -> None:
    sheet = sample_balance_sheet()
    curve = bundled_market().curve
    candidate = TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=1.0, lot_size=100_000)
    cheap = recommend_long_end_trade(sheet, curve, 5_000, candidates=(candidate,))
    assert cheap is not None
    pv01_repaired = abs(cheap.before_pv01) - abs(cheap.after_pv01)
    break_even_bp = 15.0 * pv01_repaired / cheap.turnover * 10_000
    over = recommend_long_end_trade(
        sheet,
        curve,
        5_000,
        candidates=(
            TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=break_even_bp * 1.01, lot_size=100_000),
        ),
    )
    under = recommend_long_end_trade(
        sheet,
        curve,
        5_000,
        candidates=(
            TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=break_even_bp * 0.99, lot_size=100_000),
        ),
    )
    assert over is None
    assert under is not None


def test_recommendation_sells_when_book_is_long_long_end() -> None:
    curve = bundled_market().curve
    assets = Portfolio(
        "assets",
        [fixed_rate_bond("30Y Treasury", 300_000_000, 0.0475, 30)],
    )
    liabilities = Portfolio(
        "liabilities", [CashflowPosition("liabilities", [5, 10, 20, 30], [100.0] * 4)]
    )
    recommendation = recommend_long_end_trade(
        BalanceSheet(assets, liabilities), curve, 5_000, treasury_candidates()
    )
    assert recommendation is not None
    assert recommendation.face_value < 0
    assert abs(recommendation.after_pv01) <= 5_000


def test_picker_prefers_the_cheaper_candidate() -> None:
    recommendation = recommend_long_end_trade(
        sample_balance_sheet(),
        bundled_market().curve,
        5_000,
        candidates=(
            TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=1.0, lot_size=100_000),
            TradeCandidate("30Y Treasury", 30, 0.0475, transaction_cost_bp=5.0, lot_size=100_000),
        ),
    )
    assert recommendation is not None
    assert recommendation.instrument == "20Y Treasury"


def test_rejects_negative_cost() -> None:
    with pytest.raises(ValueError, match="cost must be non-negative"):
        recommend_long_end_trade(
            sample_balance_sheet(),
            bundled_market().curve,
            5_000,
            candidates=(
                TradeCandidate("20Y Treasury", 20, 0.045, transaction_cost_bp=-1.0, lot_size=100_000),
            ),
        )