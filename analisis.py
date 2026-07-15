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
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path, delimiter=';', encoding='latin1')
    
    # Limpieza básica de coordenadas
    df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.').astype(float)
    df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.').astype(float)
    
    # Identificar columnas de bovinos de forma segura excluyendo años de control
    cols_bovinos = [
        c for c in df.columns 
        if 'AFTOSA_BOVINOS' in c 
        and not c.endswith('_AÑ_CONTROL') 
        and not c.endswith('_ANO_CONTROL')
    ]
    df[cols_bovinos] = df[cols_bovinos].fillna(0)
    df['TOTAL_BOVINOS'] = df[cols_bovinos].sum(axis=1)
    
    # Filtrar coordenadas válidas
    df = df[(df['LATITUD'] > 0) & (df['LONGITUD'] < 0)]
    
    return df

try:
    df = load_data(archivo_seleccionado)
except Exception as e:
    st.error(f"Error cargando el archivo '{archivo_seleccionado}': {e}")
    st.info("Asegúrate de que el archivo CSV esté en la misma carpeta que este script de Python.")
    st.stop()

# 3. BARRA LATERAL (FILTROS)
st.sidebar.header("Filtros de Visualización")
municipios_disponibles = sorted(df['MUNICIPIO'].dropna().unique())
municipio_filter = st.sidebar.multiselect(
    "Seleccionar Municipio:",
    options=municipios_disponibles,
    default=municipios_disponibles[:3] if len(municipios_disponibles) >= 3 else municipios_disponibles
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
    
    # --- MAPEADO ADAPTADO AL ARCHIVO 2025 ---
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
        'AFTOSA_BOVINOS_TERNEROS_MENORES_A_1_AÑ': 'Terneros < 1 año',
        'AFTOSA_BOVINOS_MACHOS_1___2_AÑO': '1-2 años',
        'AFTOSA_BOVINOS_MACHOS_2___3_AÑO': '2-3 años',
        'AFTOSA_BOVINOS_MACHOS_MAYORES_A_3_AÑO': '> 3 años'
    }

    orden_cronologico = [
        '0-3 meses', '< 3 meses',
        '3-8 meses',
        '8-12 meses', 'Terneros < 1 año',
        '1-2 años',
        '2-3 años',
        '3-5 años', '> 3 años',
        '> 5 años'
    ]

    datos_edad, datos_sexo, datos_poblacion = [], [], []

    # Procesar Hembras
    for col_name, etiqueta in mapa_hembras.items():
        if col_name in df_filtered.columns:
            total = df_filtered[col_name].sum()
            datos_edad.append(etiqueta)
            datos_sexo.append('Hembra')
            datos_poblacion.append(total)

    # Procesar Machos
    for col_name, etiqueta in mapa_machos.items():
        if col_name in df_filtered.columns:
            total = df_filtered[col_name].sum()
            datos_edad.append(etiqueta)
            datos_sexo.append('Macho')
            datos_poblacion.append(total)

    piramide_df = pd.DataFrame({
        'Edad': datos_edad,
        'Sexo': datos_sexo,
        'Poblacion': datos_poblacion
    })

    if not piramide_df.empty:
        categorias_existentes = [x for x in orden_cronologico if x in piramide_df['Edad'].unique()]
        piramide_df['Edad'] = pd.Categorical(piramide_df['Edad'], categories=categorias_existentes, ordered=True)
        piramide_df = piramide_df.sort_values('Edad')

        piramide_df_plot = piramide_df.copy()
        piramide_df_plot.loc[piramide_df_plot['Sexo'] == 'Macho', 'Poblacion'] *= -1
        
        fig_piramide = go.Figure()
        
        # Hembras
        df_h = piramide_df_plot[piramide_df_plot['Sexo'] == 'Hembra']
        fig_piramide.add_trace(go.Bar(
            y=df_h['Edad'], x=df_h['Poblacion'],
            orientation='h', name='Hembras', marker_color='#E91E63'
        ))
        
        # Machos
        df_m = piramide_df_plot[piramide_df_plot['Sexo'] == 'Macho']
        fig_piramide.add_trace(go.Bar(
            y=df_m['Edad'], x=df_m['Poblacion'],
            orientation='h', name='Machos', marker_color='#2196F3'
        ))
        
        max_val = piramide_df_plot['Poblacion'].abs().max()
        if pd.isna(max_val) or max_val == 0: max_val = 100

        fig_piramide.update_layout(
            title='Pirámide de Edad y Sexo (Ordenada por edad)',
            barmode='relative',
            xaxis=dict(title='Población', range=[-max_val*1.1, max_val*1.1]),
            yaxis=dict(type='category'),
            height=600,
            bargap=0.1
        )
        st.plotly_chart(fig_piramide, use_container_width=True)
    else:
        st.info("No hay datos de población suficientes para estructurar la pirámide.")
        
    st.markdown("---")
    st.subheader("2. Distribución de Población Bovina por Municipio")
    
    if not df_filtered.empty:
        top_munis = df_filtered.groupby('MUNICIPIO')['TOTAL_BOVINOS'].sum().sort_values(ascending=False).reset_index(name='Población Bovina') 
        fig_bar = px.bar(
            top_munis, x='Población Bovina', y='MUNICIPIO', orientation='h', 
            color='Población Bovina', color_continuous_scale='Viridis'
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.header("Vigilancia: Predios con Cero Bovinos")
    df_error = df_filtered[df_filtered['TOTAL_BOVINOS'] == 0]
    
    if not df_error.empty:
        st.warning(f"🚨 Se encontraron {len(df_error)} predios registrados con 0 animales.")
        fig_error = px.scatter_map(
            df_error, lat="LATITUD", lon="LONGITUD", color_discrete_sequence=["red"],
            zoom=9, height=500, title="Ubicación de Registros Anómalos (0 Animales)"
        )
        fig_error.update_layout(map_style="open-street-map")
        st.plotly_chart(fig_error, use_container_width=True)
        
        with st.expander("Ver tabla de datos anómalos"):
            # En el CSV de 2025 la columna es 'PREDIO' en lugar de 'NOMBRE_PREDIO'
            st.dataframe(df_error[['MUNICIPIO', 'VEREDA', 'GANADERO', 'PREDIO']])
    else:
        st.success("No se detectaron predios con 0 bovinos en los datos seleccionados.")

# Pie de página
st.markdown("---")
st.markdown("© 2025 Observatorio Epidemiológico - Desarrollado con Python y Streamlit")