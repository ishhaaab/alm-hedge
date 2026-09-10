from __future__ import annotations

import csv
import io
from datetime import date, datetime
from urllib.request import urlopen

from .curves import ZeroCurve
from .sample import MarketSnapshot


FRED_SERIES = {2: "DGS2", 5: "DGS5", 10: "DGS10", 20: "DGS20", 30: "DGS30"}


def fetch_fred_curve(timeout: float = 10) -> MarketSnapshot:
    observations: dict[int, dict[date, float]] = {}
    for tenor, series in FRED_SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        with urlopen(url, timeout=timeout) as response:
            text = response.read().decode("utf-8")
        rows = csv.DictReader(io.StringIO(text))
        observations[tenor] = {
            datetime.strptime(row["observation_date"], "%Y-%m-%d").date(): float(row[series])
            for row in rows
            if row[series] not in ("", ".")
        }

    common_dates = set.intersection(*(set(values) for values in observations.values()))
    if not common_dates:
        raise ValueError("FRED series have no common complete observation")
    as_of = max(common_dates)
    rates = [observations[tenor][as_of] / 100 for tenor in FRED_SERIES]
    return MarketSnapshot(as_of, ZeroCurve(list(FRED_SERIES), rates), "FRED")
