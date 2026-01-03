import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Satellite Collision Risk Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data
def load_and_clean_data():
    # Attempt to find the CSV in common locations
    file_paths = ['data/tle_data.csv', 'tle_data.csv', '../data/tle_data.csv']
    df = None
    
    for path in file_paths:
        if os.path.exists(path):
            df = pd.read_csv(path)
            break
    
    if df is None:
        return None

    # 1. Clean Dates
    # Auto-detect date column (common names: 'date', 'epoch', 'Time')
    date_col = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower() or 'epoch' in c.lower()), df.columns[0])
    df['normalized_date'] = pd.to_datetime(df[date_col])
    
    # 2. Ensure Distance exists
    dist_col = next((c for c in df.columns if 'dist' in c.lower()), None)
    if dist_col:
        df['distance_m'] = pd.to_numeric(df[dist_col], errors='coerce')
    else:
        # Fallback: create dummy distance if column missing for testing
        df['distance_m'] = 1000 

    # 3. Create Risk Categories if missing
    if 'risk' not in df.columns:
        df['risk'] = pd.cut(df['distance_m'], 
                            bins=[0, 500, 1500, 5000, float('inf')], 
                            labels=['Critical', 'High', 'Medium', 'Low'])
    
    return df

df_raw = load_and_clean_data()

# --- ERROR HANDLING ---
if df_raw is None:
    st.error("⚠️ **Data File Not Found!**")
    st.info("Please ensure `tle_data.csv` is in your `data/` folder on GitHub.")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("🛠️ Control Panel")

# Dynamically set date range based on actual data
min_ts = df_raw['normalized_date'].min().to_pydatetime()
max_ts = df_raw['normalized_date'].max().to_pydatetime()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_ts, max_ts),
    min_value=min_ts,
    max_value=max_ts
)

max_distance = st.sidebar.slider("Max Distance (m)", 100, 5000, 2500)

selected_risks = st.sidebar.multiselect(
    "Risk Categories",
    options=['Critical', 'High', 'Medium', 'Low'],
    default=['Critical', 'High', 'Medium']
)

search_query = st.sidebar.text_input("Satellite name contains (optional)", "")

# --- FILTER LOGIC ---
mask = (df_raw['normalized_date'].dt.date >= date_range[0])
if len(date_range) > 1:
    mask &= (df_raw['normalized_date'].dt.date <= date_range[1])

mask &= (df_raw['distance_m'] <= max_distance)
mask &= (df_raw['risk'].isin(selected_risks))

if search_query:
    # Adjust 'satellite_name' to your actual CSV column name
    name_col = next((c for c in df_raw.columns if 'name' in c.lower() or 'sat' in c.lower()), df_raw.columns[0])
    mask &= (df_raw[name_col].str.contains(search_query, case=False, na=False))

df = df_raw.loc[mask]

# --- MAIN CONTENT ---
st.title("Satellite Collision Risk Dashboard")

tabs = st.tabs(["📊 Overview", "📈 Visualisations", "🧪 Analysis", "📋 Logs"])

# TAB 1: OVERVIEW
with tabs[0]:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Events", len(df))
    m2.metric("Critical Events", len(df[df['risk'] == 'Critical']))
    m3.metric("Closest Approach", f"{df['distance_m'].min():.1f}m" if not df.empty else "N/A")
    m4.metric("Unique Objects", df.iloc[:, 0].nunique() if not df.empty else 0)

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("Risk Event Timeline")
        if not df.empty:
            fig_timeline = px.scatter(df, x='normalized_date', y='distance_m', color='risk',
                                    hover_data=df.columns, template="plotly_dark")
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("No events match current filters.")

    with col_right:
        st.subheader("Risk Distribution")
        if not df.empty:
            fig_pie = px.pie(df, names='risk', hole=0.4, template="plotly_dark",
                            color_discrete_map={'Critical':'red', 'High':'orange', 'Medium':'yellow', 'Low':'blue'})
            st.plotly_chart(fig_pie, use_container_width=True)

# TAB 2: VISUALISATIONS
with tabs[1]:
    if not df.empty:
        st.subheader("Distance vs Velocity (If available)")
        # Example of a more complex chart
        fig_hist = px.histogram(df, x="distance_m", color="risk", nbins=30, template="plotly_dark")
        st.plotly_chart(fig_hist, use_container_width=True)

# TAB 3: ANALYSIS
with tabs[2]:
    st.subheader("Conjunction Data Table")
    st.dataframe(df, use_container_width=True)

# TAB 4: LOGS
with tabs[3]:
    st.subheader("System Logs")
    st.code(f"Successfully loaded {len(df_raw)} rows from CSV.\nFilters applied: Distance < {max_distance}m.\nRows after filtering: {len(df)}")
