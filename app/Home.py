"""
Home page --- The Case for Nuclear

> 3 KPI cards
    a) X tonnes CO2 avoided
    b) $Y consumer savings
    c) Z% of Ontario's grid

> Chart 1: [Annual] Actual vs counterfactual price over time
    - annual average line chart
    - x=time (yearly), y=price ($/MWh)
    - one line (actual price) another line (counterfactual price)
    - gap between them is the visual story (how much we saved)
    - gap = Nuclear suppressed prices by avg $X/MWh
    data==> actual price (staging_marts/fact_counterfactual.actual_price), counterfactual price (staging_marts/fact_counterfactual.counterfactual_price), year

> Chart 2: Annual CO2 avoided bar chart (categorical)
    - x=years (11 bars, 2015...2025), y=CO2 avoided (tonnes)

> Chart 3: Cumulative cost savings over time
    - filled area chart, starting at 0 in 2015 and climbing...
    - x=time (count by years), y=$ saved
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Configure layout and header
st.set_page_config(page_title="Grid Without Nuclear", layout="wide", page_icon="⚛️")
st.title("📊 Grid Without Nuclear")
st.markdown("If Ontario's nuclear fleet went offline — what would electricity cost, and how much CO2 would be emitted to replace it?")

COLORS = {
    'nuclear':  '#2196F3',
    'gas':      '#FF9800',
    'hydro':    '#4CAF50',
    'wind':     '#00BCD4',
    'solar':    '#FFEB3B',
    'biofuel':  '#795548',
    'actual':   '#2196F3',
    'counter':  '#FF5722',
}

# Sidebar
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

# row of metrics (KPI Cards)
col1, col2, col3 = st.columns(3)
col1.metric("🌱 CO₂ Avoided by Nuclear", "70M tonnes", border=True)
col2.metric("💰 Consumer Savings", "$50.6B", border=True)
col3.metric("⚡️ Avg Nuclear Share", "56.4%", border=True)

st.divider()


@st.cache_data # cache the data
def load_data():
    df = pd.read_parquet("data/fact_counterfactual.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    return df[df["year"].between(2015, 2024)] # filter rows where Year is between 2015-2025

df_full = load_data()

# group by Year then perform Named Aggregations on each Year
annual = df_full.groupby("year").agg(
    # Chart 1 data - avg actual & counterfactual price (line)
    actual_price=("actual_price", "mean"),
    counterfactual_price=("counterfactual_price", "mean"),
    # Chart 2 data - total co2 avoided that year
    co2_avoided=("co2_avoided_tonnes", "sum"),
    # Chart 3 data - total saved costs ~= actual_price - counterfactual_price
    cost_delta=("cost_delta_dollars", "sum")
).reset_index()

# col_left (Chart 1), col_right (Chart 2)
col_left, col_right = st.columns(2, border=True)

with col_left:
    st.subheader("Actual vs Counterfactual Price")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annual["year"], y=annual["actual_price"],
        name="Actual price", line=dict(color=COLORS["actual"], width=2.5),
        mode="lines+markers"
    ))
    fig.add_trace(go.Scatter(
        x=annual["year"], y=annual["counterfactual_price"],
        name="No-nuclear price", line=dict(color=COLORS["counter"], width=2.5, dash="dash"),
        mode="lines+markers"
    ))
    fig.update_layout(
        yaxis_title="$/MWh",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Annual CO₂ Avoided (Million Tonnes)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=annual["year"],
        y=annual["co2_avoided"] / 1_000_000,
        marker_color=COLORS["nuclear"],
        text=(annual["co2_avoided"] / 1_000_000).round(1),
        textposition="outside"
    ))
    fig2.update_layout(
        yaxis_title="Million tonnes CO₂",
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False
    )
    fig2.add_annotation(
        x=2022, y=annual.loc[annual["year"]==2022, "co2_avoided"].values[0] / 1_000_000 + 0.5,
        text="Darlington refurbishment<br>reduces nuclear output",
        showarrow=True, arrowhead=2, ax=60, ay=-40,
        font=dict(size=11)
    )
    st.plotly_chart(fig2, use_container_width=True)

# Cumulative savings
st.subheader("Cumulative Consumer Savings Without Nuclear")
annual["cumulative_savings"] = annual["cost_delta"].cumsum() / 1_000_000_000

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=annual["year"],
    y=annual["cumulative_savings"],
    fill="tozeroy",
    line=dict(color=COLORS["nuclear"], width=2.5),
    name="Cumulative savings"
))
for milestone in [10, 25, 50]:
    fig3.add_hline(
        y=milestone,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"${milestone}B",
        annotation_position="right"
    )
fig3.update_layout(
    yaxis_title="Cumulative savings ($B)",
    xaxis_title="Year",
    margin=dict(l=0, r=0, t=30, b=0),
    showlegend=False,
    hovermode="x unified"
)
st.plotly_chart(fig3, use_container_width=True)