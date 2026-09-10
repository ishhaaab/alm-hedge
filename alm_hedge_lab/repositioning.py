from __future__ import annotations

from dataclasses import dataclass

from .curves import ZeroCurve
from .instruments import fixed_rate_bond
from .portfolio import BalanceSheet, Portfolio


@dataclass(frozen=True)
class TradeRecommendation:
    instrument: str
    face_value: float
    before_pv01: float
    after_pv01: float


def recommend_long_end_trade(
    balance_sheet: BalanceSheet,
    curve: ZeroCurve,
    limit: float = 5_000,
) -> TradeRecommendation | None:
    ladder = balance_sheet.surplus_pv01_ladder(curve)
    before = sum(value for tenor, value in ladder.items() if tenor >= 10)
    if abs(before) <= limit:
        return None

    candidates = [
        fixed_rate_bond("20Y Treasury", 1_000_000, 0.045, 20),
        fixed_rate_bond("30Y Treasury", 1_000_000, 0.0475, 30),
    ]
    target = limit if before > limit else -limit
    needed = target - before
    best = max(
        candidates,
        key=lambda bond: abs(
            sum(value for tenor, value in Portfolio("trade", [bond]).pv01_ladder(curve).items() if tenor >= 10)
        ),
    )
    unit_risk = sum(
        value
        for tenor, value in Portfolio("trade", [best]).pv01_ladder(curve).items()
        if tenor >= 10
    )
    face_value = needed / unit_risk * 1_000_000
    return TradeRecommendation(best.name, face_value, before, target)
