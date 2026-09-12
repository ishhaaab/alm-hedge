from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .curves import QUOTED_TENORS, ZeroCurve, bootstrap_zero_curve
from .instruments import declining_annuity, fixed_rate_bond, payer_swap
from .portfolio import BalanceSheet, Portfolio


@dataclass(frozen=True)
class MarketSnapshot:
    as_of: date
    curve: ZeroCurve
    source: str


HISTORICAL_CURVES = [
    (date(2024, 1, 31), [0.0427, 0.0391, 0.0399, 0.0434, 0.0422]),
    (date(2024, 2, 29), [0.0464, 0.0426, 0.0425, 0.0451, 0.0438]),
    (date(2024, 3, 28), [0.0459, 0.0421, 0.0420, 0.0445, 0.0434]),
    (date(2024, 4, 30), [0.0504, 0.0472, 0.0469, 0.0490, 0.0479]),
    (date(2024, 5, 31), [0.0489, 0.0452, 0.0451, 0.0473, 0.0465]),
    (date(2024, 6, 28), [0.0471, 0.0433, 0.0436, 0.0461, 0.0451]),
    (date(2024, 7, 31), [0.0429, 0.0397, 0.0409, 0.0444, 0.0435]),
    (date(2024, 8, 30), [0.0391, 0.0371, 0.0391, 0.0428, 0.0420]),
    (date(2024, 9, 30), [0.0366, 0.0358, 0.0381, 0.0419, 0.0414]),
    (date(2024, 10, 31), [0.0416, 0.0415, 0.0428, 0.0458, 0.0447]),
    (date(2024, 11, 29), [0.0413, 0.0405, 0.0418, 0.0445, 0.0436]),
    (date(2024, 12, 31), [0.0425, 0.0438, 0.0458, 0.0486, 0.0478]),
    (date(2025, 1, 2), [0.0425, 0.0438, 0.0457, 0.0486, 0.0479]),
]


def bundled_market() -> MarketSnapshot:
    return MarketSnapshot(
        as_of=date(2025, 1, 2),
        curve=bootstrap_zero_curve(QUOTED_TENORS, [0.0425, 0.0438, 0.0457, 0.0486, 0.0479]),
        source="Bundled FRED snapshot",
    )


def bundled_history() -> list[MarketSnapshot]:
    return [
        MarketSnapshot(as_of, bootstrap_zero_curve(QUOTED_TENORS, rates), "FRED historical snapshot")
        for as_of, rates in HISTORICAL_CURVES
    ]


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
