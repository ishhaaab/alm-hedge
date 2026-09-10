import numpy as np
import pytest

from alm_hedge_lab.curves import ZeroCurve
from alm_hedge_lab.instruments import CashflowPosition, fixed_rate_bond, level_annuity


def test_cashflow_position_discounts_each_payment() -> None:
    curve = ZeroCurve([1, 2], [0.03, 0.04])
    position = CashflowPosition("two payments", [1, 2], [5, 105])
    expected = 5 * np.exp(-0.03) + 105 * np.exp(-0.08)
    assert position.present_value(curve) == pytest.approx(expected)


def test_bond_adds_principal_to_last_coupon() -> None:
    bond = fixed_rate_bond("5Y Treasury", 1_000, 0.04, 5, 2)
    assert len(bond.times) == 10
    assert bond.amounts[0] == pytest.approx(20)
    assert bond.amounts[-1] == pytest.approx(1_020)


def test_annuity_splits_annual_payment_by_frequency() -> None:
    annuity = level_annuity("liability", 12_000, 2, 12)
    assert len(annuity.times) == 24
    np.testing.assert_allclose(annuity.amounts, 1_000)
