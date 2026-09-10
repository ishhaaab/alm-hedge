from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .market_data import FRED_SERIES
from .portfolio import BalanceSheet, Portfolio
from .sample import MarketSnapshot
from .sensitivities import pv01


@dataclass(frozen=True)
class ValidationResult:
    name: str
    passed: bool
    detail: str


class ValidationError(ValueError):
    pass


def validate_market(
    market: MarketSnapshot,
    balance_sheet: BalanceSheet,
    today: date | None = None,
    max_age_days: int = 10,
    pv01_tolerance: float = 0.001,
) -> list[ValidationResult]:
    current_date = today or date.today()
    required = set(FRED_SERIES)
    available = set(float(value) for value in market.curve.tenors)
    tenor_passed = required == available
    age = (current_date - market.as_of).days
    stale_passed = 0 <= age <= max_age_days

    positions = balance_sheet.assets.positions + balance_sheet.liabilities.positions
    total_pv01 = sum(pv01(position, market.curve) for position in positions)
    ladder_pv01 = sum(
        sum(portfolio.pv01_ladder(market.curve).values())
        for portfolio in (balance_sheet.assets, balance_sheet.liabilities)
    )
    relative_error = abs(ladder_pv01 - total_pv01) / max(abs(total_pv01), 1.0)
    reconciliation_passed = relative_error <= pv01_tolerance

    results = [
        ValidationResult("Required tenors", tenor_passed, f"Found {sorted(available)}"),
        ValidationResult("Curve freshness", stale_passed, f"Observation is {age} days old"),
        ValidationResult(
            "PV01 reconciliation",
            reconciliation_passed,
            f"Relative error {relative_error:.4%}",
        ),
    ]
    failures = [result for result in results if not result.passed]
    if failures:
        details = "; ".join(f"{item.name}: {item.detail}" for item in failures)
        raise ValidationError(details)
    return results


def validate_portfolio_reconciliation(
    portfolio: Portfolio,
    market: MarketSnapshot,
    tolerance: float = 0.001,
) -> ValidationResult:
    total = sum(pv01(position, market.curve) for position in portfolio.positions)
    ladder = sum(portfolio.pv01_ladder(market.curve).values())
    error = abs(ladder - total) / max(abs(total), 1.0)
    return ValidationResult("PV01 reconciliation", error <= tolerance, f"Relative error {error:.4%}")
