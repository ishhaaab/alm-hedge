import pytest

from alm_hedge_lab.curves import ZeroCurve
from alm_hedge_lab.instruments import CashflowPosition
from alm_hedge_lab.sensitivities import effective_duration, key_rate_risk, pv01


def test_zero_coupon_pv01_matches_direct_revaluation() -> None:
    curve = ZeroCurve([5, 10], [0.04, 0.04])
    position = CashflowPosition("10Y zero", [10], [100])
    assert pv01(position, curve) == pytest.approx(
        position.present_value(curve) - position.present_value(curve.parallel_bump(1))
    )


def test_zero_coupon_duration_equals_maturity() -> None:
    curve = ZeroCurve([5, 10], [0.04, 0.04])
    position = CashflowPosition("10Y zero", [10], [100])
    assert effective_duration(position, curve) == pytest.approx(10, rel=1e-6)


def test_key_rate_pv01_reconciles_to_parallel_pv01() -> None:
    curve = ZeroCurve([2, 5, 10, 20, 30], [0.03, 0.032, 0.035, 0.038, 0.04])
    position = CashflowPosition("mixed cashflows", [1, 4, 8, 15, 25, 30], [5, 5, 5, 5, 5, 105])
    ladder = key_rate_risk(position, curve)
    assert sum(item.pv01 for item in ladder) == pytest.approx(pv01(position, curve), rel=2e-4)
    assert all(item.convexity >= 0 for item in ladder)
