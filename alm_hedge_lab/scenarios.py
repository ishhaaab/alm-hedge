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
    """Return the standard 20-scenario grid used for stress and hedge tests.

    Parallel shifts (+/-100 bp, +/-50 bp) and scaled twists (a linear
    steepener/flattener pinned at +/-75 bp at the shortest/longest quoted
    tenor, plus a 1.5x version) cover directional and rotation risk. The 2008
    replay and its half-size variant add a historical stress, and single-node
    +/-25 bp key-rate shocks isolate each quoted tenor so the regression in
    ``effectiveness_tests`` sees tenor-level co-movement rather than only
    parallel moves.
    """
    tenor = curve.tenors
    steepener = tuple(np.interp(tenor, [tenor[0], tenor[-1]], [-75, 75]))
    flattener = tuple(-value for value in steepener)
    key_rate_shocks = [
        Scenario(
            f"{node:g}Y {suffix}",
            tuple(sign * 25.0 if abs(node - quoted) < 1e-9 else 0.0 for quoted in tenor),
        )
        for sign, suffix in ((1.0, "+25 bp"), (-1.0, "-25 bp"))
        for node in tenor
    ]
    return [
        Scenario("Rates +100 bp", tuple(np.full(len(tenor), 100.0))),
        Scenario("Rates -100 bp", tuple(np.full(len(tenor), -100.0))),
        Scenario("Rates +50 bp", tuple(np.full(len(tenor), 50.0))),
        Scenario("Rates -50 bp", tuple(np.full(len(tenor), -50.0))),
        Scenario("Steepener", steepener),
        Scenario("Flattener", flattener),
        Scenario("Steepener +50%", tuple(value * 1.5 for value in steepener)),
        Scenario("Flattener +50%", tuple(value * 1.5 for value in flattener)),
        Scenario("2008 replay", (-212, -173, -166, -134, -166)),
        Scenario("2008 replay half", (-106, -86.5, -83, -67, -83)),
        *key_rate_shocks,
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
