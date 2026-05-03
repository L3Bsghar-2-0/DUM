from __future__ import annotations
import json
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "extractor"))
from db import read_all_records
from forecast import generate_forecast

DB_URL = os.getenv("DB_URL", "sqlite:///data/db/energy.db")
_engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

st.set_page_config(page_title="Energy Dashboard", layout="wide", page_icon="⚡")
st.title("⚡ Pharmaceutical Factory — Energy Analytics")


@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    df = read_all_records(_engine)
    if df.empty:
        return df
    if 'extraction_warnings' in df.columns:
        df['extraction_warnings'] = df['extraction_warnings'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else []
        )
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp')
    return df


df = load_data()

if df.empty:
    st.warning("No data loaded yet. Run the pipeline first.")
    st.stop()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 KPIs", "🌿 CO2 Trend", "🚨 Anomalies", "📋 Data Table", "🔍 Coverage", "📈 Forecast"
])

# --- TAB 1: KPIs ---
with tab1:
    excel_df = df[df['source_type'] == 'excel']
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        total_co2 = df['co2_kg'].sum() / 1000 if 'co2_kg' in df.columns else 0
        st.metric("Total CO2", f"{total_co2:.1f} tCO2")
    with col2:
        avg_power = excel_df['puissance_brute_kw'].mean() if not excel_df.empty else 0
        st.metric("Avg Power", f"{avg_power:.0f} kW")
    with col3:
        avg_eff = excel_df['rendement_electrique_pct'].mean() if not excel_df.empty else 0
        st.metric("Avg Elec Efficiency", f"{avg_eff:.1f} %")
    with col4:
        anomalies = int(df['is_anomaly'].sum())
        st.metric("Anomalies Detected", anomalies)
    with col5:
        avg_conf = df['confidence_score'].mean()
        st.metric("Avg Confidence", f"{avg_conf:.0%}")

    if not excel_df.empty and 'timestamp' in excel_df.columns:
        st.subheader("Electrical Power Output Over Time")
        fig = px.line(
            excel_df.dropna(subset=['timestamp', 'puissance_brute_kw']),
            x='timestamp', y='puissance_brute_kw',
            title='Puissance Brute (kW)', labels={'puissance_brute_kw': 'kW'}
        )
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            fig2 = px.line(
                excel_df.dropna(subset=['timestamp', 'gaz_debit_nm3h']),
                x='timestamp', y='gaz_debit_nm3h',
                title='Gas Flow (Nm3/h)'
            )
            st.plotly_chart(fig2, use_container_width=True)
        with col_b:
            fig3 = px.line(
                excel_df.dropna(subset=['timestamp', 'rendement_electrique_pct']),
                x='timestamp', y='rendement_electrique_pct',
                title='Electrical Efficiency (%)'
            )
            st.plotly_chart(fig3, use_container_width=True)

# --- TAB 2: CO2 Trend ---
with tab2:
    co2_df = df.dropna(subset=['co2_kg'])
    if not co2_df.empty and 'timestamp' in co2_df.columns:
        co2_df = co2_df.dropna(subset=['timestamp'])
        daily = co2_df.set_index('timestamp').resample('D')['co2_kg'].sum().reset_index()
        daily['co2_tonne'] = daily['co2_kg'] / 1000
        fig = px.line(daily, x='timestamp', y='co2_tonne',
                      title='Daily CO2 Emissions (tCO2)',
                      labels={'co2_tonne': 'tCO2', 'timestamp': 'Date'})
        fig.add_hline(y=daily['co2_tonne'].mean(), line_dash="dash",
                      annotation_text="Average")
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            total_elec_co2 = co2_df['energie_alternateur_kwh'].dropna().sum() * 0.267 / 1000
            total_gas_co2 = (
                co2_df['gaz_volume_nm3'].dropna().sum() * 9.082 * 1.163 * 0.202 / 1000
            )
            fig_pie = px.pie(
                values=[total_elec_co2, total_gas_co2],
                names=['Electricity (STEG)', 'Natural Gas'],
                title='CO2 by Source'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            st.metric("Total CO2 Emitted", f"{co2_df['co2_kg'].sum() / 1000:.1f} tCO2")
            st.metric("Electricity CO2", f"{total_elec_co2:.1f} tCO2")
            st.metric("Gas CO2", f"{total_gas_co2:.1f} tCO2")
    else:
        st.info("No CO2 data available yet.")

# --- TAB 3: Anomalies ---
with tab3:
    anomaly_df = df[df['is_anomaly'] == True]
    st.metric("Total Anomalies", len(anomaly_df))

    if not anomaly_df.empty:
        type_counts = anomaly_df['anomaly_type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Count']
        fig = px.bar(type_counts, x='Type', y='Count', title='Anomalies by Type',
                     color='Type')
        st.plotly_chart(fig, use_container_width=True)

        cols_show = ['timestamp', 'source_file', 'site', 'anomaly_type',
                     'puissance_brute_kw', 'gaz_debit_nm3h', 'anomaly_confidence']
        cols_show = [c for c in cols_show if c in anomaly_df.columns]
        st.dataframe(
            anomaly_df[cols_show].head(200),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No anomalies detected!")

# --- TAB 4: Data Table ---
with tab4:
    sources = ['All'] + sorted(df['source_type'].unique().tolist())
    selected = st.selectbox("Filter by source type", sources)
    filtered = df if selected == 'All' else df[df['source_type'] == selected]

    if 'timestamp' in filtered.columns:
        min_d = filtered['timestamp'].dropna().min()
        max_d = filtered['timestamp'].dropna().max()
        if pd.notna(min_d) and pd.notna(max_d):
            date_range = st.date_input("Date range", [min_d, max_d])
            if len(date_range) == 2:
                filtered = filtered[
                    (filtered['timestamp'] >= pd.Timestamp(date_range[0])) &
                    (filtered['timestamp'] <= pd.Timestamp(date_range[1]))
                ]

    st.write(f"Showing {len(filtered):,} records")

    display_cols = [
        'timestamp', 'source_file', 'source_type', 'confidence_score',
        'puissance_brute_kw', 'gaz_debit_nm3h', 'eg_puissance_kw',
        'co2_kg', 'is_anomaly', 'anomaly_type'
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].head(500),
        use_container_width=True,
        hide_index=True,
    )

# --- TAB 5: Coverage ---
with tab5:
    st.subheader("Extraction Coverage by Source File")
    coverage = df.groupby('source_file').agg(
        records=('id', 'count'),
        avg_confidence=('confidence_score', 'mean'),
        anomalies=('is_anomaly', 'sum'),
    ).reset_index().sort_values('avg_confidence', ascending=False)
    fig = px.bar(coverage, x='source_file', y='avg_confidence',
                 color='avg_confidence', color_continuous_scale='RdYlGn',
                 title='Confidence Score by Source File',
                 labels={'avg_confidence': 'Confidence', 'source_file': 'File'})
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(coverage, use_container_width=True, hide_index=True)

    st.subheader("Files with Extraction Warnings")
    if 'extraction_warnings' in df.columns:
        with_warnings = df[df['extraction_warnings'].apply(
            lambda x: isinstance(x, list) and len(x) > 0
        )][['source_file', 'extraction_warnings']].drop_duplicates('source_file').head(20)
        if not with_warnings.empty:
            st.dataframe(with_warnings, use_container_width=True, hide_index=True)
        else:
            st.success("No extraction warnings!")

# --- TAB 6: Forecast ---
with tab6:
    st.subheader("24-Hour Energy Trend Forecasting")
    st.write("Using Random Forest ML model on historical data to predict future consumption.")
    
    with st.spinner("Generating forecast..."):
        try:
            future_df = generate_forecast(df, horizon_hours=24)
            if not future_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_pow = px.line(
                        future_df, x='timestamp', y='pred_puissance_brute_kw',
                        title='Predicted Power Demand (kW)',
                        labels={'pred_puissance_brute_kw': 'Predicted kW'}
                    )
                    fig_pow.update_traces(line_color='orange')
                    st.plotly_chart(fig_pow, use_container_width=True)
                
                with col2:
                    if 'pred_co2_kg' in future_df.columns:
                        fig_co2 = px.line(
                            future_df, x='timestamp', y='pred_co2_kg',
                            title='Predicted CO2 Emissions (kg)',
                            labels={'pred_co2_kg': 'Predicted CO2 (kg)'}
                        )
                        fig_co2.update_traces(line_color='red')
                        st.plotly_chart(fig_co2, use_container_width=True)
                
                st.dataframe(future_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Not enough historical data to generate a forecast.")
        except Exception as e:
            st.error(f"Error generating forecast: {e}")
