# ALM Hedge Lab

ALM Hedge Lab prices a small life-insurer balance sheet from its cashflows. The app shows where asset and liability rate risk split apart, revalues the book under curve shocks, and checks whether the assets actually offset the liability.

This is a teaching model. The positions are fictional and the capital number is a rough proxy, not a Bermuda Monetary Authority BSCR calculation.

## Run it

Use Python 3.11 or later.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens with a bundled curve dated 2 January 2025, so it works with no network. Turn on "Use latest FRED curve" in the sidebar to pull the latest complete observation.

Run the tests with:

```bash
python -m pytest -q
```

## What the model does

Every bond, payer swap, and annuity is a series of dated cashflows. FRED publishes Treasury constant-maturity par yields, so the code bootstraps them into continuously compounded zero rates first, then interpolates linearly between quoted tenors. A node bump moves one quoted tenor, and interpolation spreads the effect over cashflows between the adjacent nodes. Rates outside the quoted range use the nearest node rate.

The ALM monitor reports:

- Asset value, liability value, surplus, and duration gap
- Surplus PV01 at 2Y, 5Y, 10Y, 20Y, and 30Y
- Full revaluation under parallel shocks, twists, and a 2008 replay
- A Treasury trade that pulls 10Y+ PV01 back inside the $5,000 limit

The trade picker prices each candidate 20Y/30Y Treasury at par, rounds up to a lot size, and takes the cheapest trade that lands inside the limit. Trading cost, lot size, and the PV01 limit are assumptions you set in the sidebar; the model does not look them up. It drops any trade whose cost exceeds the capital the repair releases (the 15% capital proxy times a 100 bp move). If no candidate gets there at a sane cost, it reports no trade instead of forcing one.

The hedge review runs 20 scenarios, not 5. Parallel moves, twists, a 2008 replay plus a half-size version, and single-node shocks at each tenor. It reports dollar offset, regression fit, key-rate coverage, and scenario P&L attribution. The regression refuses to run on fewer than 10 scenarios and flatlines at zero when the hedge legs do not move, instead of printing a fit on noise. Validation stops a live run when the curve is stale, incomplete, or fails the PV01 reconciliation check.

## Data

The live curve comes from the Federal Reserve Bank of St. Louis FRED CSV service:

| Tenor | FRED series |
| --- | --- |
| 2Y | DGS2 |
| 5Y | DGS5 |
| 10Y | DGS10 |
| 20Y | DGS20 |
| 30Y | DGS30 |

Each quoted yield is treated as the coupon on a semi-annual par bond at that maturity. The bootstrap solves shortest-first for the zero rate that reprices each par bond at 100, using the same linear interpolation the finished curve applies. The bundled 2 Jan 2025 par yields bootstrap to zero rates roughly 2 to 4.5 bp below par where the curve is rising, and about 6 bp above par at the 20Y hump where the par curve turns down. That is the compounding and interpolation correction the old par-as-zero shortcut skipped.

The 2008 replay uses the change between 2 January and 31 December 2008, rounded to whole basis points at each tenor. It is a historical curve shift applied to the current book, not a recreation of 2008 spreads or liquidity conditions.

## Limits

- Swaps are valued at a coupon reset date. The floating leg collapses to par at time zero and the model does not project fixings between resets.
- Cashflows are deterministic. No lapses, mortality changes, optionality, or credit spreads.
- The picker buys one Treasury tranche at par. Trading costs are assumptions you set, not market data; the model ignores how real bid/ask quotes move, funding, and repo.
- The capital proxy charges 15% of the loss implied by a 100 bp move against each residual key-rate PV01.

On the bundled book the hedge passes dollar offset and regression but fails key-rate coverage at about 73% against the 80% bar. The 20Y bucket stays short and twists expose it. I think that is the honest result here. A hedge can look fine in aggregate and still leave a concentrated tenor bet on.
