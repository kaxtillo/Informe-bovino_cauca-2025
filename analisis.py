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

# Nombre fijo del archivo
archivo_datos = 'Ruv Total Cauca II 2025.csv'

# 2. CARGA DE DATOS (Con caché para velocidad)
@st.cache_data
def load_data(file_path):
    try:
        # Intentamos leer con UTF-8
        df = pd.read_csv(file_path, delimiter=';', encoding='utf-8', skip_blank_lines=True)
    except Exception:
        # Fallback a Latin-1 si UTF-8 falla
        df = pd.read_csv(file_path, delimiter=';', encoding='latin1', skip_blank_lines=True)
    
    # 1. Limpieza absoluta de nombres de columnas (eliminar espacios y saltos de línea invisibles)
    df.columns = df.columns.str.strip().str.replace('\r', '').str.replace('\n', '')
    df.columns = [col.replace('ï»¿', '') for col in df.columns]
    
    # 2. NORMALIZAR CARACTERES EXTRAÑOS (Corrige las tildes y las Ñ deformadas)
    # Reemplaza cualquier variante deformada de "AÑO", "AÑOS" o "VACUNACIÓN" por su formato estándar
    nuevas_columnas = []
    for col in df.columns:
        col_limpia = col
        col_limpia = col_limpia.replace('AÃ‘O', 'AÑO').replace('AÃ\x91O', 'AÑO')
        col_limpia = col_limpia.replace('AÃ‘OS', 'AÑO').replace('AÃ\x91OS', 'AÑO')
        col_limpia = col_limpia.replace('AÃ‘', 'AÑ').replace('AÃ\x91', 'AÑ')
        col_limpia = col_limpia.replace('AÃ\x91', 'AÑ')
        col_limpia = col_limpia.replace('VACUNACIÃ\x93N', 'VACUNACIÓN')
        nuevas_columnas.append(col_limpia)
    df.columns = nuevas_columnas
    
    # 3. Eliminar filas vacías
    df = df.dropna(subset=['MUNICIPIO'], how='all')
    
    # 4. Procesar LATITUD de forma segura
    if 'LATITUD' in df.columns:
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.').str.strip()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
    else:
        st.error(f"La columna 'LATITUD' no se encontró. Columnas disponibles: {list(df.columns)}")
        st.stop()
        
    # 5. Procesar LONGITUD de forma segura
    if 'LONGITUD' in df.columns:
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.').str.strip()
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
    else:
        st.error(f"La columna 'LONGITUD' no se encontró. Columnas disponibles: {list(df.columns)}")
        st.stop()
    
    # 6. OPCIÓN A: Cargar directamente la columna nativa del CSV para evitar duplicidades
    if 'TOTAL_ANIMALES_AFTOSA'
    else:
        st.error("No se encontró la columna oficial 'TOTAL_ANIMALES_AFTOSA' en el archivo CSV.")
        st.stop()
        
    # Limpiar también las columnas individuales de bovinos para la pirámide (para que no tengan NaN)
    cols_bovinos = [
        c for c in df.columns 
        if 'AFTOSA_BOVINOS' in c 
        and not c.endswith('_AÑ_CONTROL') 
        and not c.endswith('_ANO_CONTROL')
        and not c.endswith('_NV')
        and not c.endswith('_N')
    ]
    df[cols_bovinos] = df[cols_bovinos].fillna(0)
    
    # Filtrar coordenadas válidas
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
    st.info("Por favor, verifica que el archivo esté subido correctamente a GitHub.")

# --- SOLO EJECUTAR SI EL DATAFRAME SE CARGÓ CORRECTAMENTE ---
if df is not None:

    # 3. BARRA LATERAL (FILTROS)
    st.sidebar.header("Filtros de Análisis")
    municipios_disponibles = sorted(df['MUNICIPIO'].dropna().unique())
    municipio_filter = st.sidebar.multiselect(
        "Seleccionar Municipio(s):",
        options=municipios_disponibles,
        default=municipios_disponibles[:3] if len(municipios_disponibles) >= 3 else municipios_disponibles,
        help="Selecciona uno o varios municipios para filtrar todo el observatorio."
    )

    # Aplicar filtro
    if municipio_filter:
        df_filtered = df[df['MUNICIPIO'].isin(municipio_filter)]
    else:
        df_filtered = df

    # 4. KPIs (INDICADORES CLAVE - TOTAL_ANIMALES_AFTOSA oficial)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Predios Filtrados", f"{len(df_filtered):,}")
    col2.metric("Población Bovina", f"{int(df_filtered['TOTAL_ANIMALES_AFTOSA'].sum()):,}")
    promedio = df_filtered['TOTAL_ANIMALES_AFTOSA'].mean() if len(df_filtered) > 0 else 0
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
                
                # Identificar dinámicamente el nombre de la columna de predio
                col_predio = 'PREDIO' if 'PREDIO' in df_filtered.columns else ('NOMBRE_PREDIO' if 'NOMBRE_PREDIO' in df_filtered.columns else df_filtered.columns[3])
                
                # Configurar el mapa de dispersión para mostrar el predio en el hover
                fig_scatter = px.scatter_map(
                    df_filtered, 
                    lat="LATITUD", 
                    lon="LONGITUD", 
                    color="MUNICIPIO", 
                    size="TOTAL_ANIMALES_AFTOSA",
                    hover_name=col_predio,  # Muestra el nombre del predio al pasar el mouse
                    hover_data={
                        "MUNICIPIO": True,
                        "VEREDA": True,
                        "GANADERO": True,
                        "TOTAL_ANIMALES_AFTOSA": ":,.0f",  # Formatea con separador de miles
                        "LATITUD": False,
                        "LONGITUD": False
                    },
                    zoom=8, 
                    height=500
                )
                fig_scatter.update_layout(map_style="open-street-map")
                st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("No hay datos geográficos para mostrar con los filtros actuales.")

    with tab2:
        st.header("Análisis de la Estructura del Hato Ganadero")
        st.subheader("1. Pirámide Poblacional Bovina (Edad y Sexo)")
        
        # Mapeos de columnas unificando etiquetas a los 7 rangos
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
            'AFTOSA_BOVINOS_MACHOS_MENORES_A_3_MESES': '0-3 meses', 
            'AFTOSA_BOVINOS_MACHOS_3_HASTA_8_MESES': '3-8 meses',
            'AFTOSA_BOVINOS_MACHOS_8_HASTA_12_MESES': '8-12 meses',
            'AFTOSA_BOVINOS_TERNEROS_MENORES_A_1_AÑ': '8-12 meses',
            'AFTOSA_BOVINOS_MACHOS_1___2_AÑO': '1-2 años',
            'AFTOSA_BOVINOS_MACHOS_2___3_AÑO': '2-3 años',
            'AFTOSA_BOVINOS_MACHOS_MAYORES_A_3_AÑO': '3-5 años'
        }

        # El orden estricto solicitado
        orden_estricto = [
            '0-3 meses',
            '3-8 meses',
            '8-12 meses',
            '1-2 años',
            '2-3 años',
            '3-5 años',
            '> 5 años'
        ]

        datos_edad, datos_sexo, datos_poblacion = [], [], []

        for col_name, etiqueta in mapa_hembras.items():
            if col_name in df_filtered.columns:
                total = df_filtered[col_name].sum()
                datos_edad.append(etiqueta)
                datos_sexo.append('Hembra')
                datos_poblacion.append(total)

        for col_name, etiqueta in mapa_machos.items():
            if col_name in df_filtered.columns:
                total = df_filtered[col_name].sum()
                datos_edad.append(etiqueta)
                datos_sexo.append('Macho')
                datos_poblacion.append(total)

        piramide_raw = pd.DataFrame({
            'Edad': datos_edad,
            'Sexo': datos_sexo,
            'Poblacion': datos_poblacion
        })

        piramide_df = piramide_raw.groupby(['Edad', 'Sexo'], as_index=False)['Poblacion'].sum()

        if not piramide_df.empty and piramide_df['Poblacion'].sum() > 0:
            categorias_existentes = [x for x in orden_estricto if x in piramide_df['Edad'].unique()]
            piramide_df['Edad'] = pd.Categorical(piramide_df['Edad'], categories=categorias_existentes, ordered=True)
            piramide_df = piramide_df.sort_values('Edad')

            piramide_df_plot = piramide_df.copy()
            piramide_df_plot.loc[piramide_df_plot['Sexo'] == 'Macho', 'Poblacion'] *= -1
            
            fig_piramide = go.Figure()
            
            df_h = piramide_df_plot[piramide_df_plot['Sexo'] == 'Hembra']
            fig_piramide.add_trace(go.Bar(
                y=df_h['Edad'], x=df_h['Poblacion'],
                orientation='h', name='Hembras', marker_color='#E91E63',
                hovertemplate="Edad: %{y}<br>Hembras: %{x:,.0f}<extra></extra>"
            ))
            
            df_m = piramide_df_plot[piramide_df_plot['Sexo'] == 'Macho']
            fig_piramide.add_trace(go.Bar(
                y=df_m['Edad'], x=df_m['Poblacion'],
                orientation='h', name='Machos', marker_color='#2196F3',
                hovertemplate="Edad: %{y}<br>Machos: %{customdata:,.0f}<extra></extra>",
                customdata=df_m['Poblacion'].abs()
            ))
            
            max_val = piramide_df_plot['Poblacion'].abs().max()
            if pd.isna(max_val) or max_val == 0: max_val = 100

            ticks_valores = list(range(int(-max_val), int(max_val), max(1, int(max_val // 5))))
            ticks_textos = [f"{abs(v):,}" for v in ticks_valores]

            fig_piramide.update_layout(
                title='Pirámide Poblacional de Edad y Sexo (Ciclo II 2025)',
                barmode='relative',
                xaxis=dict(
                    title='Número de Animales',
                    tickvals=ticks_valores,
                    ticktext=ticks_textos,
                    range=[-max_val * 1.1, max_val * 1.1]
                ),
                yaxis=dict(type='category', title='Rango de Edad'),
                height=600,
                bargap=0.1
            )
            st.plotly_chart(fig_piramide, use_container_width=True)
        else:
            st.warning("No hay datos de población suficientes para estructurar la pirámide.")
            
        st.markdown("---")
        st.subheader("2. Distribución de Población Bovina por Municipio")
        
        if not df_filtered.empty:
            top_munis = df_filtered.groupby('MUNICIPIO')['TOTAL_ANIMALES_AFTOSA'].sum().sort_values(ascending=False).reset_index(name='Población Bovina') 
            fig_bar = px.bar(
                top_munis, x='Población Bovina', y='MUNICIPIO', orientation='h', 
                color='Población Bovina', color_continuous_scale='Viridis'
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.header("Vigilancia: Predios con Cero Bovinos")
        
        # Filtramos predios registrados que registren exactamente 0 animales usando TOTAL_ANIMALES_AFTOSA oficial
        df_error = df_filtered[df_filtered['TOTAL_ANIMALES_AFTOSA'] == 0]
        
        if not df_error.empty:
            st.warning(f"🚨 Se encontraron {len(df_error)} predios registrados con 0 animales vacunados para Aftosa.")
            
            # Identificar dinámicamente el nombre de la columna de predio
            col_predio = 'PREDIO' if 'PREDIO' in df_error.columns else ('NOMBRE_PREDIO' if 'NOMBRE_PREDIO' in df_error.columns else df_error.columns[3])
            
            fig_error = px.scatter_map(
                df_error, 
                lat="LATITUD", 
                lon="LONGITUD", 
                color_discrete_sequence=["red"],
                hover_name=col_predio,
                hover_data={
                    "MUNICIPIO": True, 
                    "VEREDA": True, 
                    "GANADERO": True,
                    "LATITUD": False,
                    "LONGITUD": False
                },
                zoom=9, 
                height=500, 
                title="Ubicación de Registros Anómalos (0 Animales)"
            )
            fig_error.update_layout(map_style="open-street-map")
            st.plotly_chart(fig_error, use_container_width=True)
            
            with st.expander("Ver tabla de datos anómalos"):
                st.dataframe(df_error[['MUNICIPIO', 'VEREDA', 'GANADERO', col_predio]])
        else:
            st.success("No se detectaron predios con 0 bovinos vacunados en los datos de los municipios seleccionados.")

    # Pie de página
    st.markdown("---")
    st.markdown("© 2025 Observatorio Epidemiológico - Desarrollado con Python y Streamlit")
else:
    st.warning("⚠️ La aplicación no puede continuar porque no se cargaron datos válidos.")
