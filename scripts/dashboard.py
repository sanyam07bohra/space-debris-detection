# ============================================================
# SATELLITE ORBIT VISUALIZATION DASHBOARD (EDUCATIONAL)
# Author: Team Infinity
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Satellite Orbit Visualization",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ Satellite Orbit Visualization Dashboard")
st.caption("Educational visualization of real satellite orbits using TLE propagation")

# ============================================================
# SAFE FILE LOADING
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(_file_))
DATA_PATH = os.path.join(BASE_DIR, "data", "all_satellite_orbits.csv")

@st.cache_data(show_spinner=True)
def load_orbit_data(path):
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)

    # Normalize column names (defensive)
    df.columns = df.columns.str.strip()

    # Parse timestamps safely
    if "Time (UTC)" in df.columns:
        df["Time (UTC)"] = pd.to_datetime(df["Time (UTC)"], errors="coerce")

    # Force numeric columns
    for col in ["Latitude", "Longitude", "Altitude (m)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop fully invalid rows
    df = df.dropna(subset=["Time (UTC)", "Latitude", "Longitude", "Altitude (m)"])

    return df

df = load_orbit_data(DATA_PATH)

if df is None or df.empty:
    st.error("❌ Orbit data not found or invalid.")
    st.stop()

st.success("✅ Orbit data loaded successfully")

# ============================================================
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.header("🔧 Controls")

# ---- Date range ----
min_date = df["Time (UTC)"].min().date()
max_date = df["Time (UTC)"].max().date()

date_range = st.sidebar.date_input(
    "Simulation Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# ---- Satellite selection ----
satellites = sorted(df["Satellite Name"].unique())
selected_sat = st.sidebar.selectbox(
    "Select Satellite (optional)",
    ["All Satellites"] + satellites
)

# ---- Altitude filter ----
min_alt = float(df["Altitude (m)"].min())
max_alt = float(df["Altitude (m)"].max())

altitude_range = st.sidebar.slider(
    "Altitude Range (meters)",
    min_value=int(min_alt),
    max_value=int(max_alt),
    value=(int(min_alt), int(max_alt)),
    step=1000
)

# ============================================================
# DATA FILTERING
# ============================================================
filtered_df = df.copy()

# Date filter
filtered_df = filtered_df[
    (filtered_df["Time (UTC)"].dt.date >= start_date) &
    (filtered_df["Time (UTC)"].dt.date <= end_date)
]

# Satellite filter
if selected_sat != "All Satellites":
    filtered_df = filtered_df[filtered_df["Satellite Name"] == selected_sat]

# Altitude filter
filtered_df = filtered_df[
    (filtered_df["Altitude (m)"] >= altitude_range[0]) &
    (filtered_df["Altitude (m)"] <= altitude_range[1])
]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# ============================================================
# TOP METRICS
# ============================================================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Data Points", len(filtered_df))
c2.metric("Satellites", filtered_df["Satellite Name"].nunique())
c3.metric("Min Altitude (m)", f"{filtered_df['Altitude (m)'].min():.0f}")
c4.metric("Max Altitude (m)", f"{filtered_df['Altitude (m)'].max():.0f}")

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["🌍 Global View", "🛰️ Ground Track", "📊 Analysis", "📋 Data"]
)

# ============================================================
# TAB 1: GLOBAL DISTRIBUTION
# ============================================================
with tab1:
    st.subheader("Global Satellite Distribution")

    fig_global = px.scatter_geo(
        filtered_df,
        lat="Latitude",
        lon="Longitude",
        color="Altitude (m)",
        hover_name="Satellite Name",
        hover_data=["Time (UTC)", "Altitude (m)"],
        projection="natural earth",
        color_continuous_scale="Viridis"
    )

    fig_global.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    st.plotly_chart(fig_global, use_container_width=True)

# ============================================================
# TAB 2: GROUND TRACK (PATH VISUALIZATION)
# ============================================================
with tab2:
    st.subheader("Satellite Ground Track")

    if selected_sat == "All Satellites":
        st.info("Select a specific satellite from the sidebar to view its ground track.")
    else:
        sat_df = filtered_df.sort_values("Time (UTC)")

        fig_track = px.line_geo(
            sat_df,
            lat="Latitude",
            lon="Longitude",
            hover_data=["Time (UTC)", "Altitude (m)"],
            title=f"Ground Track of {selected_sat}"
        )

        fig_track.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=40, b=0)
        )

        st.plotly_chart(fig_track, use_container_width=True)

# ============================================================
# TAB 3: ANALYSIS
# ============================================================
with tab3:
    st.subheader("Orbital Analysis")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### Altitude vs Time")

        fig_alt_time = px.line(
            filtered_df.sort_values("Time (UTC)"),
            x="Time (UTC)",
            y="Altitude (m)",
            color="Satellite Name",
            labels={"Altitude (m)": "Altitude (meters)"}
        )

        st.plotly_chart(fig_alt_time, use_container_width=True)

    with colB:
        st.markdown("### Altitude Distribution")

        fig_alt_hist = px.histogram(
            filtered_df,
            x="Altitude (m)",
            nbins=30,
            title="Altitude Histogram"
        )

        st.plotly_chart(fig_alt_hist, use_container_width=True)

# ============================================================
# TAB 4: RAW DATA
# ============================================================
with tab4:
    st.subheader("Orbit Data Table")

    show_cols = [
        "Satellite Name",
        "Time (UTC)",
        "Latitude",
        "Longitude",
        "Altitude (m)"
    ]

    st.dataframe(
        filtered_df[show_cols],
        use_container_width=True
    )

    st.download_button(
        "📥 Download Filtered Data",
        filtered_df.to_csv(index=False),
        file_name="filtered_orbit_data.csv",
        mime="text/csv"
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(
    "Data source: Celestrak | Orbit propagation: Skyfield | Visualization: Plotly + Streamlit"
)
