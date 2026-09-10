from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .curves import ZeroCurve


@dataclass(frozen=True)
class CashflowPosition:
    name: str
    times: NDArray[np.float64]
    amounts: NDArray[np.float64]

    def __init__(self, name: str, times: ArrayLike, amounts: ArrayLike) -> None:
        time_array = np.asarray(times, dtype=float)
        amount_array = np.asarray(amounts, dtype=float)
        if time_array.ndim != 1 or amount_array.ndim != 1:
            raise ValueError("times and amounts must be one-dimensional")
        if len(time_array) == 0 or len(time_array) != len(amount_array):
            raise ValueError("times and amounts must have the same non-zero length")
        if np.any(time_array <= 0) or np.any(np.diff(time_array) <= 0):
            raise ValueError("cashflow times must be positive and strictly increasing")
        if not np.all(np.isfinite(amount_array)):
            raise ValueError("cashflow amounts must be finite")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "times", time_array)
        object.__setattr__(self, "amounts", amount_array)

    def present_value(self, curve: ZeroCurve) -> float:
        return float(np.dot(self.amounts, curve.discount_factor(self.times)))


def fixed_rate_bond(
    name: str,
    face_value: float,
    coupon_rate: float,
    maturity: float,
    payments_per_year: int = 2,
) -> CashflowPosition:
    periods = round(maturity * payments_per_year)
    if payments_per_year <= 0 or periods <= 0:
        raise ValueError("maturity and payment frequency must be positive")
    if not np.isclose(periods / payments_per_year, maturity):
        raise ValueError("maturity must fall on a coupon date")

    times = np.arange(1, periods + 1, dtype=float) / payments_per_year
    amounts = np.full(periods, face_value * coupon_rate / payments_per_year)
    amounts[-1] += face_value
    return CashflowPosition(name, times, amounts)


def level_annuity(
    name: str,
    annual_payment: float,
    years: int,
    payments_per_year: int = 1,
) -> CashflowPosition:
    periods = years * payments_per_year
    if periods <= 0:
        raise ValueError("years and payment frequency must be positive")
    times = np.arange(1, periods + 1, dtype=float) / payments_per_year
    amounts = np.full(periods, annual_payment / payments_per_year)
    return CashflowPosition(name, times, amounts)


def declining_annuity(
    name: str,
    first_payment: float,
    years: int,
    annual_decline: float = 0.02,
) -> CashflowPosition:
    if years <= 0 or first_payment <= 0:
        raise ValueError("years and first payment must be positive")
    if not 0 <= annual_decline < 1:
        raise ValueError("annual decline must be between zero and one")
    times = np.arange(1, years + 1, dtype=float)
    amounts = first_payment * (1 - annual_decline) ** np.arange(years)
    return CashflowPosition(name, times, amounts)


def payer_swap(
    name: str,
    notional: float,
    fixed_rate: float,
    maturity: int,
    payments_per_year: int = 2,
) -> CashflowPosition:
    """Approximate a receive-floating, pay-fixed swap at a coupon reset date."""
    fixed_leg = fixed_rate_bond(name, notional, fixed_rate, maturity, payments_per_year)
    times = np.concatenate(([1e-9], fixed_leg.times))
    amounts = np.concatenate(([notional], -fixed_leg.amounts))
    return CashflowPosition(name, times, amounts)
