from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


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
