import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap
import os

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Observatorio Epidemiológico Cauca", layout="wide", page_icon="🐄")

# --- Configuración de Datos ---
st.sidebar.header("Configuración de Datos")

# Nombre del archivo fijo o dinámico si existen más
archivo_predeterminado = 'Ruv Total Cauca II 2025.csv'
archivos_disponibles = [f for f in os.listdir('.') if f.endswith('.csv')]

if archivo_predeterminado in archivos_disponibles:
    archivo_seleccionado = st.sidebar.selectbox(
        "Seleccione el archivo de datos:",
        options=archivos_disponibles,
        index=archivos_disponibles.index(archivo_predeterminado)
    )
else:
    archivo_seleccionado = st.sidebar.selectbox(
        "Seleccione el archivo de datos:",
        options=archivos_disponibles if archivos_disponibles else [archivo_predeterminado],
        index=0
    )

# Título dinámico
st.title("🐄 Observatorio de Vigilancia Vacunación - Cauca - 2025")
st.markdown("Análisis de datos de vacunación bovina - Ciclo II 2025")

# 2. CARGA DE DATOS (Con caché para velocidad)
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
    df = load_data(archivo_seleccionado)
except Exception as e:
    st.error(f"❌ Error crítico al procesar el archivo '{archivo_seleccionado}':")
    st.exception(e)  # <-- Esto nos mostrará el detalle exacto del error en la web de Streamlit
    st.info("Por favor, verifica que el archivo esté subido correctamente a GitHub con el mismo nombre.")
