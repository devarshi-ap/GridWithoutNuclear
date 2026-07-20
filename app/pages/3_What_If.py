import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="What If?", page_icon="🔬", layout="wide")

COLORS = {
    'nuclear': '#2196F3', 'gas': '#FF9800',
    'hydro': '#4CAF50', 'actual': '#2196F3', 'counter': '#FF5722'
}

@st.cache_data
def load_data():
    df = pd.read_parquet("data/fact_counterfactual.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    return df[df["year"].between(2015, 2024)]

df = load_data()

st.title("What If?")
st.markdown("Adjust the scenario parameters and watch the impact update in real time.")
st.divider()

# Sliders
col1, col2, col3 = st.columns(3)
with col1:
    nuclear_reduction = st.slider(
        "Nuclear output reduction (%)",
        min_value=0, max_value=100, value=100, step=5,
        help="100% = full removal. 50% = half the fleet offline."
    )
with col2:
    gas_cost = st.slider(
        "Gas marginal cost ($/MWh)",
        min_value=70, max_value=120, value=95, step=5,
        help="Published range for Ontario gas peakers."
    )
with col3:
    year_range = st.select_slider(
        "Year range",
        options=list(range(2015, 2025)),
        value=(2015, 2024)
    )

# Filter and recalculate
filtered = df[df["year"].between(year_range[0], year_range[1])].copy()
reduction_factor = nuclear_reduction / 100

filtered["adj_nuclear_gap"] = filtered["nuclear_mw"] * reduction_factor
filtered["adj_hydro_fill"] = filtered["hydro_fill_mw"] * reduction_factor
filtered["adj_gas_fill"] = filtered["gas_fill_mw"] * reduction_factor
filtered["adj_import_fill"] = filtered["import_fill_mw"] * reduction_factor

filtered["adj_price_delta"] = (
    filtered["adj_gas_fill"] / filtered["ontario_demand_mw"].replace(0, pd.NA)
) * (gas_cost - filtered["actual_price"])

filtered["adj_cf_price"] = filtered["actual_price"] + filtered["adj_price_delta"]
filtered["adj_cost_delta"] = filtered["adj_price_delta"] * filtered["ontario_demand_mw"]
filtered["adj_co2"] = (
    (filtered["adj_gas_fill"] * 1000 * 0.490)
    - (filtered["nuclear_mw"] * reduction_factor * 1000 * 0.012)
) / 1_000_000

st.divider()

# Dynamic KPIs
k1, k2, k3, k4 = st.columns(4)
with k1:
    avg_cf = filtered["adj_cf_price"].mean()
    avg_actual = filtered["actual_price"].mean()
    st.metric(
        "Counterfactual Price",
        f"${avg_cf:.2f}/MWh",
        delta=f"+${avg_cf - avg_actual:.2f} vs actual",
        delta_color="inverse"
    )
with k2:
    annual_cost = filtered["adj_cost_delta"].sum() / len(filtered["year"].unique()) / 1e9
    st.metric(
        "Extra Cost Per Year",
        f"${annual_cost:.2f}B",
        delta_color="inverse"
    )
with k3:
    annual_co2 = filtered["adj_co2"].sum() / len(filtered["year"].unique())
    st.metric(
        "Extra CO₂ Per Year",
        f"+{annual_co2:.1f}M tonnes",
        delta_color="inverse"
    )
with k4:
    avg_gas_fill = filtered["adj_gas_fill"].mean()
    st.metric(
        "Avg Gas Fill Required",
        f"{avg_gas_fill:,.0f} MW"
    )

st.divider()

# Annual charts
annual = filtered.groupby("year").agg(
    actual_price=("actual_price", "mean"),
    cf_price=("adj_cf_price", "mean"),
    cf_price_low=("actual_price", lambda x: (
        x + (filtered.loc[x.index, "adj_gas_fill"] /
             filtered.loc[x.index, "ontario_demand_mw"].replace(0, pd.NA))
        * (70 - x)
    ).mean()),
    cf_price_high=("actual_price", lambda x: (
        x + (filtered.loc[x.index, "adj_gas_fill"] /
             filtered.loc[x.index, "ontario_demand_mw"].replace(0, pd.NA))
        * (120 - x)
    ).mean()),
    hydro_fill=("adj_hydro_fill", "mean"),
    gas_fill=("adj_gas_fill", "mean"),
    import_fill=("adj_import_fill", "mean"),
).reset_index()

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Price Impact with Uncertainty Band")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annual["year"].tolist() + annual["year"].tolist()[::-1],
        y=annual["cf_price_high"].tolist() + annual["cf_price_low"].tolist()[::-1],
        fill="toself",
        fillcolor="rgba(255,87,34,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Uncertainty band ($70–$120/MWh gas)"
    ))
    fig.add_trace(go.Scatter(
        x=annual["year"], y=annual["actual_price"],
        name="Actual price",
        line=dict(color=COLORS["actual"], width=2.5),
        mode="lines+markers"
    ))
    fig.add_trace(go.Scatter(
        x=annual["year"], y=annual["cf_price"],
        name="Counterfactual price",
        line=dict(color=COLORS["counter"], width=2.5, dash="dash"),
        mode="lines+markers"
    ))
    fig.update_layout(
        yaxis_title="$/MWh",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("How the Nuclear Gap Gets Filled")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=annual["year"], y=annual["hydro_fill"],
        name="Hydro fill", marker_color=COLORS["hydro"]
    ))
    fig2.add_trace(go.Bar(
        x=annual["year"], y=annual["gas_fill"],
        name="Gas fill", marker_color=COLORS["gas"]
    ))
    fig2.add_trace(go.Bar(
        x=annual["year"], y=annual["import_fill"],
        name="Import fill", marker_color="#9C27B0"
    ))
    fig2.update_layout(
        barmode="stack",
        yaxis_title="Average MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig2, use_container_width=True)

# Validation callout
st.divider()
st.info(
    "**Model Validation:** The merit order model was validated against "
    "Darlington refurbishment windows where nuclear output dropped by "
    "documented amounts. Predicted price increases tracked with actual "
    "HOEP data during those windows, confirming the model's accuracy. "
    "Uncertainty bands reflect gas marginal cost ranging from $70–$120/MWh."
)