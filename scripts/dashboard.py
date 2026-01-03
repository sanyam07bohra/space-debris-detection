import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
from google import genai

# === 1. INITIALIZE GEMINI API ===
# Use the API key you generated. For security, never share this publicly.
try:
    # Replace the string below with your NEW secret key
    API_KEY = "AIzaSyAjpfO5bjmMEHTWYSb1NihMv8jR-EzpNH4" 
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(f"AI initialization failed: {e}. Check your API key.")

# === Page & Layout ======
st.set_page_config(page_title="Satellite Collision Risk Dashboard", layout="wide")

# === Load Data ===
# Check both possible paths to ensure students see data regardless of folder structure
data_path = "data/persistent_risks.csv" if os.path.exists("data/persistent_risks.csv") else "../data/persistent_risks.csv"

try:
    df = pd.read_csv(data_path, parse_dates=["Timestamp"])
except Exception as e:
    st.error(f"Failed to read CSV: {e}")
    df = pd.DataFrame(columns=["Timestamp", "Satellite 1", "Satellite 2", "Distance (m)", "Latitude", "Longitude", "Avg Altitude", "Risk Score"])

# Ensure expected columns exist for the physics engine [cite: 8, 9]
for col in ["Satellite 1", "Satellite 2", "Distance (m)", "Latitude", "Longitude", "Avg Altitude", "Risk Score"]:
    if col not in df.columns:
        df[col] = np.nan

# === Labels / Colors ===
color_map = {
    "Critical": "red",
    "High": "orange",
    "Medium": "yellow",
    "Low": "green"
}

# === Custom CSS Styling ===
st.markdown("""
    <style>
    .block-container { padding: 0.75rem; }
    h1 { margin-bottom: 0.4rem; }
    .kpi-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid rgba(0,0,0,0.06);
        text-align: center;
    }
    .kpi-label { font-size: 13px; color: rgb(100,100,100); margin-bottom: 6px; }
    .kpi-value { font-size: 22px; font-weight: 600; color: rgb(0,0,0); }
    </style>
""", unsafe_allow_html=True)

# === Risk Level Categorization ===
def categorize_risk(score):
    if pd.isna(score): return "Low"
    if score > 0.01: return "Critical"
    elif score > 0.005: return "High"
    elif score > 0.001: return "Medium"
    return "Low"

df["Risk Level"] = df["Risk Score"].apply(categorize_risk)

# === Sidebar Controls ===
st.sidebar.header("🔧 Control Panel")
if df["Timestamp"].notna().any():
    min_date, max_date = df["Timestamp"].min().date(), df["Timestamp"].max().date()
else:
    min_date = max_date = pd.Timestamp.today().date()

date_range = st.sidebar.date_input("Date Range", [min_date, max_date])
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

max_dist = st.sidebar.slider("Max Distance (m)", 100, 5000, 1000, step=100)
risk_levels = st.sidebar.multiselect("Risk Categories", ["Critical", "High", "Medium", "Low"], default=["Critical", "High"])
sat_query = st.sidebar.text_input("Satellite search").strip()

# === Filter Data ===
filtered_df = df.copy()
if not filtered_df.empty:
    if "Timestamp" in filtered_df.columns:
        mask = (filtered_df["Timestamp"].dt.date >= start_date) & (filtered_df["Timestamp"].dt.date <= end_date)
        filtered_df = filtered_df[mask]
    filtered_df = filtered_df[filtered_df["Distance (m)"].fillna(1e12) <= max_dist]
    filtered_df = filtered_df[filtered_df["Risk Level"].isin(risk_levels)]
    if sat_query:
        mask_sat = (filtered_df["Satellite 1"].str.contains(sat_query, case=False, na=False) | 
                    filtered_df["Satellite 2"].str.contains(sat_query, case=False, na=False))
        filtered_df = filtered_df[mask_sat]

# === Dashboard Content ===
st.title("Satellite Collision Risk Dashboard 🛰️")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Visualisations", "Analysis", "Logs", "🎓 AI Physics Tutor"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Events</div><div class="kpi-value">{len(filtered_df)}</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Critical Events</div><div class="kpi-value">{(filtered_df["Risk Level"]=="Critical").sum()}</div></div>', unsafe_allow_html=True)
    with col3:
        closest = filtered_df["Distance (m)"].min()
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Closest Approach</div><div class="kpi-value">{closest:.2f} m</div></div>' if not pd.isna(closest) else "—", unsafe_allow_html=True)
    with col4:
        u_sats = len(set(filtered_df["Satellite 1"].dropna()).union(set(filtered_df["Satellite 2"].dropna())))
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Sats at Risk</div><div class="kpi-value">{u_sats}</div></div>', unsafe_allow_html=True)

    st.write("")
    map_col, pie_col = st.columns([2, 1], gap="large")
    with map_col:
        st.markdown("#### Risk Event Map")
        if not filtered_df.empty:
            st.plotly_chart(px.scatter_geo(filtered_df.dropna(subset=["Latitude", "Longitude"]), lat="Latitude", lon="Longitude", color="Risk Level", size="Risk Score", projection="natural earth", color_discrete_map=color_map), use_container_width=True)
    with pie_col:
        st.markdown("#### Risk Distribution")
        if not filtered_df.empty:
            st.plotly_chart(px.pie(filtered_df, names="Risk Level", color="Risk Level", color_discrete_map=color_map, hole=0.3), use_container_width=True)

with tab2:
    st.markdown("#### Visualisation Dashboard")
    sub = st.radio("Section", ["Timeline", "Altitude vs Distance", "Top Satellites"], horizontal=True)
    if sub == "Timeline" and not filtered_df.empty:
        bar_data = filtered_df.groupby(filtered_df["Timestamp"].dt.floor("h")).size().reset_index(name="Events")
        st.plotly_chart(px.bar(bar_data, x="Timestamp", y="Events"), use_container_width=True)
    elif sub == "Altitude vs Distance" and not filtered_df.empty:
        st.plotly_chart(px.scatter(filtered_df, x="Distance (m)", y="Avg Altitude", color="Risk Level", color_discrete_map=color_map), use_container_width=True)

with tab3:
    st.markdown("#### Analysis Dashboard")
    an_mode = st.radio("Mode", ["Individual Satellite", "Heatmap"], horizontal=True)
    if an_mode == "Individual Satellite":
        opts = sorted(set(df["Satellite 1"].dropna()).union(set(df["Satellite 2"].dropna())))
        sel = st.selectbox("Select Satellite", opts)
        s_df = df[(df["Satellite 1"] == sel) | (df["Satellite 2"] == sel)]
        st.plotly_chart(px.line(s_df.sort_values("Timestamp"), x="Timestamp", y="Distance (m)", color="Risk Level", color_discrete_map=color_map), use_container_width=True)
    else:
        if not filtered_df.empty:
            heat_df = filtered_df.copy()
            heat_df["Hour"] = heat_df["Timestamp"].dt.hour
            hc = heat_df.groupby(["Hour", "Risk Level"]).size().unstack().fillna(0)
            st.plotly_chart(px.imshow(hc.T, color_continuous_scale="YlOrRd"), use_container_width=True)

with tab4:
    st.subheader("📋 Detailed Event Log")
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button("📥 Download Filtered Data", filtered_df.to_csv(index=False), "filtered_events.csv", "text/csv")

# === Tab 5: THE AI TUTOR ===
with tab5:
    st.header("🎓 AI Space Science Tutor")
    st.write("Ask the AI to explain the orbital mechanics or collision risks shown in this data.")
    user_input = st.text_input("Type your question here (e.g., 'What is Kessler Syndrome?')")
    
    if user_input:
        context_summary = filtered_df.sort_values("Risk Score", ascending=False).head(5)[["Satellite 1", "Satellite 2", "Distance (m)", "Risk Score"]].to_string()
        
        prompt = (
            f"You are an expert Astrophysics Tutor. Use this current satellite data context:\n{context_summary}\n\n"
            f"Explain to a student in plain language: {user_input}. "
            "Discuss concepts like orbital decay, TLE elements, or Kessler Syndrome if relevant."
        )

        with st.spinner("Gemini is analyzing orbits..."):
            try:
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.markdown("### 🔭 Tutor's Analysis")
                st.write(response.text)
            except Exception as e:
                st.error(f"Gemini Error: {e}. Check your API key.")

    with st.expander("Astrophysics Reference"):
        st.write("""
        * **Kessler Syndrome**: A cascade of collisions where debris creates even more debris[cite: 42, 43].
        * **TLE (Two-Line Element)**: A format used to track each object's orbital parameters[cite: 8, 9].
        * **Skyfield**: A library used for high-precision satellite positioning[cite: 9, 10].
        """)
