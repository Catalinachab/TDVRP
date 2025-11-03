"""
TDVRP Analyzer - Herramienta de Análisis Interactiva
Tesis TD8: Problema de Ruteo de Vehículos Dependiente del Tiempo

Aplicación web para visualizar y evaluar soluciones óptimas de TDVRP
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import pandas as pd
import io
import json

# Importar nuestro motor de análisis
import tdvrp_analyzer as core

# ============= CONFIGURACIÓN DE LA PÁGINA =============
st.set_page_config(
    page_title="TDVRP Analyzer",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= ESTILOS CUSTOM =============
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# ============= HEADER =============
st.markdown('<p class="main-header">🚛 TDVRP Analyzer</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Análisis de Soluciones Óptimas para Problemas de Ruteo Dependientes del Tiempo</p>',
    unsafe_allow_html=True
)

st.markdown("""
**Objetivo**: Validar la hipótesis de que las soluciones óptimas tienden a elegir arcos 
cuya duración está próxima al mínimo posible dentro del conjunto de arcos factibles.
""")

st.divider()

# ============= SIDEBAR: CARGA DE DATOS =============
with st.sidebar:
    st.header("📁 Carga de Datos")
    
    st.markdown("""
    **Instrucciones**:
    1. Carga las **instancias** como archivo `.zip` con archivos `.json`
    2. Carga las **soluciones** como un único archivo `solutions.json`
    """)
    
    # Cargador de instancias (ZIP)
    instances_file = st.file_uploader(
        "📦 Instancias (ZIP)",
        type=['zip'],
        help="Archivo .zip con archivos .json de instancias (ej: C101_25.json, C102_25.json)"
    )
    
    # Cargador de soluciones (JSON)
    solutions_file = st.file_uploader(
        "📄 Soluciones (JSON)",
        type=['json'],
        help="Archivo solutions.json con lista de soluciones"
    )
    
    st.divider()
    
    # Parámetros de análisis
    st.header("⚙️ Parámetros")
    epsilon = st.slider(
        "Epsilon (tolerancia temporal)",
        min_value=0.0,
        max_value=5000.0,
        value=0.0,
        step=1.0,
        help="Diferencia ±t para calcular intervalos"
    )
    
    cant_muestras = st.slider(
        "Cantidad de muestras",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
        help="Muestras por intervalo para calcular duraciones"
    )

# ============= MAIN CONTENT =============

# Estado: Sin archivos cargados
if instances_file is None or solutions_file is None:
    st.info("👆 Por favor, sube los archivos de **instancias (ZIP)** y **soluciones (JSON)** en la barra lateral")
    
    # Mostrar ejemplo de estructura esperada
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("📦 Estructura del ZIP de Instancias"):
            st.code("""
            instancias.zip
            ├── C101_25.json
            ├── C102_25.json
            ├── C103_25.json
            ├── R101_25.json
            ├── R102_25.json
            └── RC101_25.json
            """, language="text")
    
    with col2:
        with st.expander("📄 Estructura del JSON de Soluciones"):
            st.code("""
[
    {
        "instance_name": "C101_25",
        "routes": [
        {
            "duration": 2965.20,
            "path": [0, 23, 22, 21, 26],
            "t0": 7222.49
        },
        ...
        ],
        "value": 24709.17,
        "tags": ["OPT"]
    },
    {
        "instance_name": "C102_25",
        "routes": [...],
        ...
    }
]
            """, language="json")
    
    st.stop()

# ============= PROCESAMIENTO DE ARCHIVOS =============
with st.spinner("🔄 Procesando archivos..."):
    try:
        # Leer bytes de los archivos
        instances_bytes = instances_file.read()
        solutions_bytes = solutions_file.read()
        
        # Procesar con nuestro motor
        paired_data = core.process_files(instances_bytes, solutions_bytes)
        
        if not paired_data:
            st.error("❌ No se encontraron pares válidos de Instancia-Solución")
            st.warning("Verifica que los nombres de las instancias en `solutions.json` coincidan con los archivos `.json` en el ZIP")
            st.stop()
        
        st.success(f"✅ Se encontraron **{len(paired_data)}** pares Instancia-Solución")
        
        # Guardar en session state
        st.session_state['paired_data'] = paired_data
        
    except json.JSONDecodeError as e:
        st.error(f"❌ Error al leer el archivo JSON de soluciones: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al procesar los archivos: {str(e)}")
        st.exception(e)
        st.stop()

# ============= SELECTOR DE INSTANCIA =============
with st.sidebar:
    st.divider()
    st.header("🎯 Selección")
    
    instance_names = list(st.session_state['paired_data'].keys())
    selected_instance = st.selectbox(
        "Instancia a analizar",
        options=instance_names,
        help="Selecciona el par Instancia-Solución para analizar"
    )

# ============= EJECUCIÓN DEL ANÁLISIS =============
if selected_instance:
    st.header(f"📊 Análisis: {selected_instance}")
    
    # Obtener datos seleccionados
    instance_data = st.session_state['paired_data'][selected_instance]['instance']
    solution_data = st.session_state['paired_data'][selected_instance]['solution']
    
    # Mostrar información básica
    with st.expander("ℹ️ Información de la Instancia y Solución"):
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.markdown("**Instancia:**")
            st.write(f"- Nodos: {instance_data.get('digraph', {}).get('vertex_count', 'N/A')}")
            st.write(f"- Capacidad: {instance_data.get('capacity', 'N/A')}")
            st.write(f"- Horizonte: {instance_data.get('horizon', 'N/A')}")
        
        with col_info2:
            st.markdown("**Solución:**")
            st.write(f"- Rutas: {len(solution_data.get('routes', []))}")
            st.write(f"- Valor: {solution_data.get('value', 'N/A'):.2f}")
            st.write(f"- Tags: {', '.join(solution_data.get('tags', []))}")
    
    # Ejecutar análisis
    with st.spinner("🔬 Ejecutando análisis completo..."):
        try:
            analysis_df = core.run_full_analysis(
                instance_name=selected_instance,
                instance_data=instance_data,
                solution_data=solution_data,
                epsilon=epsilon,
                cant_muestras=cant_muestras
            )
            
            summary_metrics = core.get_summary_metrics(analysis_df)
            
            st.success("✅ Análisis completado exitosamente")
            
        except Exception as e:
            st.error(f"❌ Error durante el análisis: {str(e)}")
            st.exception(e)
            st.stop()
    
    # ============= SECCIÓN 1: MÉTRICAS CLAVE =============
    st.subheader("📈 Métricas Clave")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Arcos",
            value=summary_metrics['total_arcs'],
            delta=f"{summary_metrics['total_routes']} rutas"
        )
    
    with col2:
        st.metric(
            label="Arcos Óptimos (Deciles 0-2)",
            value=summary_metrics['optimal_arcs_count'],
            delta=f"{summary_metrics['optimal_arcs_pct']:.1f}%"
        )
    with col3:
        st.metric(
            label="Cantidad Arcos Cortos (más cercanos al arco de distancia mínima)",
            value=summary_metrics['short_arcs'],
            
        )
    with col4:
        st.metric(
            label="Cerca del Mínimo",
            value=summary_metrics['near_minimum_count'],
            delta=f"{summary_metrics['near_minimum_pct']:.1f}%"
        )
    col5, col6, col7, col8 = st.columns(4)
    
    
    with col5:
        st.metric(
            label="Decil Promedio",
            value=f"{summary_metrics['avg_decile']:.2f}",
            delta="Más bajo = Mejor",
            delta_color="inverse"
        )
    
    
    with col6:
        st.metric("Ratio Promedio vs Mínimo", f"{summary_metrics['avg_ratio_to_min']:.3f}")
    
    with col7:
        st.metric("Ratio Promedio vs Máximo", f"{summary_metrics['avg_ratio_to_max']:.3f}")
    
    with col8:
        st.metric("Arcos Factibles Promedio", f"{summary_metrics['avg_feasible_arcs']:.1f}")
    
    st.divider()
    
    # ============= SECCIÓN 2: GRÁFICO DE DECILES (DURACIÓN) =============
    st.subheader("🎯 Distribución de Decisiones por Decil (Duración)")

    st.markdown("""
    Este gráfico muestra en qué decil se encuentran los arcos elegidos 
    en las soluciones óptimas. Si la hipótesis es correcta, esperamos ver una concentración 
    en los deciles bajos (0-2).
    """)

    decile_data = core.create_decile_histogram_data(analysis_df)

    fig_decile = px.bar(
        decile_data,
        x='Decil',
        y='Cantidad de Arcos',
        text='Porcentaje',
        title="Distribución de Arcos por Decil de Duración",
        labels={'Decil': 'Decil (0 = Más Rápido, 9 = Más Lento)', 'Cantidad de Arcos': 'Frecuencia'},
        color='Decil',
        color_continuous_scale='RdYlGn_r',
        category_orders={'Decil': list(range(10))}  #  fuerza orden 0-9
    )

    fig_decile.update_traces(
    texttemplate='%{text:.1f}%',
    textposition='outside',
    width=0.7  
    )

    fig_decile.update_layout(
        height=500,
        showlegend=False,
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(10)),  #ticks fijos 0..9
            ticktext=[str(i) for i in range(10)],
            tickfont=dict(size=16),   # agranda números del eje
        ),
        bargap=0.3,  
    )


    st.plotly_chart(fig_decile, use_container_width=True)

    # Interpretación automática
    if summary_metrics['optimal_arcs_pct'] > 60:
        st.success("✅ **Hipótesis VALIDADA**: Más del 60% de los arcos están en deciles óptimos (0-2)")
    elif summary_metrics['optimal_arcs_pct'] > 40:
        st.warning("⚠️ **Hipótesis PARCIALMENTE VALIDADA**: Entre 40-60% de arcos en deciles óptimos")
    else:
        st.error("❌ **Hipótesis NO VALIDADA**: Menos del 40% de arcos en deciles óptimos")
    
    # ============= GRÁFICO DE DECILES (DISTANCIA) =============
    st.subheader("📏 Distribución de Decisiones por Decil (Distancia)")

    st.markdown("""
    Este gráfico replica el análisis de deciles pero usando **distancia** en lugar de duración.
    Mide en qué decil de distancia cae el arco elegido respecto a los arcos factibles del intervalo.
    """)

    dist_decile_data = core.create_distance_decile_histogram_data(analysis_df)

    fig_dist_decile = px.bar(
        dist_decile_data,
        x='DecilDist',
        y='Cantidad de Arcos',
        text='Porcentaje',
        title="Distribución de Arcos por Decil de Distancia",
        labels={'DecilDist': 'Decil de Distancia (0 = Más Corto, 9 = Más Largo)', 'Cantidad de Arcos': 'Frecuencia'},
        color='DecilDist',
        color_continuous_scale='RdYlGn_r',
        category_orders={'DecilDist': list(range(10))}  # fuerza orden 0-9
    )

    fig_dist_decile.update_traces(
    texttemplate='Decil %{x}<br>%{text:.1f}%',
    textposition='outside',
    width=0.7
    )

    fig_dist_decile.update_layout(
        height=500,
        showlegend=False,
        xaxis=dict(
            type='linear',
            tickmode='array',
            tickvals=list(range(10)),
            ticktext=[str(i) for i in range(10)],
            tickfont=dict(size=16),
            range=[-0.5, 9.5] #esta linea me parece rara 
        ),
        bargap=0.3
    )

    st.plotly_chart(fig_dist_decile, use_container_width=True)



    # ================================================================
    st.divider()
    
    # ============= SECCIÓN 4: TABLA DE DATOS DETALLADOS =============
    st.subheader("📋 Datos Detallados")
    
    # Filtros
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        filter_route = st.multiselect(
            "Filtrar por Ruta",
            options=sorted(analysis_df['route_idx'].unique()),
            default=None
        )
    
    with col_filter2:
        filter_decile = st.slider(
            "Filtrar por Rango de Decil",
            min_value=0,
            max_value=9,
            value=(0, 9)
        )
    
    # Aplicar filtros
    filtered_df = analysis_df.copy()
    if filter_route:
        filtered_df = filtered_df[filtered_df['route_idx'].isin(filter_route)]
    filtered_df = filtered_df[
        (filtered_df['decile_rank'] >= filter_decile[0]) & 
        (filtered_df['decile_rank'] <= filter_decile[1])
    ]
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=400,
        column_config={
            "arc_id": "Arco",
            "departure_time": st.column_config.NumberColumn("Tiempo Salida", format="%.2f"),
            "actual_travel_time": st.column_config.NumberColumn("Duración Real", format="%.3f"),
            "fastest_feasible_time": st.column_config.NumberColumn("Mínimo Factible", format="%.3f"),
            "decile_rank": st.column_config.NumberColumn("Decil", format="%d"),
            "proximity_category": "Categoría"
        }
    )
    
    st.divider()
    
    # ============= SECCIÓN 5: EXPORTACIÓN =============
    st.subheader("💾 Exportar Resultados")
    
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        # Exportar a Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            analysis_df.to_excel(writer, sheet_name='Detalle_Arcos', index=False)
            pd.DataFrame([summary_metrics]).to_excel(writer, sheet_name='Resumen', index=False)
            decile_data.to_excel(writer, sheet_name='Distribucion_Deciles', index=False)
        
        st.download_button(
            label="📥 Descargar Excel Completo",
            data=buffer.getvalue(),
            file_name=f"analisis_{selected_instance}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col_export2:
        # Exportar CSV
        csv_buffer = io.StringIO()
        analysis_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Descargar CSV",
            data=csv_buffer.getvalue(),
            file_name=f"analisis_{selected_instance}.csv",
            mime="text/csv"
        )

# ============= FOOTER =============
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
<p><strong>TDVRP Analyzer</strong> - Tesis TD8: Problema de Ruteo de Vehículos Dependiente del Tiempo</p>
<p>Herramienta desarrollada para análisis estructural de soluciones óptimas</p>
</div>
""", unsafe_allow_html=True)