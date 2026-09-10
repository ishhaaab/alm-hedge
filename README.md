# ALM Hedge Lab

ALM Hedge Lab values a small life-insurer balance sheet from its cashflows. The app shows where asset and liability rate risk diverge, revalues the book under curve shocks, and checks whether the asset portfolio offsets the liability.

This is a teaching model. The positions are fictional and the capital number is an illustrative proxy, not a Bermuda Monetary Authority BSCR calculation.

## Run it

Use Python 3.11 or later.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens with a bundled curve dated 2 January 2025, so it works without a network connection. Turn on "Use latest FRED curve" in the sidebar to download the latest complete observation.

Run the tests with:

```bash
python -m pytest -q
```

## What the model does

Every bond, payer swap, and annuity is a series of dated cashflows. The curve uses continuously compounded zero rates and linear interpolation between quoted tenors. A node bump changes one quoted tenor; interpolation spreads its effect over cashflows between the adjacent nodes.

The ALM monitor reports:

- Asset value, liability value, surplus, and duration gap
- Surplus PV01 at 2Y, 5Y, 10Y, 20Y, and 30Y
- Full revaluation under parallel shocks, twists, and a 2008 replay
- A Treasury trade that moves 10Y+ PV01 to the $5,000 limit

The hedge review reports dollar offset, regression fit, key-rate coverage, and scenario P&L attribution. Validation stops a live run when the curve is stale, incomplete, or fails the PV01 reconciliation check.

## Data

The live curve comes from the Federal Reserve Bank of St. Louis FRED CSV service:

| Tenor | FRED series |
| --- | --- |
| 2Y | DGS2 |
| 5Y | DGS5 |
| 10Y | DGS10 |
| 20Y | DGS20 |
| 30Y | DGS30 |

FRED publishes Treasury constant-maturity par yields. This project treats them as zero rates to keep the pricing code inspectable. A production model would bootstrap discount factors from instrument prices.

The 2008 replay uses the change between 2 January and 31 December 2008, rounded to whole basis points at each available tenor. It is a historical curve shift applied to the current book, not a recreation of 2008 spreads or liquidity conditions.

## Limits

- Swaps use the value of a par floater at a coupon reset date. The model does not project floating fixings between reset dates.
- Cashflows are deterministic. There are no lapses, mortality changes, optionality, or credit spreads.
- The optimizer chooses one 20Y or 30Y Treasury and scales its face value. It does not include transaction costs or lot sizes.
- The capital proxy charges 15% of the loss implied by a 100 bp move against each residual key-rate PV01.

On the bundled book, the assets cover the liability's total rate exposure closely, but the 20Y bucket remains short. Curve twists expose that mismatch even though the dollar-offset and regression tests pass. That is the useful result: a hedge can pass aggregate tests and still leave a concentrated tenor risk.
