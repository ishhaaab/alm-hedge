from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


# The quoted tenor grid shared across the app. FRED's constant-maturity set,
# the bundled sample curve, and every curve built from par yields use these
# nodes, so a change to the grid is made in exactly one place.
QUOTED_TENORS = (2.0, 5.0, 10.0, 20.0, 30.0)


@dataclass(frozen=True)
class ZeroCurve:
    """Continuously compounded zero rates indexed by maturity in years."""

    tenors: NDArray[np.float64]
    rates: NDArray[np.float64]

    def __init__(self, tenors: ArrayLike, rates: ArrayLike) -> None:
        tenor_array = np.asarray(tenors, dtype=float)
        rate_array = np.asarray(rates, dtype=float)

        if tenor_array.ndim != 1 or rate_array.ndim != 1:
            raise ValueError("tenors and rates must be one-dimensional")
        if len(tenor_array) != len(rate_array) or len(tenor_array) < 2:
            raise ValueError("tenors and rates must have the same length of at least two")
        if not np.all(np.isfinite(tenor_array)) or not np.all(np.isfinite(rate_array)):
            raise ValueError("tenors and rates must be finite")
        if np.any(tenor_array <= 0) or np.any(np.diff(tenor_array) <= 0):
            raise ValueError("tenors must be positive and strictly increasing")

        object.__setattr__(self, "tenors", tenor_array)
        object.__setattr__(self, "rates", rate_array)

    def zero_rate(self, maturity: ArrayLike) -> NDArray[np.float64]:
        """Interpolate zero rates linearly between quoted tenors.

        Maturities outside the quoted range use the nearest node's rate
        (flat extrapolation), so long-dated cashflows are discounted at the
        30Y rate rather than a trend extrapolation.
        """
        maturities = np.asarray(maturity, dtype=float)
        if np.any(maturities < 0):
            raise ValueError("maturities cannot be negative")
        return np.interp(maturities, self.tenors, self.rates)

    def discount_factor(self, maturity: ArrayLike) -> NDArray[np.float64]:
        maturities = np.asarray(maturity, dtype=float)
        return np.exp(-self.zero_rate(maturities) * maturities)

    def parallel_bump(self, basis_points: float) -> ZeroCurve:
        return ZeroCurve(self.tenors, self.rates + basis_points / 10_000)

    def shifted(self, basis_points: ArrayLike) -> ZeroCurve:
        shifts = np.asarray(basis_points, dtype=float)
        if shifts.shape != self.rates.shape:
            raise ValueError("shifts must match the curve tenors")
        return ZeroCurve(self.tenors, self.rates + shifts / 10_000)

    def tenor_bump(self, tenor: float, basis_points: float) -> ZeroCurve:
        matches = np.flatnonzero(np.isclose(self.tenors, tenor, rtol=0, atol=1e-12))
        if len(matches) != 1:
            raise ValueError(f"{tenor:g}Y is not a curve tenor")
        bumped = self.rates.copy()
        bumped[matches[0]] += basis_points / 10_000
        return ZeroCurve(self.tenors, bumped)


def bootstrap_zero_curve(
    tenors: ArrayLike,
    par_yields: ArrayLike,
    payments_per_year: int = 2,
) -> ZeroCurve:
    """Build a continuously compounded zero curve from par yields.

    Each tenor is treated as the maturity of a par bond paying coupons
    ``payments_per_year`` times per year (semi-annual, the Treasury market
    convention behind the FRED constant-maturity series). Nodes are solved
    shortest-first: coupons on or before the last solved node are discounted
    with the curve built so far, while coupons between the last solved node
    and the node being solved use the same linear zero-rate interpolation the
    finished curve applies (a straight line from the last solved rate to the
    unknown node rate). The node rate is the unique value that prices its par
    bond at 100, found by bisection, so the finished curve reprices every
    input par bond by construction.
    """
    tenor_array = np.asarray(tenors, dtype=float)
    yield_array = np.asarray(par_yields, dtype=float)

    if tenor_array.ndim != 1 or yield_array.ndim != 1:
        raise ValueError("tenors and par yields must be one-dimensional")
    if len(tenor_array) != len(yield_array) or len(tenor_array) < 2:
        raise ValueError("tenors and par yields must have the same length of at least two")
    if not np.all(np.isfinite(tenor_array)) or not np.all(np.isfinite(yield_array)):
        raise ValueError("tenors and par yields must be finite")
    if np.any(tenor_array <= 0) or np.any(np.diff(tenor_array) <= 0):
        raise ValueError("tenors must be positive and strictly increasing")
    if payments_per_year <= 0:
        raise ValueError("payments per year must be positive")

    solved_tenors: list[float] = []
    solved_rates: list[float] = []

    def discount_at(times: ArrayLike) -> NDArray[np.float64]:
        """Discount factors from the curve solved so far.

        Uses linear interpolation of zero rates between solved nodes, the
        first solved rate for earlier times, and flat extrapolation of the
        last solved rate beyond it.
        """
        query = np.asarray(times, dtype=float)
        if not solved_tenors:
            raise ValueError("no curve nodes solved yet")
        known_tenors = np.array(solved_tenors)
        known_rates = np.array(solved_rates)
        interpolated = np.interp(query, known_tenors, known_rates)
        interpolated[query < known_tenors[0]] = known_rates[0]
        return np.exp(-interpolated * query)

    for tenor, par in zip(tenor_array.tolist(), yield_array.tolist()):
        periods = round(float(tenor) * payments_per_year)
        if periods <= 0 or not np.isclose(periods / payments_per_year, float(tenor)):
            raise ValueError(f"tenor {tenor:g}Y must fall on a coupon date")
        coupon = float(par) / payments_per_year * 100.0
        coupon_times = np.arange(1, periods + 1, dtype=float) / payments_per_year

        if solved_tenors:
            last_tenor = solved_tenors[-1]
            last_rate = solved_rates[-1]
            early = coupon_times[coupon_times <= last_tenor]
            middle = coupon_times[coupon_times > last_tenor]
            known_value = float(np.sum(discount_at(early))) if len(early) else 0.0
        else:
            last_tenor = 0.0
            last_rate = None
            middle = coupon_times
            known_value = 0.0

        def mispricing(zero: float) -> float:
            if len(middle):
                if last_rate is None:
                    segment_rates = np.full_like(middle, zero)
                else:
                    span = float(tenor) - last_tenor
                    weight = (middle - last_tenor) / span if span else np.ones_like(middle)
                    segment_rates = last_rate + weight * (zero - last_rate)
                middle_value = float(np.sum(np.exp(-segment_rates * middle)))
            else:
                middle_value = 0.0
            return coupon * (known_value + middle_value) + 100.0 * np.exp(-zero * float(tenor)) - 100.0

        low, high = -0.05, 0.50
        while mispricing(low) < 0:
            low *= 2
        while mispricing(high) > 0:
            high = high * 2 + 0.01
        for _ in range(200):
            mid = (low + high) / 2
            if mispricing(mid) > 0:
                low = mid
            else:
                high = mid
        rate = (low + high) / 2
        solved_tenors.append(float(tenor))
        solved_rates.append(rate)

    return ZeroCurve(tenor_array, np.array(solved_rates))
