from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .curves import ZeroCurve
from .instruments import CashflowPosition
from .sensitivities import effective_duration, key_rate_risk


@dataclass(frozen=True)
class Portfolio:
    name: str
    positions: tuple[CashflowPosition, ...]

    def __init__(self, name: str, positions: Iterable[CashflowPosition]) -> None:
        items = tuple(positions)
        if not items:
            raise ValueError("a portfolio needs at least one position")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "positions", items)

    def present_value(self, curve: ZeroCurve) -> float:
        return sum(position.present_value(curve) for position in self.positions)

    def effective_duration(self, curve: ZeroCurve) -> float:
        value = self.present_value(curve)
        if value == 0:
            raise ValueError("duration is undefined for a zero-value portfolio")
        weighted_duration = sum(
            position.present_value(curve) * effective_duration(position, curve)
            for position in self.positions
        )
        return weighted_duration / value

    def pv01_ladder(self, curve: ZeroCurve) -> dict[float, float]:
        ladder = {float(tenor): 0.0 for tenor in curve.tenors}
        for position in self.positions:
            for risk in key_rate_risk(position, curve):
                ladder[risk.tenor] += risk.pv01
        return ladder


@dataclass(frozen=True)
class BalanceSheet:
    assets: Portfolio
    liabilities: Portfolio

    def values(self, curve: ZeroCurve) -> dict[str, float]:
        assets = self.assets.present_value(curve)
        liabilities = self.liabilities.present_value(curve)
        return {
            "assets": assets,
            "liabilities": liabilities,
            "surplus": assets - liabilities,
        }

    def duration_gap(self, curve: ZeroCurve) -> float:
        values = self.values(curve)
        if values["assets"] == 0:
            raise ValueError("duration gap is undefined when asset value is zero")
        return self.assets.effective_duration(curve) - (
            values["liabilities"]
            / values["assets"]
            * self.liabilities.effective_duration(curve)
        )

    def surplus_pv01_ladder(self, curve: ZeroCurve) -> dict[float, float]:
        asset_ladder = self.assets.pv01_ladder(curve)
        liability_ladder = self.liabilities.pv01_ladder(curve)
        return {
            tenor: asset_ladder[tenor] - liability_ladder[tenor]
            for tenor in asset_ladder
        }
