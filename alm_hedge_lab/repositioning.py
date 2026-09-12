from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .curves import ZeroCurve
from .instruments import CashflowPosition, fixed_rate_bond
from .portfolio import BalanceSheet, Portfolio


@dataclass(frozen=True)
class TradeRecommendation:
    instrument: str
    face_value: float
    before_pv01: float
    after_pv01: float
    turnover: float
    transaction_cost: float


@dataclass(frozen=True)
class TradeCandidate:
    """A hedge candidate priced under the caller's trading assumptions.

    ``transaction_cost_bp`` and ``lot_size`` are inputs, not market data. The
    app lets the user set them in the sidebar, so nobody mistakes an assumption
    for a fact that was looked up.
    """

    name: str
    maturity: float
    coupon_rate: float
    transaction_cost_bp: float
    lot_size: float


# Tenors at or above this count as the "long end" of the surplus ladder.
LONG_END_FROM_TENOR = 10.0

# The capital proxy charges 15% of the loss from a 100 bp move against each
# dollar of residual key-rate PV01, so the capital a trade releases is 15 * the
# PV01 it repairs. A trade that costs more than that is uneconomical: it spends
# more money than the risk it removes is worth in this model.
CAPITAL_RELEASE_PER_PV01 = 0.15 * 100


def _long_end_pv01(ladder: dict[float, float]) -> float:
    """Sum the key-rate buckets at and above ``LONG_END_FROM_TENOR``."""
    return sum(value for tenor, value in ladder.items() if tenor >= LONG_END_FROM_TENOR)


def _long_end_risk(positions: Iterable[CashflowPosition], curve: ZeroCurve) -> float:
    """Surplus PV01 at the long-end nodes of a position set."""
    return _long_end_pv01(Portfolio("trade", positions).pv01_ladder(curve))


def recommend_long_end_trade(
    balance_sheet: BalanceSheet,
    curve: ZeroCurve,
    limit: float,
    candidates: tuple[TradeCandidate, ...],
) -> TradeRecommendation | None:
    """Pick the cheapest candidate Treasury trade that restores the limit.

    The caller supplies the candidates and the assumptions that price them:
    trading cost in basis points and lot size. The app exposes those in the
    sidebar so the ticket reads as a set of inputs, not market facts. Each
    candidate is priced at par (face value as clean price), scaled to the
    face that moves 10Y+ surplus PV01 onto the nearer limit edge, then
    rounded up to the candidate lot size. Candidates that cannot reach the
    limit, round to zero face, or cost more than the capital the PV01 repair
    releases are reported as not economical (``None``). The cheapest
    compliant trade wins; ties break toward lower turnover.
    """
    ladder = balance_sheet.surplus_pv01_ladder(curve)
    before = _long_end_pv01(ladder)
    if abs(before) <= limit:
        return None

    direction = -1.0 if before > 0 else 1.0
    target = limit if before > limit else -limit
    needed = target - before

    options: list[TradeRecommendation] = []
    for candidate in candidates:
        if candidate.lot_size <= 0:
            raise ValueError(f"{candidate.name}: lot size must be positive")
        if candidate.transaction_cost_bp < 0:
            raise ValueError(f"{candidate.name}: cost must be non-negative")
        unit = fixed_rate_bond(candidate.name, 1_000_000, candidate.coupon_rate, candidate.maturity)
        unit_risk = _long_end_risk([unit], curve)
        # A candidate works only if its risk has the same sign as the gap, so
        # the trade actually moves the book toward (not past) the limit edge.
        if unit_risk == 0 or (needed / unit_risk) * direction < 0:
            continue
        raw_face = needed / unit_risk * 1_000_000
        lots = int(np.ceil(abs(raw_face) / candidate.lot_size))
        if lots <= 0:
            continue
        face_value = np.sign(raw_face) * lots * candidate.lot_size
        achieved = face_value / 1_000_000 * unit_risk
        after = before + achieved
        if abs(after) > limit + 1e-6:
            continue
        turnover = abs(face_value)
        cost = turnover * candidate.transaction_cost_bp / 10_000
        pv01_repaired = abs(before) - abs(after)
        if pv01_repaired <= 0 or cost >= pv01_repaired * CAPITAL_RELEASE_PER_PV01:
            continue
        options.append(
            TradeRecommendation(candidate.name, face_value, before, after, turnover, cost)
        )

    if not options:
        return None
    return min(options, key=lambda item: (item.transaction_cost, item.turnover))
