import pandas as pd
import streamlit as st

@st.cache_resource
def load_data():
    df = pd.read_parquet("data/fact_counterfactual.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"]  = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["hour"]  = df["datetime"].dt.hour
    return df#[df["year"].between(2015, 2024)]