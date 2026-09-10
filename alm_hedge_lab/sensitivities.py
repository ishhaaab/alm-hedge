from __future__ import annotations

from dataclasses import dataclass

from .curves import ZeroCurve
from .instruments import CashflowPosition


@dataclass(frozen=True)
class KeyRateRisk:
    tenor: float
    pv01: float
    convexity: float


def pv01(position: CashflowPosition, curve: ZeroCurve) -> float:
    """Return the value gained when all rates fall by one basis point."""
    return position.present_value(curve) - position.present_value(curve.parallel_bump(1))


def effective_duration(position: CashflowPosition, curve: ZeroCurve) -> float:
    value = position.present_value(curve)
    if value == 0:
        raise ValueError("duration is undefined for a zero-value position")
    down = position.present_value(curve.parallel_bump(-1))
    up = position.present_value(curve.parallel_bump(1))
    return (down - up) / (2 * value * 0.0001)


def key_rate_risk(position: CashflowPosition, curve: ZeroCurve) -> list[KeyRateRisk]:
    base_value = position.present_value(curve)
    bump = 0.0001
    results = []
    for tenor in curve.tenors:
        up_value = position.present_value(curve.tenor_bump(float(tenor), 1))
        down_value = position.present_value(curve.tenor_bump(float(tenor), -1))
        results.append(
            KeyRateRisk(
                tenor=float(tenor),
                pv01=base_value - up_value,
                convexity=(down_value + up_value - 2 * base_value) / bump**2,
            )
        )
    return results
