from __future__ import annotations

from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from alm_hedge_lab.hedge import capital_proxy, effectiveness_tests, pnl_attribution
from alm_hedge_lab.market_data import fetch_fred_curve
from alm_hedge_lab.reporting import assess_limits
from alm_hedge_lab.repositioning import recommend_long_end_trade
from alm_hedge_lab.sample import bundled_history, bundled_market, sample_balance_sheet
from alm_hedge_lab.scenarios import scenario_results, standard_scenarios
from alm_hedge_lab.validation import ValidationError, validate_market


st.set_page_config(page_title="ALM Hedge Lab", page_icon=None, layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background: #f3f0e8; color: #17231d; }
    [data-testid="stHeader"] { background: transparent; }
    h1, h2, h3 { font-family: Georgia, serif; color: #17231d; letter-spacing: -.025em; }
    [data-testid="stMetric"] { border-top: 2px solid #17231d; padding-top: .75rem; }
    .eyebrow { font: 700 .72rem/1.2 monospace; letter-spacing: .12em; text-transform: uppercase; color: #a2432f; }
    .source { color: #59645d; font-size: .86rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=21_600, show_spinner=False)
def load_live_market():
    return fetch_fred_curve()


def money(value: float) -> str:
    return f"${value / 1_000_000:,.2f}m"


def risk_chart(ladder: dict[float, float]):
    figure, axis = plt.subplots(figsize=(8, 3.4))
    figure.patch.set_facecolor("#f3f0e8")
    axis.set_facecolor("#f3f0e8")
    colors = ["#a2432f" if value < 0 else "#315b47" for value in ladder.values()]
    axis.bar([f"{tenor:g}Y" for tenor in ladder], ladder.values(), color=colors, width=0.62)
    axis.axhline(0, color="#17231d", linewidth=0.8)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    axis.set_ylabel("PV01, USD")
    figure.tight_layout()
    return figure


st.markdown('<p class="eyebrow">Investment risk / daily monitor</p>', unsafe_allow_html=True)
st.title("ALM Hedge Lab")
st.caption("A cashflow-based view of rate mismatch, hedge performance, and residual capital.")

use_live = st.sidebar.toggle("Use latest FRED curve", value=False)
if use_live:
    try:
        market = load_live_market()
    except Exception as error:
        st.sidebar.error(f"FRED download failed: {error}")
        market = bundled_market()
else:
    market = bundled_market()

balance_sheet = sample_balance_sheet()
validation_date = date.today() if market.source == "FRED" else market.as_of
try:
    checks = validate_market(market, balance_sheet, today=validation_date)
except ValidationError as error:
    st.error(f"Analytics stopped. {error}")
    st.stop()

curve = market.curve
scenarios = standard_scenarios(curve)
tests = effectiveness_tests(balance_sheet.assets, balance_sheet.liabilities, curve, scenarios)
breaches = assess_limits(balance_sheet, curve, tests)
values = balance_sheet.values(curve)

st.sidebar.markdown(f"**Curve date**  {market.as_of:%d %b %Y}")
st.sidebar.markdown(f"**Source**  {market.source}")
if market.source != "FRED":
    st.sidebar.info("Historical demo mode. Turn on the FRED curve for a current run.")
st.sidebar.markdown("**Validation**")
for check in checks:
    st.sidebar.success(f"{check.name}: {check.detail}")

overview, hedge_tab, erm = st.tabs(["ALM monitor", "Hedge review", "ERM summary"])

with overview:
    columns = st.columns(4)
    columns[0].metric("Assets", money(values["assets"]))
    columns[1].metric("Liabilities", money(values["liabilities"]))
    columns[2].metric("Surplus", money(values["surplus"]))
    columns[3].metric("Duration gap", f"{balance_sheet.duration_gap(curve):.2f} years")

    left, right = st.columns([1.25, 1])
    ladder = balance_sheet.surplus_pv01_ladder(curve)
    with left:
        st.subheader("Surplus PV01 by tenor")
        st.pyplot(risk_chart(ladder))
        st.caption("Positive bars gain value when that curve node falls by one basis point.")
    with right:
        st.subheader("Stress revaluation")
        scenario_frame = pd.DataFrame(scenario_results(balance_sheet, curve, scenarios))
        st.dataframe(
            scenario_frame.style.format({"surplus": "${:,.0f}", "change": "${:+,.0f}"}),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Duration gap history")
    history = pd.DataFrame(
        {
            "date": item.as_of,
            "duration gap": balance_sheet.duration_gap(item.curve),
        }
        for item in bundled_history()
    ).set_index("date")
    history["warning +"] = 0.5
    history["warning -"] = -0.5
    history["limit +"] = 1.0
    history["limit -"] = -1.0
    st.line_chart(
        history,
        color=["#315b47", "#c28a32", "#c28a32", "#a2432f", "#a2432f"],
    )
    st.caption("Month-end FRED curves through the bundled snapshot. Positions are held constant.")

    recommendation = recommend_long_end_trade(balance_sheet, curve)
    st.subheader("Repositioning ticket")
    if recommendation:
        action = "Buy" if recommendation.face_value > 0 else "Sell"
        st.write(
            f"{action} **${abs(recommendation.face_value) / 1_000_000:,.2f}m** face of "
            f"{recommendation.instrument}. Estimated 10Y+ PV01 moves from "
            f"${recommendation.before_pv01:,.0f} to ${recommendation.after_pv01:,.0f}."
        )
    else:
        st.success("Long-end PV01 is inside the $5,000 limit. No trade required.")

with hedge_tab:
    st.subheader("Effectiveness tests")
    test_columns = st.columns(len(tests))
    for column, test in zip(test_columns, tests):
        column.metric(test.name, f"{test.value:.1%}", "PASS" if test.passed else "FAIL")
        column.caption(test.threshold)

    selected = st.selectbox("Attribution scenario", scenarios, format_func=lambda item: item.name)
    attribution = pnl_attribution(balance_sheet.assets, balance_sheet.liabilities, curve, selected)
    display_attribution = {key: value for key, value in attribution.items() if key != "pnl after capital"}
    st.subheader("P&L attribution")
    st.bar_chart(pd.Series(display_attribution), color="#315b47", horizontal=True)
    st.caption(
        f"Economic P&L after the illustrative capital proxy: {money(attribution['pnl after capital'])}. "
        "The proxy is not a BMA BSCR calculation."
    )

with erm:
    st.subheader("Limit and control summary")
    summary_columns = st.columns(3)
    summary_columns[0].metric("Open items", len(breaches))
    summary_columns[1].metric("Capital proxy", money(capital_proxy(balance_sheet.assets, balance_sheet.liabilities, curve)))
    worst = min(scenario_results(balance_sheet, curve, scenarios), key=lambda row: row["change"])
    summary_columns[2].metric("Worst stress", money(float(worst["change"])), str(worst["scenario"]))

    if breaches:
        breach_frame = pd.DataFrame(
            {
                "as of": market.as_of,
                "measure": item.measure,
                "status": item.status,
                "observed": item.observed,
                "limit": item.limit,
                "scenario": item.scenario,
            }
            for item in breaches
        )
        st.dataframe(breach_frame, hide_index=True, width="stretch")
        st.download_button(
            "Download breach log",
            breach_frame.to_csv(index=False),
            file_name=f"breach-log-{market.as_of.isoformat()}.csv",
            mime="text/csv",
        )
    else:
        st.success("No warnings, limits, or hedge tests are open.")

    st.subheader("Curve used in this run")
    curve_frame = pd.DataFrame({"tenor": curve.tenors, "zero rate": curve.rates})
    st.dataframe(curve_frame.style.format({"tenor": "{:.0f}Y", "zero rate": "{:.2%}"}), hide_index=True)
