import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests

st.set_page_config(page_title="Síntomas Respiratorios - SaluData", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1 { color: #003366; font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700; border-bottom: 2px solid #003366; padding-bottom: 10px; }
    h2, h3 { color: #004080; font-family: 'Helvetica Neue', Arial, sans-serif; }
    .info-box { background-color: #eef4f8; border-left: 4px solid #0056b3; padding: 12px 15px; margin-bottom: 20px; font-size: 0.95rem; }
    </style>
""", unsafe_allow_html=True)

st.title("Prevalencia de síntomas respiratorios sin gripa en menores de 5 años – enero a julio de 2025")

st.markdown("""
<div class="info-box">
    <strong>Observatorio de Salud de Bogotá (SaluData)</strong> — Encuesta periódica de salud en Bogotá, D.C.<br>
    <em>Indicador de prevalencia de síntomas respiratorios sin estar cursando un cuadro gripal en el período comprendido entre enero y julio de 2025.</em>
</div>
""", unsafe_allow_html=True)

@st.cache_data
def cargar_datos():
    try:
        df_salud = pd.read_csv("salud_limpio.csv")
        df_iboca = pd.read_csv("iboca_limpio.csv")
    except Exception as e:
        st.error(f"Error al cargar los archivos CSV: {e}")
        return pd.DataFrame(), pd.DataFrame(), None
    
    # Estandarizar nombres de columnas a mayúsculas
    df_salud.columns = df_salud.columns.str.strip().str.upper()
    df_iboca.columns = df_iboca.columns.str.strip().str.upper()

    # Cargar GeoJSON de Bogotá de forma segura
    geojson = None
    try:
        url = "https://raw.githubusercontent.com/gongora2/bogota_geojson/master/localidades.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            geojson = res.json()
    except:
        geojson = None
        
    return df_salud, df_iboca, geojson

df_salud, df_iboca, geojson_bogota = cargar_datos()

if df_salud.empty:
    st.warning("Por favor asegúrate de tener 'salud_limpio.csv' e 'iboca_limpio.csv' en la misma carpeta.")
    st.stop()

# Filtros por Localidad
listado_loc = ["Todas las localidades"] + sorted(list(df_salud['LOCALIDAD'].dropna().unique()))
loc_sel = st.selectbox("Seleccione Localidad para filtrar el dashboard:", listado_loc)

df_salud_filt = df_salud[df_salud['LOCALIDAD'] == loc_sel] if loc_sel != "Todas las localidades" else df_salud.copy()

# Agrupación general por localidad
df_loc_salud = df_salud.groupby('LOCALIDAD', as_index=False).agg(
    total_encuestados=('NINOS_ENCUESTADOS', 'sum'),
    total_sintomas=('CASOS_SIN_GRIPA', 'sum')
)
df_loc_salud['Prevalencia_%'] = np.where(df_loc_salud['total_encuestados'] > 0, (df_loc_salud['total_sintomas'] / df_loc_salud['total_encuestados']) * 100, 0)
df_loc_salud['Prevalencia_%'] = df_loc_salud['Prevalencia_%'].round(2)

# Métricas principales
c1, c2, c3 = st.columns(3)
t_enc = int(df_salud_filt['NINOS_ENCUESTADOS'].sum())
t_sint = int(df_salud_filt['CASOS_SIN_GRIPA'].sum())
prev = (t_sint / t_enc * 100) if t_enc > 0 else 0
c1.metric("Niños Encuestados", f"{t_enc:,}")
c2.metric("Con Síntomas Sin Gripa", f"{t_sint:,}")
c3.metric("Prevalencia Calculada", f"{prev:.2f}%")

st.divider()

# Sección 1: Mapa y Caracterización
st.header("1. Dashboard de síntomas respiratorios sin gripa")
col_map, col_car = st.columns([1.2, 1])

with col_map:
    st.subheader("Mapa por Localidades")
    if geojson_bogota:
        fig1 = px.choropleth_mapbox(
            df_loc_salud, geojson=geojson_bogota, locations='LOCALIDAD',
            featureidkey="properties.Nombre", color='Prevalencia_%',
            color_continuous_scale="YlOrRd", mapbox_style="carto-positron",
            zoom=9.3, center={"lat": 4.63, "lon": -74.08}, hover_name='LOCALIDAD',
            hover_data={'total_encuestados': True, 'total_sintomas': True, 'Prevalencia_%': ':.2f'}
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Mapa no disponible temporalmente por red; mostrando tabla resumen:")
        st.dataframe(df_loc_salud, use_container_width=True)

with col_car:
    st.subheader("Caracterización de Menores")
    f_sex = px.pie(df_salud_filt.groupby('SEXO', as_index=False)['CASOS_SIN_GRIPA'].sum(),
                   values='CASOS_SIN_GRIPA', names='SEXO', title="1. Sexo")
    st.plotly_chart(f_sex, use_container_width=True)
    
    f_sgss = px.bar(df_salud_filt.groupby('ASEGURAMIENTO', as_index=False)['CASOS_SIN_GRIPA'].sum(),
                    x='ASEGURAMIENTO', y='CASOS_SIN_GRIPA', title="2. Recibe atención en salud (SGSS)")
    st.plotly_chart(f_sgss, use_container_width=True)
    
    f_est = px.bar(df_salud_filt.groupby('ESTRATO', as_index=False)['CASOS_SIN_GRIPA'].sum(),
                   x='ESTRATO', y='CASOS_SIN_GRIPA', title="3. Estrato Socioeconómico")
    st.plotly_chart(f_est, use_container_width=True)

st.divider()

# Sección 2: Mapa de Calidad del Aire (PM2.5)
st.header("2. Dashboard de PM2.5 y comparación con síntomas respiratorios")

# Normalizar columna LOCALIDAD en ambos datasets para asegurar el merge
df_loc_salud['LOCALIDAD'] = df_loc_salud['LOCALIDAD'].astype(str).str.strip().str.upper()
df_iboca['LOCALIDAD'] = df_iboca['LOCALIDAD'].astype(str).str.strip().str.upper()

df_mapa_iboca = pd.merge(df_loc_salud, df_iboca, on='LOCALIDAD', how='left')

if geojson_bogota:
    fig2 = px.choropleth_mapbox(
        df_mapa_iboca, geojson=geojson_bogota, locations='LOCALIDAD',
        featureidkey="properties.Nombre", color='PM25_PROMEDIO',
        color_continuous_scale="Reds", mapbox_style="carto-positron",
        zoom=9.3, center={"lat": 4.63, "lon": -74.08}, hover_name='LOCALIDAD',
        hover_data={'PM25_PROMEDIO': ':.2f', 'total_encuestados': True, 'total_sintomas': True, 'Prevalencia_%': ':.2f'}
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.dataframe(df_mapa_iboca[['LOCALIDAD', 'PM25_PROMEDIO', 'Prevalencia_%']], use_container_width=True)

st.divider()

# Sección 3: Correlación Analítica
st.header("3. Relación entre PM2.5 y síntomas respiratorios")
df_an = df_mapa_iboca.dropna(subset=['PM25_PROMEDIO', 'Prevalencia_%'])

if not df_an.empty:
    fig_scat = px.scatter(
        df_an, x='PM25_PROMEDIO', y='Prevalencia_%', text='LOCALIDAD',
        title="Concentración PM2.5 vs Prevalencia de Síntomas",
        labels={'PM25_PROMEDIO': 'PM2.5 Promedio (µg/m³)', 'Prevalencia_%': 'Prevalencia Síntomas (%)'}
    )
    fig_scat.update_traces(textposition='top center', marker=dict(size=10, color='#003366'))
    st.plotly_chart(fig_scat, use_container_width=True)
    
    corr_sp = df_an['PM25_PROMEDIO'].corr(df_an['Prevalencia_%'], method='spearman')
    st.info(f"**Coeficiente de Spearman:** {corr_sp:.3f}")
    st.markdown("Se evidencia una **tendencia o asociación observada** positiva entre las zonas con mayor concentración de PM2.5 y una mayor prevalencia de síntomas respiratorios sin gripa. *Nota: Esta asociación no demuestra relación directa de causalidad.*")