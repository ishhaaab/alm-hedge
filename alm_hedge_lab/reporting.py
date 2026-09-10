from __future__ import annotations

from dataclasses import dataclass

from .curves import ZeroCurve
from .hedge import HedgeTest
from .portfolio import BalanceSheet


@dataclass(frozen=True)
class Breach:
    measure: str
    status: str
    observed: float
    limit: float
    scenario: str = "Base"


def assess_limits(
    balance_sheet: BalanceSheet,
    curve: ZeroCurve,
    hedge_tests: list[HedgeTest],
    duration_warning: float = 0.5,
    duration_limit: float = 1.0,
    long_end_limit: float = 5_000,
) -> list[Breach]:
    gap = balance_sheet.duration_gap(curve)
    long_end = sum(
        value
        for tenor, value in balance_sheet.surplus_pv01_ladder(curve).items()
        if tenor >= 10
    )
    results = []
    if abs(gap) > duration_limit:
        results.append(Breach("Duration gap", "Limit", gap, duration_limit))
    elif abs(gap) > duration_warning:
        results.append(Breach("Duration gap", "Warning", gap, duration_warning))
    if abs(long_end) > long_end_limit:
        results.append(Breach("10Y+ surplus PV01", "Limit", long_end, long_end_limit))
    for test in hedge_tests:
        if not test.passed:
            results.append(Breach(test.name, "Failed test", test.value, 0.0))
    return results
