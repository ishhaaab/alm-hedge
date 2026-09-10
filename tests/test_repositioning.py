from alm_hedge_lab.repositioning import recommend_long_end_trade
from alm_hedge_lab.sample import bundled_market, sample_balance_sheet


def test_recommendation_closes_long_end_gap_to_limit() -> None:
    recommendation = recommend_long_end_trade(sample_balance_sheet(), bundled_market().curve, 5_000)
    assert recommendation is not None
    assert abs(recommendation.after_pv01) == 5_000
    assert recommendation.face_value != 0


def test_no_trade_when_book_is_inside_limit() -> None:
    recommendation = recommend_long_end_trade(sample_balance_sheet(), bundled_market().curve, 1_000_000)
    assert recommendation is None
