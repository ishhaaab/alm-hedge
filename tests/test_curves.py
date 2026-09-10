import numpy as np
import pytest

from alm_hedge_lab.curves import ZeroCurve


@pytest.fixture
def curve() -> ZeroCurve:
    return ZeroCurve([2, 5, 10, 20, 30], [0.03, 0.032, 0.035, 0.038, 0.04])


def test_interpolates_zero_rates(curve: ZeroCurve) -> None:
    assert curve.zero_rate(7.5) == pytest.approx(0.0335)


def test_discount_factor_uses_continuous_compounding(curve: ZeroCurve) -> None:
    assert curve.discount_factor(10) == pytest.approx(np.exp(-0.35))
    assert curve.discount_factor(0) == pytest.approx(1.0)


def test_parallel_bump_moves_every_rate_one_basis_point(curve: ZeroCurve) -> None:
    bumped = curve.parallel_bump(1)
    np.testing.assert_allclose(bumped.rates - curve.rates, 0.0001)


def test_tenor_bump_only_moves_selected_node(curve: ZeroCurve) -> None:
    bumped = curve.tenor_bump(10, 1)
    np.testing.assert_allclose(
        bumped.rates - curve.rates,
        [0, 0, 0.0001, 0, 0],
        atol=1e-15,
    )


@pytest.mark.parametrize(
    ("tenors", "rates"),
    [([2, 5], [0.03]), ([5, 2], [0.03, 0.04]), ([0, 2], [0.03, 0.04])],
)
def test_rejects_invalid_curve_data(tenors: list[float], rates: list[float]) -> None:
    with pytest.raises(ValueError):
        ZeroCurve(tenors, rates)
