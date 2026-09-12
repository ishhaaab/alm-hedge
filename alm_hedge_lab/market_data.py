from __future__ import annotations

import csv
import io
from datetime import date, datetime
from urllib.request import urlopen

from .curves import QUOTED_TENORS, bootstrap_zero_curve
from .sample import MarketSnapshot


FRED_SERIES = {
    int(tenor): series
    for tenor, series in zip(QUOTED_TENORS, ("DGS2", "DGS5", "DGS10", "DGS20", "DGS30"))
}


def fetch_fred_curve(timeout: float = 10) -> MarketSnapshot:
    series = ",".join(FRED_SERIES.values())
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    with urlopen(url, timeout=timeout) as response:
        rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))
    complete = [
        row
        for row in rows
        if all(row.get(series_id) not in (None, "", ".") for series_id in FRED_SERIES.values())
    ]
    if not complete:
        raise ValueError("FRED series have no common complete observation")
    latest = complete[-1]
    as_of = datetime.strptime(latest["observation_date"], "%Y-%m-%d").date()
    par_yields = [float(latest[series_id]) / 100 for series_id in FRED_SERIES.values()]
    return MarketSnapshot(as_of, bootstrap_zero_curve(tuple(FRED_SERIES), par_yields), "FRED")
