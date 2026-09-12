from __future__ import annotations

from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from alm_hedge_lab.hedge import capital_proxy, effectiveness_tests, pnl_attribution
from alm_hedge_lab.market_data import fetch_fred_curve
from alm_hedge_lab.reporting import assess_limits
from alm_hedge_lab.repositioning import TradeCandidate, recommend_long_end_trade
from alm_hedge_lab.sample import bundled_history, bundled_market, sample_balance_sheet
from alm_hedge_lab.scenarios import scenario_results, standard_scenarios
from alm_hedge_lab.validation import ValidationError, validate_market


st.set_page_config(page_title="ALM Hedge Lab", page_icon=None, layout="wide")
st.markdown(
    """
    <style>
    :root {
        --ink: #17231d;
        --muted: #667069;
        --paper: #f4f1e9;
        --surface: #fbfaf6;
        --line: #d8d3c6;
        --accent: #9f3f2c;
        --positive: #315b47;
    }

    html { scroll-behavior: smooth; }
    [data-testid="stAppViewContainer"] {
        background: var(--paper);
        color: var(--ink);
    }
    [data-testid="stHeader"] { background: color-mix(in srgb, var(--paper) 88%, transparent); }
    [data-testid="stMainBlockContainer"] {
        max-width: 92rem;
        padding: 3.5rem 3.25rem 5rem;
    }

    h1, h2, h3, p, label { color: var(--ink); }
    h1 {
        font-size: clamp(2.4rem, 4vw, 4.25rem) !important;
        line-height: .98 !important;
        letter-spacing: -.055em !important;
        margin: .4rem 0 1rem !important;
    }
    h2, h3 {
        letter-spacing: -.035em !important;
        line-height: 1.08 !important;
    }
    [data-testid="stCaptionContainer"] { color: var(--muted); }
    .eyebrow {
        margin: 0;
        font: 700 .72rem/1.2 ui-monospace, SFMono-Regular, Consolas, monospace;
        letter-spacing: .12em;
        text-transform: uppercase;
        color: var(--accent);
    }

    [data-testid="stSidebar"] {
        background: #20261f;
        border-right: 1px solid #30382f;
    }
    [data-testid="stSidebarContent"] { padding: 2rem 1.35rem; }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #eef0ea;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] {
        border: 1px solid #3c493f;
        border-radius: .45rem;
        background: #293129;
        padding: .8rem .9rem;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] p {
        color: #dfe5dd;
        font-size: .9rem;
        line-height: 1.55;
    }
    [data-testid="stSidebar"] [data-baseweb="notification"] { box-shadow: none; }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 1.75rem;
        border-bottom: 1px solid var(--line);
    }
    [data-testid="stTabs"] button[role="tab"] {
        color: var(--muted);
        padding: .75rem 0 .8rem;
        transition: color 160ms ease;
    }
    [data-testid="stTabs"] button[role="tab"]:hover { color: var(--ink); }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: var(--accent);
        font-weight: 650;
    }

    [data-testid="stMetric"] {
        min-height: 8.5rem;
        margin: 1.25rem 0 2.25rem;
        padding: 1.15rem 1.25rem 1.3rem;
        background: var(--surface);
        border: 1px solid var(--line);
        border-top: 3px solid var(--ink);
        border-radius: 0 0 .5rem .5rem;
    }
    [data-testid="stMetricLabel"] p {
        color: var(--muted) !important;
        font-size: .78rem !important;
        font-weight: 700 !important;
        letter-spacing: .07em;
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
        font-size: clamp(1.65rem, 2.3vw, 2.5rem) !important;
        font-variant-numeric: tabular-nums;
        letter-spacing: -.04em;
    }
    [data-testid="stMetricDelta"] { font-variant-numeric: tabular-nums; }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: .5rem;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] * { font-variant-numeric: tabular-nums; }
    [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], [data-testid="stPyplot"] {
        border: 1px solid var(--line);
        border-radius: .5rem;
        background: var(--surface);
        padding: .5rem;
    }
    [data-testid="stAlert"] {
        border-radius: .45rem;
        box-shadow: none;
    }
    button:focus-visible, [tabindex="0"]:focus-visible {
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px;
    }

    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] { padding: 2.5rem 1.25rem 4rem; }
        [data-testid="stMetric"] { margin: .6rem 0; min-height: 7.25rem; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 1rem; overflow-x: auto; }
    }
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
    figure.patch.set_facecolor("#fbfaf6")
    axis.set_facecolor("#fbfaf6")
    colors = ["#9f3f2c" if value < 0 else "#315b47" for value in ladder.values()]
    axis.bar([f"{tenor:g}Y" for tenor in ladder], ladder.values(), color=colors, width=0.62)
    axis.axhline(0, color="#17231d", linewidth=0.8)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.spines["bottom"].set_color("#8a908b")
    axis.tick_params(axis="both", colors="#39443e", length=0, labelsize=9)
    axis.grid(axis="y", color="#ded9cd", linewidth=0.7, alpha=0.8)
    axis.set_axisbelow(True)
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

st.sidebar.markdown("**Trade assumptions**")
st.sidebar.caption("Inputs you set. The model does not look these up.")
trade_limit = st.sidebar.number_input(
    "Long-end PV01 limit, $",
    min_value=100.0,
    max_value=100_000.0,
    value=5_000.0,
    step=500.0,
)
candidates: list[TradeCandidate] = []
for name, maturity, coupon in (
    ("20Y Treasury", 20.0, 0.045),
    ("30Y Treasury", 30.0, 0.0475),
):
    cost_bp = st.sidebar.number_input(
        f"{name} cost, bp",
        min_value=0.0,
        max_value=50.0,
        value=5.0,
        step=0.5,
    )
    lot_size = st.sidebar.number_input(
        f"{name} lot size, $",
        min_value=1_000.0,
        max_value=10_000_000.0,
        value=100_000.0,
        step=10_000.0,
    )
    candidates.append(
        TradeCandidate(name, maturity, coupon, transaction_cost_bp=cost_bp, lot_size=lot_size)
    )
candidates = tuple(candidates)

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

    recommendation = recommend_long_end_trade(balance_sheet, curve, trade_limit, candidates)
    st.subheader("Repositioning ticket")
    assumption_frame = pd.DataFrame(
        {
            "instrument": candidate.name,
            "cost, bp": candidate.transaction_cost_bp,
            "lot size, $": candidate.lot_size,
        }
        for candidate in candidates
    )
    st.dataframe(
        assumption_frame.style.format({"lot size, $": "${:,.0f}"}),
        hide_index=True,
        width="stretch",
    )
    st.caption("Assumed trading costs and lot sizes, set in the sidebar.")
    if recommendation:
        action = "Buy" if recommendation.face_value > 0 else "Sell"
        st.write(
            f"{action} **${abs(recommendation.face_value) / 1_000_000:,.2f}m** face of "
            f"{recommendation.instrument}. Estimated 10Y+ PV01 moves from "
            f"${recommendation.before_pv01:,.0f} to ${recommendation.after_pv01:,.0f}. "
            f"Turnover ${recommendation.turnover:,.0f}, est. cost ${recommendation.transaction_cost:,.0f}."
        )
    else:
        st.success(f"Long-end PV01 is inside the ${trade_limit:,.0f} limit. No trade required.")

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
