from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .curves import ZeroCurve
from .instruments import declining_annuity, fixed_rate_bond, payer_swap
from .portfolio import BalanceSheet, Portfolio


@dataclass(frozen=True)
class MarketSnapshot:
    as_of: date
    curve: ZeroCurve
    source: str


def bundled_market() -> MarketSnapshot:
    return MarketSnapshot(
        as_of=date(2025, 1, 2),
        curve=ZeroCurve([2, 5, 10, 20, 30], [0.0425, 0.0438, 0.0457, 0.0486, 0.0479]),
        source="Bundled FRED snapshot",
    )


def sample_balance_sheet() -> BalanceSheet:
    assets = Portfolio(
        "General account assets",
        [
            fixed_rate_bond("5Y Treasury", 38_000_000, 0.04, 5),
            fixed_rate_bond("10Y Treasury", 30_000_000, 0.0425, 10),
            fixed_rate_bond("20Y Treasury", 22_000_000, 0.045, 20),
            fixed_rate_bond("30Y Treasury", 18_000_000, 0.0475, 30),
            payer_swap("10Y payer swap", 8_000_000, 0.043, 10),
            payer_swap("30Y payer swap", 10_000_000, 0.046, 30),
        ],
    )
    liabilities = Portfolio(
        "Annuity liabilities",
        [declining_annuity("30Y annuity block", 7_200_000, 30, 0.025)],
    )
    return BalanceSheet(assets, liabilities)
