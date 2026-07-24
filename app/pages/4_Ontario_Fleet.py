import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_data

st.set_page_config(page_title="Ontario's Nuclear Fleet", page_icon="🏭", layout="wide")

COLORS = {
    'nuclear': '#2196F3',
    'gas': '#FF9800',
    'hydro': '#4CAF50',
    'wind': '#00BCD4',
    'solar': '#FFEB3B',
    'biofuel': '#795548',
}
NUCLEAR_NAMEPLATE_MW = 13500

REFURBISHMENTS = [
    {"unit": "Darlington Unit 2", "start": 2016, "end": 2020},
    {"unit": "Darlington Unit 3", "start": 2020, "end": 2023},
    {"unit": "Darlington Unit 1", "start": 2022, "end": 2025},
    {"unit": "Darlington Unit 4", "start": 2024, "end": 2026},
]

df = load_data()

st.title("Ontario's Nuclear Fleet")
st.markdown("10 years of nuclear generation data — operational trends, capacity factors, and refurbishment impacts.")
st.divider()

# Stacked area chart
st.subheader("Ontario Generation Mix (2015–2024)")

annual_monthly = df.groupby(["year", "month"]).agg(
    nuclear=("nuclear_mw", "mean"),
    hydro=("hydro_mw", "mean"),
    wind=("wind_mw", "mean"),
    solar=("solar_mw", "mean"),
    gas=("gas_mw", "mean"),
    biofuel=("biofuel_mw", "mean")
).reset_index()
annual_monthly["period"] = annual_monthly["year"] + (annual_monthly["month"] - 1) / 12

fig = go.Figure()
for fuel in ["biofuel", "solar", "wind", "gas", "hydro", "nuclear"]:
    fig.add_trace(go.Scatter(
        x=annual_monthly["period"],
        y=annual_monthly[fuel],
        name=fuel.capitalize(),
        stackgroup="one",
        line=dict(color=COLORS[fuel], width=0.5),
        fillcolor=COLORS[fuel],
        hovertemplate=f"{fuel.capitalize()}: %{{y:,.0f}} MW<extra></extra>"
    ))

for r in REFURBISHMENTS:
    fig.add_vrect(
        x0=r["start"], x1=min(r["end"], 2024),
        fillcolor="rgba(255,255,255,0.08)",
        line_width=1, line_color="rgba(255,255,255,0.3)",
        annotation_text=r["unit"].replace("Darlington ", ""),
        annotation_position="top left",
        annotation_font_size=10
    )

fig.update_layout(
    yaxis_title="Average MW",
    xaxis_title="Year",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(l=0, r=0, t=30, b=0),
    hovermode="x unified",
    height=400
)
st.plotly_chart(fig, width='stretch')

st.divider()

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Nuclear Capacity Factor by Year")
    annual = df.groupby("year").agg(
        nuclear=("nuclear_mw", "mean")
    ).reset_index()
    annual["capacity_factor"] = (annual["nuclear"] / NUCLEAR_NAMEPLATE_MW * 100).round(1)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=annual["year"],
        y=annual["capacity_factor"],
        marker_color=COLORS["nuclear"],
        text=annual["capacity_factor"].astype(str) + "%",
        textposition="outside",
        customdata=annual["nuclear"].round(0).astype(int),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Capacity factor: %{y:.1f}%<br>"
            "Avg output: %{customdata:,} MW"
            "<extra></extra>"
        )
    ))
    fig2.add_hline(
        y=85, line_dash="dot", line_color="green",
        annotation_text="Industry benchmark (85%)",
        annotation_position="right"
    )
    fig2.update_layout(
        yaxis_title="Capacity factor (%)",
        yaxis_range=[0, 100],
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False
    )
    st.plotly_chart(fig2, width='stretch')

with col_r:
    st.subheader("Seasonal Nuclear Output Pattern")
    monthly = df.groupby("month").agg(
        nuclear=("nuclear_mw", "mean"),
        nuclear_min=("nuclear_mw", lambda x: x.quantile(0.1)),
        nuclear_max=("nuclear_mw", lambda x: x.quantile(0.9))
    ).reset_index()

    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=months + months[::-1],
        y=monthly["nuclear_max"].tolist() + monthly["nuclear_min"].tolist()[::-1],
        fill="toself",
        fillcolor="rgba(33,150,243,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="10th–90th percentile",
        hoverinfo="skip"
    ))
    # Average line — show all three values on hover
    fig3.add_trace(go.Scatter(
        x=months,
        y=monthly["nuclear"],
        line=dict(color=COLORS["nuclear"], width=2.5),
        name="Monthly Average",
        mode="lines+markers",
        customdata=list(zip(
            monthly["nuclear_min"].round(0).astype(int),
            monthly["nuclear_max"].round(0).astype(int)
        )),
        hovertemplate=(
            "Avg: %{y:,.0f} MW<br>"
            "10th pct: %{customdata[0]:,} MW<br>"
            "90th pct: %{customdata[1]:,} MW"
            "<extra></extra>"
        )
    ))
    fig3.update_layout(
        yaxis_title="Average MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified"
    )
    st.plotly_chart(fig3, width='stretch')

# Refurbishment timeline
st.divider()
st.subheader("Darlington Refurbishment Timeline")

fig4 = go.Figure()
for i, r in enumerate(REFURBISHMENTS):
    fig4.add_trace(go.Bar(
        x=[min(r["end"], 2025) - r["start"]],
        y=[r["unit"]],
        base=[r["start"]],
        orientation="h",
        marker_color=COLORS["nuclear"],
        opacity=0.7 + i * 0.075,
        name=r["unit"],
        text=f"{r['start']}–{r['end']}",
        textposition="inside"
    ))

fig4.update_layout(
    xaxis=dict(range=[2014, 2027], title="Year"),
    barmode="overlay",
    showlegend=False,
    margin=dict(l=0, r=0, t=30, b=0),
    height=220
)
st.plotly_chart(fig4, width='stretch')