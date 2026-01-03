import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Satellite Orbit Visualisation & Learning Dashboard",
    layout="wide"
)

# ============================================================
# DATA LOADING (ROBUST & CACHED)
# ============================================================
@st.cache_data
def load_orbit_data():
    df = pd.read_csv(
        "../data/all_satellite_orbits.csv",
        parse_dates=["Time (UTC)"]
    )

    # Ensure numeric consistency
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["Altitude (m)"] = pd.to_numeric(df["Altitude (m)"], errors="coerce")

    # Drop non-physical rows
    df = df.dropna(
        subset=["Latitude", "Longitude", "Altitude (m)", "Time (UTC)", "Satellite Name"]
    )

    return df


try:
    df = load_orbit_data()
except Exception as e:
    st.error(f"❌ Failed to load orbit data: {e}")
    st.stop()

# ============================================================
# SIDEBAR — USER CONTROLS
# ============================================================
st.sidebar.header("🛰️ Orbit Controls")

# Date range filter
min_date = df["Time (UTC)"].min().date()
max_date = df["Time (UTC)"].max().date()
start_date, end_date = st.sidebar.date_input(
    "Simulation Date Range",
    [min_date, max_date]
)

# Satellite selection
satellites = sorted(df["Satellite Name"].unique())
selected_sats = st.sidebar.multiselect(
    "Select Satellites (optional)",
    satellites,
    help="Leave empty to view all satellites"
)

# Altitude filter
alt_min = int(np.floor(df["Altitude (m)"].min()))
alt_max = int(np.ceil(df["Altitude (m)"].max()))

alt_range = st.sidebar.slider(
    "Altitude Range (meters)",
    alt_min,
    alt_max,
    (alt_min, alt_max),
    step=1000
)

# Time downsampling (performance + learning)
time_step = st.sidebar.selectbox(
    "Time Resolution",
    ["All", "5 min", "10 min", "30 min"],
    help="Reduce points for clarity and performance"
)

# ============================================================
# DATA FILTERING
# ============================================================
filtered_df = df[
    (df["Time (UTC)"].dt.date >= start_date) &
    (df["Time (UTC)"].dt.date <= end_date) &
    (df["Altitude (m)"] >= alt_range[0]) &
    (df["Altitude (m)"] <= alt_range[1])
]

if selected_sats:
    filtered_df = filtered_df[
        filtered_df["Satellite Name"].isin(selected_sats)
    ]

# Time downsampling
if time_step != "All":
    rule = {"5 min": "5min", "10 min": "10min", "30 min": "30min"}[time_step]
    filtered_df["Time Bin"] = filtered_df["Time (UTC)"].dt.floor(rule)
    filtered_df = (
        filtered_df
        .groupby(["Satellite Name", "Time Bin"])
        .first()
        .reset_index()
        .rename(columns={"Time Bin": "Time (UTC)"})
    )

# ============================================================
# TITLE
# ============================================================
st.title("🛰️ Satellite Orbit Visualisation & Learning Dashboard")

st.markdown("""
This dashboard is designed for **educational and aerospace study purposes**.
It visualizes **real orbital motion** derived from satellite metadata and propagation.
""")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Global Distribution", "Orbit Dynamics", "Data Explorer"]
)

# ============================================================
# TAB 1 — OVERVIEW (EDUCATIONAL KPIs)
# ============================================================
with tab1:
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Unique Satellites", filtered_df["Satellite Name"].nunique())
    c2.metric("Orbit Samples", len(filtered_df))
    c3.metric(
        "Mean Altitude (m)",
        f"{filtered_df['Altitude (m)'].mean():,.0f}"
    )
    c4.metric(
        "Time Span",
        f"{start_date} → {end_date}"
    )

    st.markdown("""
### 📘 How to interpret this
- Each point represents a **satellite position at a given time**
- Motion is governed by **orbital mechanics**, not Earth rotation
- Ground tracks repeat due to **orbital resonance**
    """)

# ============================================================
# TAB 2 — GLOBAL DISTRIBUTION
# ============================================================
with tab2:
    st.subheader("🌍 Global Satellite Distribution")

    fig_geo = px.scatter_geo(
        filtered_df,
        lat="Latitude",
        lon="Longitude",
        color="Altitude (m)",
        hover_name="Satellite Name",
        hover_data={
            "Time (UTC)": True,
            "Altitude (m)": ":.0f"
        },
        projection="natural earth",
        color_continuous_scale="Viridis",
        title="Satellite Positions Over Earth"
    )

    st.plotly_chart(fig_geo, use_container_width=True)

    st.markdown("""
**Insight:**
- Dense bands indicate orbital inclination
- Gaps near poles/equator reveal constellation design choices
""")

# ============================================================
# TAB 3 — ORBIT DYNAMICS & MOTION
# ============================================================
with tab3:
    st.subheader("🛰️ Single-Satellite Orbit Analysis")

    selected_sat = st.selectbox(
        "Choose a Satellite",
        satellites
    )

    sat_df = (
        df[df["Satellite Name"] == selected_sat]
        .sort_values("Time (UTC)")
    )

    # Ground track
    st.markdown("### Ground Track (Satellite Path over Earth)")
    fig_track = px.line_geo(
        sat_df,
        lat="Latitude",
        lon="Longitude",
        color="Altitude (m)",
        projection="natural earth",
        title=f"Ground Track of {selected_sat}"
    )
    st.plotly_chart(fig_track, use_container_width=True)

    # Altitude vs time
    st.markdown("### Altitude vs Time")
    fig_alt = px.line(
        sat_df,
        x="Time (UTC)",
        y="Altitude (m)",
        title="Orbital Altitude Variation"
    )
    st.plotly_chart(fig_alt, use_container_width=True)

    st.markdown("""
**Learning Notes:**
- Nearly constant altitude → circular orbit
- Periodic variation → orbital perturbations or eccentricity
""")

# ============================================================
# TAB 4 — DATA EXPLORER
# ============================================================
with tab4:
    st.subheader("📄 Orbit Data Explorer")

    st.dataframe(
        filtered_df[
            ["Time (UTC)", "Satellite Name", "Latitude", "Longitude", "Altitude (m)"]
        ],
        use_container_width=True
    )

    st.download_button(
        "📥 Download Filtered Orbit Data",
        filtered_df.to_csv(index=False),
        "filtered_orbit_data.csv",
        "text/csv"
    )
