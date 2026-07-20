import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Inside the Grid", layout="wide", page_icon="⚡️")

COLORS = {
    'nuclear':  '#2196F3',
    'gas':      '#FF9800',
    'hydro':    '#4CAF50',
    'wind':     '#00BCD4',
    'solar':    '#FFEB3B',
    'biofuel':  '#795548',
}
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

@st.cache_data
def load_data():
    df = pd.read_parquet("data/fact_counterfactual.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    return df[df["year"].between(2015, 2024)]

df = load_data()

st.title("Inside the Grid")
st.markdown("How Ontario's generation mix actually behaves — hour by hour, month by month.")
st.divider()

# Heatmap toggle
st.subheader("Generation Heatmap")
metric = st.radio(
    "Show:",
    ["Nuclear share %", "Gas share %", "Avg price ($/MWh)"],
    horizontal=True
)

heatmap_data = df.groupby(["month", "hour"]).agg(
    nuclear_share=("nuclear_mw", lambda x: (x / df.loc[x.index, "total_mw"]).mean() * 100),
    gas_share=("gas_mw", lambda x: (x / df.loc[x.index, "total_mw"]).mean() * 100),
    avg_price=("actual_price", "mean")
).reset_index()

if metric == "Nuclear share %":
    z_col, colorscale, title = "nuclear_share", "Blues", "Nuclear share of generation (%)"
elif metric == "Gas share %":
    z_col, colorscale, title = "gas_share", "Oranges", "Gas share of generation (%)"
else:
    z_col, colorscale, title = "avg_price", "RdYlGn_r", "Average electricity price ($/MWh)"

pivot = heatmap_data.pivot(index="month", columns="hour", values=z_col)

fig = go.Figure(go.Heatmap(
    z=pivot.values,
    x=[f"{h:02d}:00" for h in range(24)],
    y=MONTH_NAMES,
    colorscale=colorscale,
    colorbar=dict(title=title)
))
fig.update_layout(
    xaxis_title="Hour of day",
    yaxis_title="Month",
    margin=dict(l=0, r=0, t=30, b=0),
    height=400
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Average Generation Mix by Hour")
    hourly = df.groupby("hour").agg(
        nuclear=("nuclear_mw", "mean"),
        hydro=("hydro_mw", "mean"),
        wind=("wind_mw", "mean"),
        solar=("solar_mw", "mean"),
        gas=("gas_mw", "mean"),
        biofuel=("biofuel_mw", "mean")
    ).reset_index()

    fig2 = go.Figure()
    for fuel in ["nuclear", "hydro", "wind", "solar", "gas", "biofuel"]:
        fig2.add_trace(go.Scatter(
            x=hourly["hour"], y=hourly[fuel],
            name=fuel.capitalize(),
            stackgroup="one",
            line=dict(color=COLORS[fuel]),
            fillcolor=COLORS[fuel]
        ))
    fig2.update_layout(
        xaxis_title="Hour of day",
        yaxis_title="Average MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified"
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.subheader("Price Distribution by Hour of Day")
    hourly_price = df.groupby("hour").agg(
        q25=("actual_price", lambda x: x.quantile(0.25)),
        median=("actual_price", "median"),
        q75=("actual_price", lambda x: x.quantile(0.75)),
        mean=("actual_price", "mean")
    ).reset_index()

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=hourly_price["hour"].tolist() + hourly_price["hour"].tolist()[::-1],
        y=hourly_price["q75"].tolist() + hourly_price["q25"].tolist()[::-1],
        fill="toself",
        fillcolor="rgba(33,150,243,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="IQR (25th–75th pct)"
    ))
    fig3.add_trace(go.Scatter(
        x=hourly_price["hour"], y=hourly_price["median"],
        line=dict(color=COLORS["nuclear"], width=2),
        name="Median price"
    ))
    fig3.add_trace(go.Scatter(
        x=hourly_price["hour"], y=hourly_price["mean"],
        line=dict(color=COLORS["gas"], width=2, dash="dash"),
        name="Mean price"
    ))
    fig3.update_layout(
        xaxis_title="Hour of day",
        yaxis_title="$/MWh",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified"
    )
    st.plotly_chart(fig3, use_container_width=True)