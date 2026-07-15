import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Observatorio Epidemiológico Cauca", layout="wide", page_icon="🐄")

# Título de la Aplicación
st.title("🐄 Observatorio de Vigilancia Vacunación - Cauca - 2025")
st.markdown("Análisis de datos de vacunación bovina - Ciclo II 2025")

# Nombre fijo del archivo para evitar selectores innecesarios
archivo_datos = 'Ruv Total Cauca II 2025.csv'

# 2. CARGA DE DATOS (Con caché para velocidad)
@st.cache_data
def load_data(file_path):
    # Intentar leer con utf-8-sig (para limpiar el BOM ï»¿)
    try:
        df = pd.read_csv(file_path, delimiter=';', encoding='utf-8-sig', skip_blank_lines=True)
    except Exception:
        # Si falla utf-8-sig, intentamos con latin1
        df = pd.read_csv(file_path, delimiter=';', encoding='latin1', skip_blank_lines=True)
    
    # Limpieza absoluta de nombres de columnas (elimina espacios y saltos de línea invisibles)
    df.columns = df.columns.str.strip().str.replace('\r', '').str.replace('\n', '')
    
    # Curación extra por si el BOM persiste de forma literal
    df.columns = [col.replace('ï»¿', '') for col in df.columns]
    
    # Eliminar filas del final del CSV que solo contienen puntos y comas (sin datos reales)
    df = df.dropna(subset=['MUNICIPIO'], how='all')
    
    # Procesar LATITUD de forma segura
    if 'LATITUD' in df.columns:
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.').str.strip()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
    else:
        st.error(f"La columna 'LATITUD' no se encontró. Columnas disponibles: {list(df.columns)}")
        st.stop()
        
    # Procesar LONGITUD de forma segura
    if 'LONGITUD' in df.columns:
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.').str.strip()
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
    else:
        st.error(f"La columna 'LONGITUD' no se encontró. Columnas disponibles: {list(df.columns)}")
        st.stop()
    
    # Identificar columnas de bovinos de forma segura
    cols_bovinos = [
        c for c in df.columns 
        if 'AFTOSA_BOVINOS' in c 
        and not c.endswith('_AÑ_CONTROL') 
        and not c.endswith('_ANO_CONTROL')
    ]
    df[cols_bovinos] = df[cols_bovinos].fillna(0)
    df['TOTAL_BOVINOS'] = df[cols_bovinos].sum(axis=1)
    
    # Filtrar coordenadas válidas (distintas de cero y que no sean nulas)
    df = df.dropna(subset=['LATITUD', 'LONGITUD'])
    df = df[(df['LATITUD'] != 0) & (df['LONGITUD'] != 0)]
    
    return df

# --- INICIALIZACIÓN SEGURA ---
df = None

try:
    df = load_data(archivo_datos)
except Exception as e:
    st.error(f"❌ Error crítico al procesar el archivo '{archivo_datos}':")
    st.exception(e)
    st.info("Por favor, verifica que el archivo esté subido correctamente a GitHub con el mismo nombre.")

# --- SOLO EJECUTAR SI EL DATAFRAME SE CARGÓ CORRECTAMENTE ---
if df is not None:

    # 3. BARRA LATERAL (ÚNICAMENTE FILTRO DE MUNICIPIOS)
    st.sidebar.header("Filtros de Análisis")
    municipios_disponibles = sorted(df['MUNICIPIO'].dropna().unique())
    municipio_filter = st.sidebar.multiselect(
        "Seleccionar Municipio(s):",
        options=municipios_disponibles,
        default=municipios_disponibles[:3] if len(municipios_disponibles) >= 3 else municipios_disponibles,
        help="Selecciona uno o varios municipios para filtrar todos los datos del observatorio."
    )

    # Aplicar filtro
    if municipio_filter:
        df_filtered = df[df['MUNICIPIO'].isin(municipio_filter)]
    else:
        df_filtered = df

    # 4. KPIs (INDICADORES CLAVE)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Predios Filtrados", f"{len(df_filtered):,}")
    col2.metric("Población Bovina", f"{int(df_filtered['TOTAL_BOVINOS'].sum()):,}")
    promedio = df_filtered['TOTAL_BOVINOS'].mean() if len(df_filtered) > 0 else 0
    col3.metric("Promedio Animales/Predio", f"{promedio:.1f}")

    # 5. PESTAÑAS DE ANÁLISIS
    tab1, tab2, tab3 = st.tabs(["🗺️ Mapas Interactivos", "📊 Demografía y Vocación", "🚨 Detección de Anomalías"])

    with tab1:
        st.header("Distribución Geoespacial")
        if not df_filtered.empty:
            col_map1, col_map2 = st.columns(2)
            
            with col_map1:
                st.subheader("Mapa de Calor (Densidad)")
                m = folium.Map(location=[df_filtered['LATITUD'].mean(), df_filtered['LONGITUD'].mean()], zoom_start=9)
                heat_data = df_filtered[['LATITUD', 'LONGITUD']].values.tolist()
                HeatMap(heat_data, radius=10).add_to(m)
                st_folium(m, height=500, use_container_width=True)
                
            with col_map2:
                st.subheader("Distribución por Tamaño del Hato")
                fig_scatter = px.scatter_map(
                    df_filtered, lat="LATITUD", lon="LONGITUD", color="MUNICIPIO", size="TOTAL_BOVINOS",
                    zoom=8, height=500
                )
                fig_scatter.update_layout(map_style="open-street-map")
                st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("No hay datos geográficos para mostrar con los filtros actuales.")

    with tab2:
        st.header("Análisis de la Estructura del Hato Ganadero")
        st.subheader("1. Pirámide Poblacional Bovina (Edad y Sexo)")
        
        mapa_hembras = {
            'AFTOSA_BOVINOS_HEMBRAS_MENORES_A_3_MESES': '0-3 meses',
            'AFTOSA_BOVINOS_HEMBRAS_MENORES_DE_3_A_8_MESES': '3-8 meses',
            'AFTOSA_BOVINOS_DE_8_A_12_MESES': '8-12 meses',
            'AFTOSA_BOVINOS_HEMBRAS_1___2_AÑO': '1-2 años',
            'AFTOSA_BOVINOS_HEMBRAS_2___3_AÑO': '2-3 años',
            'AFTOSA_BOVINOS_HEMBRAS_3___5_AÑO': '3-5 años',
            'AFTOSA_BOVINOS_HEMBRAS_MAYORES_A_5_AÑO': '> 5 años'
        }

        mapa_machos = {
            'AFTOSA_BOVINOS_MACHOS_MENORES_A_3_MESES': '< 3 meses', 
            'AFTOSA_BOVINOS_MACHOS_3_HASTA_8_MESES': '3-8 meses',
            'AFTOSA_BOVINOS_MACHOS_8_HASTA_12_MESES': '8-12 meses',
            'AFTOSA_BOVINOS_TER
