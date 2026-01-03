import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Space Debris Detection", layout="wide", page_icon="🛰️")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Looking for the specific file seen in your screenshot
    file_path = 'data/collision_risks.csv'
    
    if not os.path.exists(file_path):
        # Try local path if streamlit path fails
        file_path = 'collision_risks.csv'

    try:
        df = pd.read_csv(file_path)
        
        # 1. Handle Dates
        # Based on typical space data, we look for 'date', 'epoch', or 'time'
        date_col = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(date_col)
        
        # 2. Handle Distance
        # Your CSV likely uses 'distance' or 'miss_distance'
        dist_col = next((c for c in df.columns if 'dist' in c.lower()), None)
        if dist_col:
            df['dist_display'] = pd.to_numeric(df[dist_col], errors='coerce')
        else:
            df['dist_display'] = 0

        return df, date_col
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

df, date_column = load_data()

# --- SIDEBAR ---
st.sidebar.title("Control Panel")

if df is not None:
    # Auto-adjust Date Range to match your CSV content so you don't get '0 events'
    min_date = df[date_column].min().to_pydatetime()
    max_date = df[date_column].max().to_pydatetime()

    selected_dates = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    max_dist = st.sidebar.slider("Max Distance (m)", 0, 10000, 5000)

    # Filtering Logic
    if len(selected_dates) == 2:
        mask = (df[date_column].dt.date >= selected_dates[0]) & \
               (df[date_column].dt.date <= selected_dates[1]) & \
               (df['dist_display'] <= max_dist)
        filtered_df = df.loc[mask]
    else:
        filtered_df = df
else:
    st.stop()

# --- MAIN DASHBOARD ---
st.title("🛰️ Satellite Collision Risk Dashboard")

# Top Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Events", len(filtered_df))
m2.metric("Closest Approach", f"{filtered_df['dist_display'].min():.2f}m" if not filtered_df.empty else "N/A")
m3.metric("Avg Distance", f"{filtered_df['dist_display'].mean():.2f}m" if not filtered_df.empty else "N/A")
m4.metric("Data Source", "collision_risks.csv")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Analysis", "📋 Raw Data"])

with tab1:
    if not filtered_df.empty:
        fig = px.scatter(filtered_df, x=date_column, y='dist_display', 
                         color='dist_display', size_max=10,
                         title="Collision Risk Timeline",
                         template="plotly_dark",
                         labels={'dist_display': 'Distance (meters)'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No events found. Try expanding the Date Range in the sidebar.")

with tab2:
    if not filtered_df.empty:
        fig2 = px.histogram(filtered_df, x='dist_display', nbins=20, 
                            title="Distance Distribution", template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.dataframe(filtered_df, use_container_width=True)
