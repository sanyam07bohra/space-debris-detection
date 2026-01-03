import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# === Page & Layout ======
st.set_page_config(page_title="Satellite Collision Risk Dashboard", layout="wide")

# === Load Data ===
# Robust read with parse_dates; if something goes wrong, fail gracefully.
try:
    df = pd.read_csv("../data/persistent_risks.csv", parse_dates=["Timestamp"])
except Exception as e:
    st.error(f"Failed to read CSV: {e}")
    df = pd.DataFrame(
        columns=[
            "Timestamp", "Satellite 1", "Satellite 2", "Distance (m)",
            "Latitude", "Longitude", "Avg Altitude", "Risk Score"
        ]
    )

# Ensure expected columns exist (prevents KeyErrors later)
for col in ["Satellite 1", "Satellite 2", "Distance (m)", "Latitude", "Longitude", "Avg Altitude", "Risk Score"]:
    if col not in df.columns:
        df[col] = np.nan

# === Style ===
st.markdown("""
    <style>
    /* Reduce main padding inside content block */
    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }
    /* Compact title spacing */
    h1 { margin-bottom: 0.4rem; }
    /* KPI card look for metrics row */
    .kpi-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid rgba(0,0,0,0.06);
    }
    .kpi-label {
        font-size: 13px;
        color:  rgb(0,0,0);
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 600;
        line-height: 1.2;
        color: rgb(0,0,0);
    }
    /* Smaller table header text */
    .stDataFrame table thead th { font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

# === Labels / Colors ===
color_map = {
    "Critical": "red",
    "High": "orange",
    "Medium": "yellow",
    "Low": "green"
}

# === Risk Level Categorization ===
def categorize_risk(score):
    try:
        if pd.isna(score):
            return "Low"
        if score > 0.01:
            return "Critical"
        elif score > 0.005:
            return "High"
        elif score > 0.001:
            return "Medium"
        else:
            return "Low"
    except Exception:
        return "Low"

df["Risk Level"] = df["Risk Score"].apply(categorize_risk)

# === Sidebar Controls ===
st.sidebar.header("🔧 Control Panel")

# Date range filter (defensive for empty data)
if df["Timestamp"].notna().any():
    min_date = df["Timestamp"].min().date()
    max_date = df["Timestamp"].max().date()
else:
    # fallback for empty/invalid timestamp data
    today = pd.Timestamp.today().date()
    min_date = today
    max_date = today

date_range = st.sidebar.date_input("Date Range", [min_date, max_date])
# Streamlit can return a single date or a tuple of two dates; normalize to (start, end)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date_range if date_range else min_date
    end_date = date_range if date_range else max_date

# Distance threshold - updates filter immediately when moved
max_dist = st.sidebar.slider("Max Distance (m)", 100, 5000, 500, step=100)
st.sidebar.caption("Only events within this distance will be shown (max precomputed = 5000 m)")

# Risk level selection
risk_levels = st.sidebar.multiselect(
    "Risk Categories",
    ["Critical", "High", "Medium", "Low"],
    default=["Critical", "High", "Medium"]
)

# OPTIONAL: satellite quick search to help narrow (doesn't remove any prior feature)
sat_query = st.sidebar.text_input("Satellite name contains (optional)").strip()

# === Filter Data (defensive to avoid crashes on NaNs/NaT) ===
filtered_df = df.copy()
if not filtered_df.empty:
    # Date filter (skip rows with NaT)
    if "Timestamp" in filtered_df.columns:
        mask_date = (
            filtered_df["Timestamp"].notna()
            & (filtered_df["Timestamp"].dt.date >= start_date)
            & (filtered_df["Timestamp"].dt.date <= end_date)
        )
        filtered_df = filtered_df[mask_date]

    # Distance filter (NaNs treated as very large -> excluded)
    filtered_df = filtered_df[filtered_df["Distance (m)"].fillna(1e12) <= max_dist]

    # Risk level filter
    filtered_df = filtered_df[filtered_df["Risk Level"].isin(risk_levels)]

    # Satellite query (optional)
    if sat_query:
        mask_sat = (
            filtered_df["Satellite 1"].astype(str).str.contains(sat_query, case=False, na=False) |
            filtered_df["Satellite 2"].astype(str).str.contains(sat_query, case=False, na=False)
        )
        filtered_df = filtered_df[mask_sat]

# === Top Summary ===
st.title("Satellite Collision Risk Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Visualisations", "Analysis", "Logs"])

#===============================================================
# Tab 1: Overview (compact & safe KPIs, map + pie side-by-side)
with tab1:
    # --- KPIs (ALWAYS render; handle empties safely) ---
    col1, col2, col3, col4 = st.columns(4)

    total_events = int(len(filtered_df)) if not filtered_df.empty else 0
    critical_events = int((filtered_df["Risk Level"] == "Critical").sum()) if not filtered_df.empty else 0

    # Closest approach (safe formatting)
    closest_val = filtered_df["Distance (m)"].min() if not filtered_df.empty else np.nan
    closest_text = f"{closest_val:.2f} m" if pd.notna(closest_val) else "—"

    # Unique satellites involved (drop NaNs, union both columns)
    if not filtered_df.empty:
        s1 = set(filtered_df["Satellite 1"].dropna().astype(str))
        s2 = set(filtered_df["Satellite 2"].dropna().astype(str))
        unique_sats = len(s1.union(s2))
    else:
        unique_sats = 0


    with col1:
        st.markdown('<div class="kpi-card"><div class="kpi-label">Total Events</div><div class="kpi-value">{}</div></div>'.format(total_events), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="kpi-card"><div class="kpi-label">Critical Events</div><div class="kpi-value">{}</div></div>'.format(critical_events), unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="kpi-card"><div class="kpi-label">Closest Approach</div><div class="kpi-value">{}</div></div>'.format(closest_text), unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="kpi-card"><div class="kpi-label">Unique Satellites at Risk</div><div class="kpi-value">{}</div></div>'.format(unique_sats), unsafe_allow_html=True)

    st.write("")  # small spacer

    # --- Map + Pie side-by-side to save vertical space ---
    map_col, pie_col = st.columns([2, 1], gap="large")

    with map_col:
        st.markdown("#### Risk Event Map")
        map_df = filtered_df.dropna(subset=["Latitude", "Longitude"]) if not filtered_df.empty else filtered_df
        if map_df.empty:
            st.info("No geolocated events for current filters.")
        else:
            fig_map = px.scatter_geo(
                map_df,
                lat="Latitude",
                lon="Longitude",
                color="Risk Level",
                size="Risk Score",
                hover_name="Satellite 1",
                hover_data=["Satellite 2", "Timestamp", "Distance (m)", "Risk Score"],
                projection="natural earth",
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_map, use_container_width=True)

    with pie_col:
        st.markdown("#### Risk Distribution")
        if filtered_df.empty:
            st.info("No events to build distribution.")
        else:
            pie_data = (
                filtered_df["Risk Level"]
                .value_counts()
                .rename_axis("Risk Level")
                .reset_index(name="Count")
            )
            fig_pie = px.pie(
                pie_data,
                values="Count",
                names="Risk Level",
                color="Risk Level",
                title="Risk Level Distribution",
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_pie, use_container_width=True)

#===============================================================
# Tab 2: Visualisations (no functionality removed)
with tab2:
    st.markdown("#### Visualisation Dashboard")

    sub_tab = st.radio("Select Section", ["Event Timeline", "Altitude v/s Distance", "Most Involved Satellite"], horizontal=True)

    if sub_tab == "Event Timeline":
        with st.expander("View Event Timeline", expanded=True):
            st.subheader("📊 Events Over Time")
            if filtered_df.empty:
                st.info("No events for current filters.")
            else:
                bar_data = (
                    filtered_df
                    .groupby(filtered_df["Timestamp"].dt.floor("h"))
                    .size()
                    .reset_index(name="Events")
                    .sort_values("Timestamp")
                )
                fig_bar = px.bar(
                    bar_data,
                    x="Timestamp",
                    y="Events",
                    title="Events Over Time",
                    labels={"Events": "Number of Events"}
                )
                # Add moving average trendline (2-hour window)
                if len(bar_data) >= 2:
                    fig_bar.add_scatter(
                        x=bar_data["Timestamp"],
                        y=bar_data["Events"].rolling(window=2, min_periods=1).mean(),
                        mode="lines",
                        name="2-hour Moving Average",
                        line=dict(dash="dash")
                    )
                st.plotly_chart(fig_bar, use_container_width=True)

    elif sub_tab == "Altitude v/s Distance":
        with st.expander("View Altitude vs Distance Chart", expanded=True):
            st.subheader("Altitude vs Distance")
            if filtered_df.empty:
                st.info("No events to plot.")
            else:
                fig_alt = px.scatter(
                    filtered_df,
                    x="Distance (m)",
                    y="Avg Altitude",
                    color="Risk Level",
                    color_discrete_map=color_map,
                    hover_data=["Satellite 1", "Satellite 2", "Timestamp"],
                    title="Distance vs Altitude"
                )
                # Visual bands for distance zones (transparent)
                fig_alt.update_layout(
                    shapes=[
                        dict(type="rect", xref="x", yref="paper", x0=0,    x1=500,  y0=0, y1=1, fillcolor="rgba(255,0,0,0.06)",   line_width=0),
                        dict(type="rect", xref="x", yref="paper", x0=500,  x1=1000, y0=0, y1=1, fillcolor="rgba(255,165,0,0.06)", line_width=0),
                        dict(type="rect", xref="x", yref="paper", x0=1000, x1=3000, y0=0, y1=1, fillcolor="rgba(255,215,0,0.06)", line_width=0),
                        dict(type="rect", xref="x", yref="paper", x0=3000, x1=5000, y0=0, y1=1, fillcolor="rgba(0,128,0,0.04)",   line_width=0),
                    ]
                )
                st.plotly_chart(fig_alt, use_container_width=True)

    elif sub_tab == "Most Involved Satellite":
        st.subheader("Satellite name v/s Count")
        if filtered_df.empty:
            st.info("No events to compute counts.")
        else:
            all_sats = pd.concat([filtered_df["Satellite 1"], filtered_df["Satellite 2"]]).fillna("Unknown")
            top_sats = all_sats.value_counts().nlargest(10).reset_index()
            top_sats.columns = ["Satellite", "Count"]
            fig_sat = px.bar(top_sats, x="Count", y="Satellite", orientation='h', title="Most Involved Satellites")
            st.plotly_chart(fig_sat, use_container_width=True)

        # === Closest Encounter Card (across full dataset; safe if empty) ===
        if df["Distance (m)"].notna().any():
            try:
                closest_idx = df["Distance (m)"].idxmin()
                closest_row = df.loc[closest_idx]
                st.info(f"*Closest Encounter:* {closest_row['Satellite 1']} ↔ {closest_row['Satellite 2']} at {closest_row['Timestamp']} — {closest_row['Distance (m)']:.2f} m")
            except Exception:
                st.info("Closest Encounter: data not sufficient.")
        else:
            st.info("Closest Encounter: data not available.")

#===============================================================
# Tab 3: Analysis (same tools retained)
with tab3:
    st.markdown("#### Analysis Dashboard")

    sub_tab = st.radio("Select Section", ["Satellite Risk Timeline", "Hourly Risk Heatmap", "Satellite Encounter Filter"], horizontal=True)

    if sub_tab == "Satellite Risk Timeline":
        st.subheader("Satellite Risk Timeline")
        sat_options = sorted(set(df["Satellite 1"].dropna().astype(str)).union(set(df["Satellite 2"].dropna().astype(str))))
        selected_sat = st.selectbox("Select Satellite", sat_options)
        sat_df = df[(df["Satellite 1"] == selected_sat) | (df["Satellite 2"] == selected_sat)]

        if not sat_df.empty:
            fig_line = px.line(
                sat_df.sort_values("Timestamp"),
                x="Timestamp",
                y="Distance (m)",
                color="Risk Level",
                title=f"Risk Timeline for {selected_sat}",
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_line, use_container_width=True)
            st.download_button("Download Satellite Timeline", sat_df.to_csv(index=False), f"{selected_sat}_timeline.csv", "text/csv")
        else:
            st.warning("No events found for selected satellite.")

    elif sub_tab == "Hourly Risk Heatmap":
        st.subheader("Hourly Risk Heatmap")
        if filtered_df.empty:
            st.info("No events for current filters.")
        else:
            heat_df = filtered_df.copy()
            heat_df["Hour"] = heat_df["Timestamp"].dt.hour
            heat_counts = heat_df.groupby(["Hour", "Risk Level"]).size().unstack().fillna(0)

            st.write("### Event Frequency by Hour & Risk Level")
            st.dataframe(heat_counts)

            fig_heat = px.imshow(
                heat_counts.T,
                labels=dict(x="Hour of Day", y="Risk Level", color="Event Count"),
                x=heat_counts.index,
                y=heat_counts.columns,
                color_continuous_scale="YlOrRd"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    elif sub_tab == "Satellite Encounter Filter":
        st.subheader("🛰️ Satellite Encounter Filter")
        sat1 = st.selectbox("Satellite A", sorted(df["Satellite 1"].dropna().astype(str).unique()))
        sat2 = st.selectbox("Satellite B", sorted(df["Satellite 2"].dropna().astype(str).unique()))

        proximity_df = df[
            ((df["Satellite 1"] == sat1) & (df["Satellite 2"] == sat2)) |
            ((df["Satellite 1"] == sat2) & (df["Satellite 2"] == sat1))
        ]

        if not proximity_df.empty:
            fig_pair = px.line(
                proximity_df.sort_values("Timestamp"),
                x="Timestamp", y="Distance (m)",
                title=f"Proximity between {sat1} and {sat2}",
                markers=True
            )
            st.plotly_chart(fig_pair, use_container_width=True)
        else:
            st.info("No close encounters found between the selected satellites.")

#===============================================================
# Tab 4: Logs (unchanged core, just compact)
with tab4:
    st.subheader("📋 Detailed Event Log")
    # Show only selected, core columns but keep others accessible
    cols_to_show = [
        "Timestamp", "Satellite 1", "Satellite 2", "Distance (m)", "Risk Level",
        "Latitude", "Longitude", "Avg Altitude", "Risk Score"
    ]
    # Some datasets may miss a column if badly formatted; filter to existing ones:
    cols_to_show = [c for c in cols_to_show if c in filtered_df.columns]

    st.dataframe(filtered_df[cols_to_show], use_container_width=True)

# === Export Button (kept as in your code) ===
st.download_button("📥 Download Filtered Data", filtered_df.to_csv(index=False), "filtered_events.csv", "text/csv")
