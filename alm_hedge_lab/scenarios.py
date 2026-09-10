from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .curves import ZeroCurve
from .portfolio import BalanceSheet


@dataclass(frozen=True)
class Scenario:
    name: str
    shifts_bp: tuple[float, ...]

    def apply(self, curve: ZeroCurve) -> ZeroCurve:
        return curve.shifted(self.shifts_bp)


def standard_scenarios(curve: ZeroCurve) -> list[Scenario]:
    tenor = curve.tenors
    steepener = tuple(np.interp(tenor, [tenor[0], tenor[-1]], [-75, 75]))
    flattener = tuple(-value for value in steepener)
    return [
        Scenario("Rates +100 bp", tuple(np.full(len(tenor), 100.0))),
        Scenario("Rates -100 bp", tuple(np.full(len(tenor), -100.0))),
        Scenario("Steepener", steepener),
        Scenario("Flattener", flattener),
        Scenario("2008 replay", (-142, -142, -147, -145, -164)),
    ]


def scenario_results(
    balance_sheet: BalanceSheet,
    curve: ZeroCurve,
    scenarios: list[Scenario],
) -> list[dict[str, float | str]]:
    base_surplus = balance_sheet.values(curve)["surplus"]
    results = []
    for scenario in scenarios:
        shocked_surplus = balance_sheet.values(scenario.apply(curve))["surplus"]
        results.append(
            {
                "scenario": scenario.name,
                "surplus": shocked_surplus,
                "change": shocked_surplus - base_surplus,
            }
        )
    return results
