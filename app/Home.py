"""
Home page --- The Case for Nuclear

> 3 KPI cards
    a) X tonnes CO2 avoided
    b) $Y consumer savings
    c) Z% of Ontario's grid
> Chart 1: Actual vs Counterfactual Price over time
> Chart 2: Annual CO2 Avoided bar chart
> Chart 3: Cumulative Cost Savings over time
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Configure layout and header
st.set_page_config(page_title="Grid Without Nuclear", layout="wide", page_icon="⚛️", initial_sidebar_state="expanded")

COLORS = {
    'nuclear':  '#2196F3',
    'gas':      '#FF9800',
    'hydro':    '#4CAF50',
    'wind':     '#00BCD4',
    'solar':    '#FFEB3B',
    'biofuel':  '#795548',
    'actual':   '#2196F3',
    'counter':  '#FF5722',
    'band':     'rgba(255,87,34,0.12)',
}

# Bank of Canada CPI deflators to 2024 CAD
CPI_DEFLATORS = {
    2015: 1.24, 2016: 1.22, 2017: 1.20, 2018: 1.17,
    2019: 1.14, 2020: 1.13, 2021: 1.08, 2022: 1.02,
    2023: 1.01, 2024: 1.00
}

# Gas marginal cost scenarios
GAS_BASE  = 95
GAS_LOW   = 70
GAS_HIGH  = 120

# CO2 emission factors (gCO2/kWh)
CO2_NUCLEAR   = 0.012
CO2_GAS_BASE  = 0.490
CO2_GAS_LOW   = 0.410
CO2_GAS_HIGH  = 0.650


@st.cache_data # cache the data
def load_data():
    df = pd.read_parquet("data/fact_counterfactual.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    return df[df["year"].between(2015, 2024)] # filter rows where Year is between 2015-2025


@st.cache_data
def build_monthly(_df):
    monthly = _df.groupby(["year", "month"]).agg(
        actual_price      = ("actual_price",  "mean"),
        gas_fill_mw       = ("gas_fill_mw",   "mean"),
        ontario_demand_mw = ("ontario_demand_mw", "mean"),
        nuclear_mw        = ("nuclear_mw",    "mean"),
        co2_avoided_base  = ("co2_avoided_tonnes", "sum"),
        cost_delta        = ("cost_delta_dollars",  "sum"),
    ).reset_index()

    monthly["period"] = pd.to_datetime(
        monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2) + "-01"
    )

    gas_share = monthly["gas_fill_mw"] / monthly["ontario_demand_mw"].replace(0, float("nan"))

    monthly["cf_price_base"] = monthly["actual_price"] + gas_share * (GAS_BASE  - monthly["actual_price"])
    monthly["cf_price_low"]  = monthly["actual_price"] + gas_share * (GAS_LOW   - monthly["actual_price"])
    monthly["cf_price_high"] = monthly["actual_price"] + gas_share * (GAS_HIGH  - monthly["actual_price"])

    monthly["co2_low"]  = (monthly["gas_fill_mw"] * 1000 * CO2_GAS_LOW  - monthly["nuclear_mw"] * 1000 * CO2_NUCLEAR) / 1000
    monthly["co2_high"] = (monthly["gas_fill_mw"] * 1000 * CO2_GAS_HIGH - monthly["nuclear_mw"] * 1000 * CO2_NUCLEAR) / 1000

    return monthly


@st.cache_data
def build_annual(_df):
    annual = _df.groupby("year").agg(
        actual_price      = ("actual_price",        "mean"),
        gas_fill_mw       = ("gas_fill_mw",         "mean"),
        ontario_demand_mw = ("ontario_demand_mw",   "mean"),
        nuclear_mw        = ("nuclear_mw",           "mean"),
        co2_base          = ("co2_avoided_tonnes",   "sum"),
        cost_delta        = ("cost_delta_dollars",   "sum"),
    ).reset_index()

    gas_share = annual["gas_fill_mw"] / annual["ontario_demand_mw"].replace(0, float("nan"))
    annual["co2_low"]  = (annual["gas_fill_mw"] * 1000 * CO2_GAS_LOW  - annual["nuclear_mw"] * 1000 * CO2_NUCLEAR) / 1000
    annual["co2_high"] = (annual["gas_fill_mw"] * 1000 * CO2_GAS_HIGH - annual["nuclear_mw"] * 1000 * CO2_NUCLEAR) / 1000

    annual["cpi"]            = annual["year"].map(CPI_DEFLATORS)
    annual["cost_real"]      = annual["cost_delta"] * annual["cpi"]
    annual["cost_cumulative_nominal"] = annual["cost_delta"].cumsum() / 1e9
    annual["cost_cumulative_real"]    = annual["cost_real"].cumsum()  / 1e9

    return annual


df = load_data()
monthly = build_monthly(df)
annual = build_annual(df)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚛️ Grid Without Nuclear")
    st.markdown(
        "Quantifying nuclear power's economic and "
        "environmental value to Ontario's electricity "
        "grid (2015-2025)"
    )
    st.divider()
    st.markdown("**Data:** [IESO Public Reports](https://www.ieso.ca/power-data)")
    st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-%23121011.svg?logo=github&logoColor=white)](https://github.com/devarshi-ap/GridWithoutNuclear)")
    st.divider()
    inflation_adj = st.toggle("Inflation-adjust costs (real 2024 CAD)", value=False)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("📊 Grid Without Nuclear")
st.markdown("If Ontario's nuclear fleet went offline — what would electricity cost, and how much CO2 would be emitted to replace it?")
st.divider()

# ── KPI Cards ────────────────────────────────────────────────────────────────

k1, k2, k3 = st.columns(3, border=True)

total_co2_base = annual["co2_base"].sum() / 1e6
total_co2_low  = annual["co2_low"].sum()  / 1e6
total_co2_high = annual["co2_high"].sum() / 1e6

cost_col = "cost_real" if inflation_adj else "cost_delta"
total_savings = annual[cost_col].sum() / 1e9
cost_label    = "Real 2024 CAD" if inflation_adj else "Nominal CAD"

nuclear_share = (df["nuclear_mw"] / df["total_mw"].replace(0, float("nan"))).mean() * 100

with k1:
    st.metric(
        label="🌱 CO₂ Avoided by Nuclear",
        value=f"{total_co2_base:.1f}M tonnes",
        help=f"Range: {total_co2_low:.1f}M - {total_co2_high:.1f}M tonnes depending on gas emission factor (410-650 gCO₂/kWh)"
    )

with k2:
    st.metric(
        label=f"💰 Consumer Savings ({cost_label})",
        value=f"${total_savings:.1f}B",
        help="Estimated cost premium Ontario consumers would have paid without nuclear. Toggle inflation adjustment in the sidebar."
    )

with k3:
    st.metric(
        label="⚡ Avg Nuclear Share of Generation",
        value=f"{nuclear_share:.1f}%",
        help="Average share of Ontario's total metered generation 2015-2024"
    )

st.divider()



col_left, col_right = st.columns(2, border=True)
# ── Chart 1a — Monthly price with uncertainty band ───────────────────────────
with col_left:
    st.subheader("Actual vs Counterfactual Price")
    st.caption("Monthly averages · Shaded band = $70-$120/MWh gas marginal cost range")
    fig1 = go.Figure()
    # Actual Price (HOEP)
    fig1.add_trace(go.Scatter(
        x=monthly["period"], y=monthly["actual_price"],
        name="Actual price (HOEP)",
        line=dict(color=COLORS["actual"], width=2),
        mode="lines"
    ))
    # Counterfactual Price
    fig1.add_trace(go.Scatter(
        x=monthly["period"], y=monthly["cf_price_base"],
        name="No-nuclear price (base $95/MWh gas)",
        line=dict(color=COLORS["counter"], width=1.5, dash="dash"),
        mode="lines"
    ))
    # Uncertainty Band
    fig1.add_trace(go.Scatter(
        x=monthly["period"].tolist() + monthly["period"].tolist()[::-1],
        y=monthly["cf_price_high"].tolist() + monthly["cf_price_low"].tolist()[::-1],
        fill="toself",
        fillcolor=COLORS["band"],
        line=dict(color="rgba(0,0,0,0)"),
        name="No-nuclear range ($70-$120/MWh gas)",
        hoverinfo="skip"
    ))
    fig1.update_layout(
        yaxis_title="$/MWh",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
        height=380
    )
    st.plotly_chart(fig1, width='stretch')

st.divider()


# ── Chart 1b — Annual CO2 avoided with uncertainty ───────────────────────────
with col_right:
    st.subheader("Annual CO₂ Avoided (Million Tonnes)")
    st.caption("Error bars show range from gas emission factor uncertainty (410-650 gCO₂/kWh · IPCC AR6)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=annual["year"],
        y=annual["co2_base"] / 1e6,
        marker_color=COLORS["nuclear"],
        name="CO₂ avoided (base estimate)",
        error_y=dict(
            type="data",
            symmetric=False,
            array=(annual["co2_high"] - annual["co2_base"]).div(1e6).tolist(),
            arrayminus=(annual["co2_base"] - annual["co2_low"]).div(1e6).tolist(),
            color="rgba(33,150,243,0.5)",
            thickness=2,
            width=6
        ),
        text=(annual["co2_base"] / 1e6).round(1).astype(str) + "M",
        textposition="outside"
    ))
    fig2.update_layout(
        yaxis_title="Million tonnes CO₂",
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        height=380
    )
    st.plotly_chart(fig2, width='stretch')

st.divider()


# ── Chart 1c — Annual bars + cumulative savings ───────────────────────────────
cum_col  = "cost_cumulative_real"    if inflation_adj else "cost_cumulative_nominal"
ann_col  = "cost_real"               if inflation_adj else "cost_delta"
currency = "Real 2024 CAD"           if inflation_adj else "Nominal CAD"

st.subheader(f"Consumer Savings Without Nuclear ({currency})")
st.caption("Left axis: annual savings · Right axis: cumulative total · "
    + ("Inflation-adjusted using Bank of Canada CPI." if inflation_adj else "Nominal dollars — toggle inflation adjustment in sidebar for real values.")
)



fig3 = make_subplots(specs=[[{"secondary_y": True}]])

fig3.add_trace(go.Bar(
    x=annual["year"],
    y=annual[ann_col] / 1e9,
    name="Annual savings ($B)",
    marker_color=COLORS["nuclear"],
    opacity=0.7
), secondary_y=False)

fig3.add_trace(go.Scatter(
    x=annual["year"],
    y=annual[cum_col],
    name="Cumulative savings ($B)",
    line=dict(color=COLORS["counter"], width=2.5),
    mode="lines+markers"
), secondary_y=True)

fig3.update_yaxes(title_text="Annual savings ($B)", secondary_y=False)
fig3.update_yaxes(title_text="Cumulative savings ($B)", secondary_y=True)
fig3.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(l=0, r=0, t=40, b=0),
    hovermode="x unified",
    height=380,
    barmode="group"
)
st.plotly_chart(fig3, width='stretch')

st.caption(
    "⚠️ Economic value is likely understated — excludes grid stability, "
    "capacity market value, and energy security premium of nuclear baseload. "
    "Nominal figures overstate real purchasing power — use the inflation toggle for real 2024 CAD."
)

st.divider()

# ── Assumptions block ─────────────────────────────────────────────────────────
with st.expander("Model assumptions and methodology"):
    st.markdown("""
| Parameter | Value | Source |
|---|---|---|
| Gas marginal cost (base) | $95/MWh | NRCan published averages |
| Gas marginal cost (range) | $70-$120/MWh | Sensitivity analysis |
| Gas CO₂ factor (base) | 490 gCO₂/kWh | IPCC AR6 combined cycle median |
| Gas CO₂ factor (range) | 410-650 gCO₂/kWh | IPCC AR6 full range |
| Nuclear CO₂ factor | 12 gCO₂/kWh | IPCC AR6 lifecycle median |
| Ontario gas fleet ceiling | 10,500 MW | IESO Reliability Outlook 2024 |
| Hydro seasonal capacity | 95th percentile by month | Calculated from IESO data 2015-2025 |
| Inflation deflators | Bank of Canada CPI | Real 2024 CAD conversion |

Full methodology and derivations available in the
[project README](https://github.com/devarshi-ap/GridWithoutNuclear).
A detailed PDF walkthrough of the counterfactual model is coming soon.
    """)