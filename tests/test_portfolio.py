import pytest

from alm_hedge_lab.curves import ZeroCurve
from alm_hedge_lab.instruments import CashflowPosition
from alm_hedge_lab.portfolio import BalanceSheet, Portfolio


@pytest.fixture
def curve() -> ZeroCurve:
    return ZeroCurve([2, 5, 10, 20, 30], [0.04] * 5)


def test_portfolio_value_is_sum_of_position_values(curve: ZeroCurve) -> None:
    first = CashflowPosition("first", [5], [100])
    second = CashflowPosition("second", [10], [200])
    portfolio = Portfolio("assets", [first, second])
    assert portfolio.present_value(curve) == pytest.approx(
        first.present_value(curve) + second.present_value(curve)
    )


def test_balance_sheet_reports_surplus(curve: ZeroCurve) -> None:
    assets = Portfolio("assets", [CashflowPosition("asset", [5], [120])])
    liabilities = Portfolio("liabilities", [CashflowPosition("liability", [5], [100])])
    values = BalanceSheet(assets, liabilities).values(curve)
    assert values["surplus"] == pytest.approx(values["assets"] - values["liabilities"])


def test_duration_gap_accounts_for_funding_ratio(curve: ZeroCurve) -> None:
    assets = Portfolio("assets", [CashflowPosition("asset", [5], [200])])
    liabilities = Portfolio("liabilities", [CashflowPosition("liability", [10], [100])])
    balance_sheet = BalanceSheet(assets, liabilities)
    liability_to_asset = (
        liabilities.present_value(curve) / assets.present_value(curve)
    )
    expected = 5 - liability_to_asset * 10
    assert balance_sheet.duration_gap(curve) == pytest.approx(expected, rel=1e-6)


def test_surplus_ladder_subtracts_liability_risk(curve: ZeroCurve) -> None:
    asset_position = CashflowPosition("asset", [10], [100])
    liability_position = CashflowPosition("liability", [10], [80])
    assets = Portfolio("assets", [asset_position])
    liabilities = Portfolio("liabilities", [liability_position])
    balance_sheet = BalanceSheet(assets, liabilities)

    net_ladder = balance_sheet.surplus_pv01_ladder(curve)
    asset_ladder = assets.pv01_ladder(curve)
    liability_ladder = liabilities.pv01_ladder(curve)
    assert net_ladder[10] == pytest.approx(asset_ladder[10] - liability_ladder[10])
    assert sum(abs(value) for tenor, value in net_ladder.items() if tenor != 10) == 0
