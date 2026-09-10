import pytest

from alm_hedge_lab.hedge import capital_proxy, effectiveness_tests, pnl_attribution
from alm_hedge_lab.instruments import CashflowPosition
from alm_hedge_lab.portfolio import Portfolio
from alm_hedge_lab.sample import bundled_market
from alm_hedge_lab.scenarios import standard_scenarios


def matched_portfolios() -> tuple[Portfolio, Portfolio]:
    cashflow = CashflowPosition("cashflow", [5, 10, 20], [20, 30, 100])
    return Portfolio("hedge", [cashflow]), Portfolio("liability", [cashflow])


def test_identical_cashflows_pass_effectiveness_tests() -> None:
    hedge, liability = matched_portfolios()
    curve = bundled_market().curve
    tests = effectiveness_tests(hedge, liability, curve, standard_scenarios(curve))
    assert all(item.passed for item in tests)


def test_matched_cashflows_have_no_capital_proxy() -> None:
    hedge, liability = matched_portfolios()
    assert capital_proxy(hedge, liability, bundled_market().curve) == pytest.approx(0)


def test_attribution_reconciles_to_revaluation() -> None:
    curve = bundled_market().curve
    hedge = Portfolio("hedge", [CashflowPosition("hedge", [10], [90])])
    liability = Portfolio("liability", [CashflowPosition("liability", [10], [100])])
    result = pnl_attribution(hedge, liability, curve, standard_scenarios(curve)[0])
    assert result["rate"] + result["convexity and basis"] == pytest.approx(result["economic pnl"])
