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

    epsilon = st.number_input(
        "Epsilon [1 ; 5000]",
        min_value=1,
        max_value=5000,
        value=100,
        step=1,
        help="Ingresa un valor exacto de epsilon"
    )

    # Usar el valor del input si es diferente al slider

    cant_muestras = st.slider(
        "Cantidad de muestras",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
        help="Muestras por intervalo para calcular duraciones"
    )


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



page = st.sidebar.selectbox(
    "Tipo de Análisis",
    ["Análisis Individual", "Análisis Global"],
    index=0,
    help="Elige entre analizar una instancia específica o todas las instancias"
)
# Verificar que hay datos cargados
if 'paired_data' not in st.session_state:
    st.info("Por favor, carga los archivos en la barra lateral para comenzar")
    st.stop()

if page == "Análisis Individual":
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
                label="Arcos Óptimos - Tiempo (Deciles 0-2)",
                value=summary_metrics['optimal_arcs_count'],
                delta=f"{summary_metrics['optimal_arcs_pct']:.1f}%"
            )
        
        with col3:
            st.metric(
                label="Arcos Óptimos - Distancia (Deciles 0-2)",
                value=summary_metrics['optimal_arcs_count_dist'],
                delta=f"{summary_metrics['optimal_arcs_pct_dist']:.1f}%"
            )
        with col4:
            st.metric(
                label="Cerca del Mínimo",
                value=summary_metrics['near_minimum_count'],
                delta=f"{summary_metrics['near_minimum_pct']:.1f}%"
            )
        col5, col6, col7, col8, col9 = st.columns(5)
        
        
        with col5:
            st.metric(
                label="Decil Promedio - Tiempo",
                value=f"{summary_metrics['avg_decile']:.2f}",
                delta="Más bajo = Mejor",
                delta_color="inverse"
            )
        
        with col6:
            st.metric(
                label="Decil Promedio - Distancia",
                value=f"{summary_metrics['avg_decile_distance']:.2f}",
                delta="Más bajo = Mejor",
                delta_color="inverse"
            )
        
        with col7:
            st.metric("Ratio Promedio vs Mínimo - Tiempo", f"{summary_metrics['avg_ratio_to_min']:.3f}")
        
        with col8:
            st.metric("Ratio Promedio vs Mínimo - Distancia", f"{summary_metrics['avg_ratio_to_min_dist']:.3f}")
        
        with col9:
            st.metric("Arcos Factibles Promedio", f"{summary_metrics['avg_feasible_arcs']:.1f}")
        
        st.divider()
        
        # ============= SECCIÓN 2: GRÁFICO DE DECILES (CLAVE) =============
        st.subheader("🎯 Distribución de Decisiones por Decil")
        st.markdown("""
        **Este es el gráfico clave de la tesis**. Muestra en qué decil se encuentran los arcos elegidos 
        en las soluciones óptimas. Si la hipótesis es correcta, esperamos ver una concentración 
        en los deciles bajos (0-2).
        """)

        st.markdown("### Distribución por Tiempo")
        decile_data = core.create_decile_histogram_data(analysis_df)
        
        fig_decile = px.bar(
            decile_data,
            x='Decil',
            y='Cantidad de Arcos',
            text='Porcentaje',
            title="Distribución de Arcos por Decil de Duración",
            labels={'Decil': 'Decil (0 = Más Rápido)', 'Cantidad de Arcos': 'Frecuencia'},
            color='Decil',
            color_continuous_scale='RdYlGn_r'
        )
        
        fig_decile.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_decile.update_layout(height=400, showlegend=False)
        
        # Ajustar layout para que se vea el texto
        max_value = decile_data['Cantidad de Arcos'].max()
        
        fig_decile.update_layout(
            height=450,  # Aumentar altura
            showlegend=False,
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(10)),
                ticktext=[str(i) for i in range(10)],
                range=[-0.5, 9.5]
            ),
            yaxis=dict(
                range=[0, max_value * 1.15]  # Añadir 15% extra de espacio arriba
            ),
            margin=dict(t=60, b=40, l=40, r=40)  # Ajustar márgenes
        )
        
        st.plotly_chart(fig_decile, use_container_width=True)
        
        if summary_metrics['optimal_arcs_pct'] > 60:
            st.success("✅ **Tiempo - Hipótesis VALIDADA**: >60% en deciles óptimos")
        elif summary_metrics['optimal_arcs_pct'] > 40:
            st.warning("⚠️ **Tiempo - Hipótesis PARCIAL**: 40-60% en deciles óptimos")
        else:
            st.error("❌ **Tiempo - Hipótesis NO VALIDADA**: <40% en deciles óptimos")
        
        st.markdown("### Distribución por Distancia")
        decile_data_dist = core.create_distance_decile_histogram_data(analysis_df)
        
        fig_decile_dist = px.bar(
            decile_data_dist,
            x='Decil',
            y='Cantidad de Arcos',
            text='Porcentaje',
            title="Distribución de Arcos por Decil de Distancia",
            labels={'Decil': 'Decil (0 = Más Corto)', 'Cantidad de Arcos': 'Frecuencia'},
            color='Decil',
            color_continuous_scale='Blues'
        )
        
        fig_decile_dist.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_decile_dist.update_layout(height=400, showlegend=False)
        
        fig_decile_dist.update_layout(
            height=400, 
            showlegend=False,
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(10)),  # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                ticktext=[str(i) for i in range(10)],  # ['0', '1', '2', ..., '9']
                range=[-0.5, 9.5]  # Asegurar que se vean todos los valores
            )
        )
        
        # Ajustar layout para que se vea el texto
        max_value_dist = decile_data_dist['Cantidad de Arcos'].max()
        
        fig_decile_dist.update_layout(
            height=450,  # Aumentar altura
            showlegend=False,
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(10)),
                ticktext=[str(i) for i in range(10)],
                range=[-0.5, 9.5]
            ),
            yaxis=dict(
                range=[0, max_value_dist * 1.15]  # Añadir 15% extra de espacio arriba
            ),
            margin=dict(t=60, b=40, l=40, r=40)  # Ajustar márgenes
        )
        st.plotly_chart(fig_decile_dist, use_container_width=True)

        if summary_metrics['optimal_arcs_pct_dist'] > 60:
            st.success("✅ **Distancia - Hipótesis VALIDADA**: >60% en deciles óptimos")
        elif summary_metrics['optimal_arcs_pct_dist'] > 40:
            st.warning("⚠️ **Distancia - Hipótesis PARCIAL**: 40-60% en deciles óptimos")
        else:
            st.error("❌ **Distancia - Hipótesis NO VALIDADA**: <40% en deciles óptimos")

        
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
                decile_data.to_excel(writer, sheet_name='Distribucion_Deciles_Tiempo', index=False)
                decile_data_dist.to_excel(writer, sheet_name='Distribucion_Deciles_Distancia', index=False)
            
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



elif page == "Análisis Global":
    # Código del análisis global aquí
    st.header("Análisis Global de Todas las Instancias")
# ============= SECCIÓN: ANÁLISIS GLOBAL =============


    with st.expander("ℹ️ ¿Qué es el Análisis Global?", expanded=False):
        st.markdown("""
        El análisis global procesa **todas las instancias cargadas** y genera:
        - **Métricas agregadas** de toda la colección
        - **Comparaciones por tipo** de instancia (C, R, RC)
        - **Distribuciones globales** de deciles
        - **Validación estadística** de la hipótesis a gran escala
        """)

    # Botón para ejecutar análisis global
    if st.button("🚀 Ejecutar Análisis Global", type="primary"):
        with st.spinner("🔬 Procesando todas las instancias..."):
            try:
                # Ejecutar análisis global
                global_df, global_metrics = core.run_global_analysis(
                    paired_data=st.session_state['paired_data'],
                    epsilon=epsilon,
                    cant_muestras=cant_muestras
                )
                
                comparison_data = core.create_global_comparison_data(global_df)
                
                # Guardar en session state
                st.session_state['global_df'] = global_df
                st.session_state['global_metrics'] = global_metrics
                st.session_state['comparison_data'] = comparison_data
                
                st.success(f"✅ Análisis global completado: {global_metrics['total_instances']} instancias, {global_metrics['total_arcs']} arcos")
                
            except Exception as e:
                st.error(f"❌ Error en análisis global: {str(e)}")
                st.exception(e)

    # Si ya se ejecutó el análisis global, mostrar resultados
    if 'global_df' in st.session_state and not st.session_state['global_df'].empty:
        
        global_df = st.session_state['global_df']
        global_metrics = st.session_state['global_metrics']
        comparison_data = st.session_state['comparison_data']
        
        # ============= MÉTRICAS GLOBALES =============
        st.subheader("📊 Resumen Global")
        
        col_g1, col_g2, col_g3, col_g4, col_g5 = st.columns(5)
        
        with col_g1:
            st.metric("Total Instancias", global_metrics['total_instances'])
            
        with col_g2:
            st.metric("Total Arcos", f"{global_metrics['total_arcs']:,}")
            
        with col_g3:
            st.metric(
                "% Óptimos (Tiempo)",
                f"{global_metrics['global_optimal_pct']:.1f}%",
                delta="Deciles 0-2"
            )
            
        with col_g4:
            st.metric(
                "% Óptimos (Distancia)", 
                f"{global_metrics['global_optimal_pct_dist']:.1f}%",
                delta="Deciles 0-2"
            )
            
        with col_g5:
            st.metric(
                "Decil Promedio Global",
                f"{global_metrics['global_avg_decile']:.2f}",
                delta=f"Dist: {global_metrics['global_avg_decile_dist']:.2f}"
            )
        
        # ============= VALIDACIÓN DE HIPÓTESIS GLOBAL =============
        st.subheader("🎯 Validación de Hipótesis - Nivel Global")
        
        col_hyp1, col_hyp2 = st.columns(2)
        
        with col_hyp1:
            if global_metrics['global_optimal_pct'] > 60:
                st.success(f"✅ **HIPÓTESIS VALIDADA (Tiempo)**: {global_metrics['global_optimal_pct']:.1f}% en deciles óptimos")
            elif global_metrics['global_optimal_pct'] > 40:
                st.warning(f"⚠️ **HIPÓTESIS PARCIAL (Tiempo)**: {global_metrics['global_optimal_pct']:.1f}% en deciles óptimos")
            else:
                st.error(f"❌ **HIPÓTESIS NO VALIDADA (Tiempo)**: {global_metrics['global_optimal_pct']:.1f}% en deciles óptimos")
                
        with col_hyp2:
            if global_metrics['global_optimal_pct_dist'] > 60:
                st.success(f"✅ **HIPÓTESIS VALIDADA (Distancia)**: {global_metrics['global_optimal_pct_dist']:.1f}% en deciles óptimos")
            elif global_metrics['global_optimal_pct_dist'] > 40:
                st.warning(f"⚠️ **HIPÓTESIS PARCIAL (Distancia)**: {global_metrics['global_optimal_pct_dist']:.1f}% en deciles óptimos")
            else:
                st.error(f"❌ **HIPÓTESIS NO VALIDADA (Distancia)**: {global_metrics['global_optimal_pct_dist']:.1f}% en deciles óptimos")
        
        # ============= GRÁFICOS COMPARATIVOS =============
        st.subheader("📈 Comparación por Tipo de Instancia")
        
        # Gráfico 1: Deciles por tipo (Tiempo)
        fig_global_time = px.bar(
            comparison_data['deciles_by_type'],
            x='decile_rank',
            y='percentage',
            color='instance_type',
            barmode='group',
            title="Distribución de Deciles por Tipo de Instancia (Tiempo)",
            labels={'decile_rank': 'Decil', 'percentage': 'Porcentaje (%)', 'instance_type': 'Tipo'},
            color_discrete_map={'C': '#1f77b4', 'R': '#ff7f0e', 'RC': '#2ca02c'}
        )
        fig_global_time.update_layout(height=400)
        st.plotly_chart(fig_global_time, use_container_width=True)
        
        # Gráfico 2: Deciles por tipo (Distancia)
        fig_global_dist = px.bar(
            comparison_data['deciles_dist_by_type'],
            x='decile_rank_distance',
            y='percentage',
            color='instance_type',
            barmode='group',
            title="Distribución de Deciles por Tipo de Instancia (Distancia)",
            labels={'decile_rank_distance': 'Decil Distancia', 'percentage': 'Porcentaje (%)', 'instance_type': 'Tipo'},
            color_discrete_map={'C': '#1f77b4', 'R': '#ff7f0e', 'RC': '#2ca02c'}
        )
        fig_global_dist.update_layout(height=400)
        st.plotly_chart(fig_global_dist, use_container_width=True)
        
        # ============= TABLA COMPARATIVA POR TIPO =============
        st.subheader("📋 Resumen por Tipo de Instancia")
        
        type_summary_df = pd.DataFrame([
            {
                'Tipo': tipo,
                'Total Arcos': data['total_arcs'],
                '% Óptimos (Tiempo)': f"{data['optimal_arcs_pct']:.1f}%",
                '% Óptimos (Distancia)': f"{data['optimal_arcs_pct_dist']:.1f}%",
                'Decil Promedio (Tiempo)': f"{data['avg_decile']:.2f}",
                'Decil Promedio (Distancia)': f"{data['avg_decile_dist']:.2f}",
                '% Cerca Mínimo': f"{data['near_min_pct']:.1f}%",
                '% Arcos Cortos': f"{data['short_arcs_pct']:.1f}%"
            }
            for tipo, data in global_metrics['by_instance_type'].items()
        ])
        
        st.dataframe(type_summary_df, use_container_width=True)
        
            
        # ============= EXPORTACIÓN GLOBAL =============
        st.subheader("💾 Exportar Análisis Global")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # Excel completo
            buffer_global = io.BytesIO()
            core.export_global_analysis_excel(global_df, global_metrics, comparison_data, "temp.xlsx")
            
            # Recrear el buffer para descarga
            with pd.ExcelWriter(buffer_global, engine='openpyxl') as writer:
                global_df.to_excel(writer, sheet_name='Todos_los_Arcos', index=False)
                
                global_summary_df = pd.DataFrame([{
                    'Total_Instancias': global_metrics['total_instances'],
                    'Total_Arcos': global_metrics['total_arcs'],
                    'Pct_Optimos_Tiempo': global_metrics['global_optimal_pct'],
                    'Pct_Optimos_Distancia': global_metrics['global_optimal_pct_dist'],
                    'Decil_Promedio_Tiempo': global_metrics['global_avg_decile'],
                    'Decil_Promedio_Distancia': global_metrics['global_avg_decile_dist']
                }])
                global_summary_df.to_excel(writer, sheet_name='Resumen_Global', index=False)
                
                type_summary_df.to_excel(writer, sheet_name='Resumen_por_Tipo', index=False)
                comparison_data['instance_summary'].to_excel(writer, sheet_name='Por_Instancia', index=False)
            
            st.download_button(
                label="📥 Descargar Excel Global Completo",
                data=buffer_global.getvalue(),
                file_name=f"analisis_global_epsilon_{epsilon}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col_exp2:
            # Resumen ejecutivo CSV
            summary_csv = io.StringIO()
            type_summary_df.to_csv(summary_csv, index=False)
            
            st.download_button(
                label="📥 Resumen por Tipo (CSV)",
                data=summary_csv.getvalue(),
                file_name=f"resumen_tipos_epsilon_{epsilon}.csv",
                mime="text/csv"
            )

    else:
        st.info("👆 Haz clic en **'Ejecutar Análisis Global'** para procesar todas las instancias")

    st.divider()
    # ============= FOOTER =============
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p><strong>TDVRP Analyzer</strong> - Tesis TD8: Problema de Ruteo de Vehículos Dependiente del Tiempo</p>
    <p>Herramienta desarrollada para análisis estructural de soluciones óptimas</p>
    </div>
    """, unsafe_allow_html=True)

