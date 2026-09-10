from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .curves import ZeroCurve
from .portfolio import Portfolio
from .scenarios import Scenario


@dataclass(frozen=True)
class HedgeTest:
    name: str
    value: float
    passed: bool
    threshold: str


def capital_proxy(hedges: Portfolio, liabilities: Portfolio, curve: ZeroCurve) -> float:
    hedge_ladder = hedges.pv01_ladder(curve)
    liability_ladder = liabilities.pv01_ladder(curve)
    residual = sum(abs(hedge_ladder[tenor] - liability_ladder[tenor]) for tenor in hedge_ladder)
    return 0.15 * residual * 100


def effectiveness_tests(
    hedges: Portfolio,
    liabilities: Portfolio,
    curve: ZeroCurve,
    scenarios: list[Scenario],
) -> list[HedgeTest]:
    hedge_base = hedges.present_value(curve)
    liability_base = liabilities.present_value(curve)
    hedge_moves = np.array(
        [hedges.present_value(item.apply(curve)) - hedge_base for item in scenarios]
    )
    liability_moves = np.array(
        [liabilities.present_value(item.apply(curve)) - liability_base for item in scenarios]
    )

    total_liability_move = np.sum(np.abs(liability_moves))
    dollar_offset = (
        np.sum(np.abs(hedge_moves)) / total_liability_move if total_liability_move else 0.0
    )
    slope, intercept = np.polyfit(hedge_moves, liability_moves, 1)
    fitted = slope * hedge_moves + intercept
    residual = np.sum((liability_moves - fitted) ** 2)
    total = np.sum((liability_moves - np.mean(liability_moves)) ** 2)
    r_squared = 1 - residual / total if total else 0.0

    hedge_ladder = hedges.pv01_ladder(curve)
    liability_ladder = liabilities.pv01_ladder(curve)
    covered = sum(
        min(abs(hedge_ladder[tenor]), abs(value)) for tenor, value in liability_ladder.items()
    )
    coverage = covered / sum(abs(value) for value in liability_ladder.values())

    return [
        HedgeTest("Dollar offset", dollar_offset, 0.8 <= dollar_offset <= 1.25, "80% to 125%"),
        HedgeTest(
            "Regression R-squared",
            r_squared,
            r_squared >= 0.8 and 0.8 <= slope <= 1.25,
            "R-squared >= 80%, slope 0.80 to 1.25",
        ),
        HedgeTest("Key-rate coverage", coverage, coverage >= 0.8, ">= 80%"),
    ]


def pnl_attribution(
    hedges: Portfolio,
    liabilities: Portfolio,
    curve: ZeroCurve,
    scenario: Scenario,
) -> dict[str, float]:
    shocked = scenario.apply(curve)
    actual = (
        hedges.present_value(shocked)
        - hedges.present_value(curve)
        - liabilities.present_value(shocked)
        + liabilities.present_value(curve)
    )
    hedge_ladder = hedges.pv01_ladder(curve)
    liability_ladder = liabilities.pv01_ladder(curve)
    rate_pnl = -sum(
        (hedge_ladder[tenor] - liability_ladder[tenor]) * shift
        for tenor, shift in zip(hedge_ladder, scenario.shifts_bp)
    )
    convexity = actual - rate_pnl
    capital = -capital_proxy(hedges, liabilities, shocked)
    return {
        "rate": rate_pnl,
        "convexity and basis": convexity,
        "capital proxy": capital,
        "economic pnl": actual,
        "pnl after capital": actual + capital,
    }
