import math

import numpy as np
import pytest

from alm_hedge_lab.curves import ZeroCurve, bootstrap_zero_curve
from alm_hedge_lab.instruments import fixed_rate_bond


def _par_price(par_yield: float, maturity: float, zero_rates: dict[float, float]) -> float:
    tenors = sorted(zero_rates)
    rates = [zero_rates[tenor] for tenor in tenors]
    coupon = par_yield / 2 * 100.0
    times = np.arange(1, int(maturity * 2) + 1, dtype=float) / 2
    interpolated = np.interp(times, tenors, rates)
    return float(np.sum(coupon * np.exp(-interpolated * times)) + 100 * np.exp(-interpolated[-1] * maturity))


def test_flat_par_curve_maps_to_continuous_equivalent() -> None:
    # A 4% semi-annual par yield implies a continuous zero of 2*ln(1.02).
    # The bootstrap converts payment frequency instead of copying the number across.
    curve = bootstrap_zero_curve([2, 5, 10], [0.04, 0.04, 0.04])
    np.testing.assert_allclose(curve.rates, [2 * math.log(1.02)] * 3, rtol=1e-6)
    assert curve.discount_factor(0) == pytest.approx(1.0)


def test_bootstrapped_curve_reprices_each_par_bond() -> None:
    par_yields = [0.0425, 0.0438, 0.0457, 0.0486, 0.0479]
    curve = bootstrap_zero_curve([2, 5, 10, 20, 30], par_yields)
    zero_rates = dict(zip([2.0, 5.0, 10.0, 20.0, 30.0], curve.rates.tolist()))
    for tenor, par in zip([2, 5, 10, 20, 30], par_yields):
        assert _par_price(par, tenor, zero_rates) == pytest.approx(100.0, rel=1e-6)


def test_bootstrap_differs_from_par_as_zero_shortcut() -> None:
    par_yields = [0.0425, 0.0438, 0.0457, 0.0486, 0.0479]
    bootstrapped = bootstrap_zero_curve([2, 5, 10, 20, 30], par_yields)
    naive = ZeroCurve([2, 5, 10, 20, 30], par_yields)
    bond = fixed_rate_bond("30Y Treasury", 1_000_000, 0.0475, 30)
    assert bond.present_value(bootstrapped) != pytest.approx(bond.present_value(naive))


def test_bootstrap_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        bootstrap_zero_curve([5, 2], [0.03, 0.04])
    with pytest.raises(ValueError):
        bootstrap_zero_curve([2, 5], [0.03])
    with pytest.raises(ValueError):
        bootstrap_zero_curve([2, 5], [0.03, 0.04], payments_per_year=0)


def test_bootstrap_rejects_tenor_off_the_coupon_grid() -> None:
    with pytest.raises(ValueError, match="coupon date"):
        bootstrap_zero_curve([2, 5, 7.2], [0.03, 0.035, 0.04])
