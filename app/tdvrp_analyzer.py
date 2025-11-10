"""
Motor de análisis para TDVRP (Time-Dependent Vehicle Routing Problem)
Integra toda la lógica de cálculo PWL, simulación y análisis de factibilidad
"""

import pandas as pd
import numpy as np
import json
import io
import zipfile
from typing import Dict, List, Tuple, Any
import math

# Importar funciones existentes
from build_pwl_arc import Z, P, fwd, tau_pts
from simulacion import simulacion
from metricas_arcos import clusters_arcos_ruta, duracion_arcos, metricas, metrica_distancia


def process_files(instances_zip_bytes: bytes, solutions_json_bytes: bytes) -> Dict[str, Dict[str, Any]]:
    """
    Procesa archivos de instancias (ZIP) y soluciones (JSON).
    Empareja automáticamente instancias con sus soluciones basándose en instance_name.
    
    Args:
        instances_zip_bytes: Contenido binario del archivo .zip con instancias
        solutions_json_bytes: Contenido binario del archivo JSON con todas las soluciones
        
    Returns:
        Dict con estructura: {
            'nombre_instancia': {
                'instance': dict (datos JSON de la instancia),
                'solution': dict (datos de la solución para esa instancia)
            }
        }
    """
    paired_data = {}
    
    # 1. Cargar todas las soluciones desde el JSON
    solutions_data = json.loads(solutions_json_bytes.decode('utf-8'))
    
    # Crear índice de soluciones por instance_name
    solutions_index = {}
    for solution in solutions_data:
        instance_name = solution.get("instance_name")
        if instance_name:
            solutions_index[instance_name] = solution
    
    # 2. Cargar todas las instancias desde el ZIP
    with zipfile.ZipFile(io.BytesIO(instances_zip_bytes), 'r') as zf:
        file_list = zf.namelist()
        
        for filename in file_list:
            # Ignorar directorios, archivos ocultos y metadata
            if filename.endswith('/') or filename.startswith('.') or '__MACOSX' in filename:
                continue
                
            basename = filename.split('/')[-1]  # Solo el nombre del archivo
            
            if not basename or not basename.endswith('.json'):
                continue
                
            # Extraer nombre de instancia del archivo
            instance_name = basename.rsplit('.', 1)[0]
            
            # Leer instancia
            try:
                instance_content = zf.read(filename)
                instance_data = json.loads(instance_content.decode('utf-8'))
                
                # Verificar si tenemos solución para esta instancia
                if instance_name in solutions_index:
                    paired_data[instance_name] = {
                        'instance': instance_data,
                        'solution': solutions_index[instance_name]
                    }
            except Exception as e:
                print(f"⚠️ Error al leer instancia {filename}: {str(e)}")
                continue
    
    return paired_data


def run_full_analysis(instance_name: str, instance_data: dict, solution_data: dict, 
                     epsilon: float = 0.1, cant_muestras: int = 10) -> pd.DataFrame:
    """
    Ejecuta el análisis completo sobre un par instancia-solución.
    
    Esta es la función CORE que integra toda la lógica de investigación:
    1. Simula la ruta usando PWL #? no seria la fwd en vez de pwl?
    2. Identifica arcos factibles por intervalo
    3. Calcula duraciones y métricas
    4. Asigna deciles de decisión
    
    Args:
        instance_name: Nombre de la instancia
        instance_data: Diccionario con datos de la instancia
        solution_data: Diccionario con datos de la solución (debe tener "routes")
        epsilon: Tolerancia para intervalos de tiempo
        cant_muestras: Muestras para calcular duraciones
        
    Returns:
        DataFrame con columnas detalladas del análisis
    """
    
    results = []
    
    # Extraer rutas de la solución
    routes = solution_data.get("routes", [])
    
    if not routes:
        raise ValueError(f"La solución para {instance_name} no contiene rutas")
    
    # Ejecutar simulación para obtener time_departures
    time_departures, error = simulacion(solution_data, instance_data)
    
    if error:
        print(f"⚠️ Advertencia: Error en simulación de {instance_name}")
    
    # Procesar cada ruta
    for idx_ruta, route in enumerate(routes):
        path = route["path"]
        t0 = route["t0"]
        
        # Construir intervalos de tiempo de la ruta
        intervalos_ruta = []
        td_ruta = time_departures[idx_ruta]
        for i in range(len(td_ruta) - 1):
            inter = (td_ruta[i][2], td_ruta[i+1][2])
            intervalos_ruta.append(inter)
        
        # Arcos utilizados en la ruta
        arcos_utilizados = [(path[i], path[i+1]) for i in range(len(path) - 1)]
        
        # Obtener arcos factibles por intervalo
        arcos_factibles = clusters_arcos_ruta(instance_data, intervalos_ruta, arcos_utilizados)
        
        # Calcular duraciones de arcos factibles
        duracion_arcos_factibles = duracion_arcos(
            arcos_factibles, intervalos_ruta, instance_data, epsilon, cant_muestras
        )
        
        # Calcular métricas (ahora devuelve 3 valores)
        metricas_res, metricas_str, rels = metricas(
            arcos_factibles, duracion_arcos_factibles, time_departures, idx_ruta
        )
        
        distancias = instance_data["distances"]
        #aca quiero meter metricas_distancia
        metricas_res_dist, metricas_str_dist, _ = metrica_distancia(arcos_factibles, distancias, path)
        # Construir DataFrame con resultados detallados
        for idx_arco, (intervalo, arcos) in enumerate(arcos_factibles.items()):
            arco_usado = arcos_utilizados[idx_arco]
            duracion_optima = td_ruta[idx_arco][3]
            
            # Extraer duraciones de todos los arcos factibles
            dur_entries = duracion_arcos_factibles.get(intervalo, [])
            
            duraciones = [entry["durations"]["mean"] for entry in dur_entries if entry["durations"]["mean"] > 0]
            
            # Extraer distancias de todos los arcos factibles para este intervalo
            distancias_factibles = []
            for arco in arcos:  # arcos son TODOS los arcos factibles para este intervalo
                i, j = arco
                if i < len(distancias) and j < len(distancias[i]):
                    dist = distancias[i][j]
                    if dist > 0:
                        distancias_factibles.append(dist)
        
            # Distancia del arco utilizado
            distancia_optima = distancias[arco_usado[0]][arco_usado[1]] if distancias else 0
            
            if not distancias_factibles and distancia_optima > 0:
                distancias_factibles = [distancia_optima]    
            
            min_dur = min(duraciones) if duraciones else duracion_optima
            max_dur = max(duraciones) if duraciones else duracion_optima
            min_dist = min(distancias_factibles) if distancias_factibles else distancia_optima
            max_dist = max(distancias_factibles) if distancias_factibles else distancia_optima
            
            # Calcular ratios
            ratio_min = duracion_optima / min_dur if min_dur > 0 else None
            ratio_max = duracion_optima / max_dur if max_dur > 0 else None
            ratio_min_dist = distancia_optima / min_dist if min_dist > 0 else None
            ratio_max_dist = distancia_optima / max_dist if max_dist > 0 else None
            
            # Calcular deciles
            decile = _calculate_decile(duracion_optima, duraciones)
            decile_dist = _calculate_decile(distancia_optima, distancias_factibles)
                        
            # Categoría de proximidad
            proximity = metricas_str[idx_arco] if idx_arco < len(metricas_str) else "desconocido"
            
            # Coordenadas (si están disponibles en la instancia)
            coords = _get_node_coordinates(instance_data, arco_usado[0], arco_usado[1])
            
            results.append({
                'route_idx': idx_ruta,
                'arc_idx': idx_arco,
                'arc_id': f"{arco_usado[0]}-{arco_usado[1]}",
                'node_from': arco_usado[0],
                'node_to': arco_usado[1],
                'departure_time': intervalo[0],
                'actual_travel_time': duracion_optima,
                'fastest_feasible_time': min_dur,
                'slowest_feasible_time': max_dur,
                'actual_distance': distancia_optima,
                'shortest_feasible_distance': min_dist,
                'longest_feasible_distance': max_dist,
                'ratio_to_min': ratio_min,
                'ratio_to_max': ratio_max,
                'ratio_to_min_dist': ratio_min_dist,
                'ratio_to_max_dist': ratio_max_dist,
                'longitud arco': metricas_str_dist[idx_arco],
                'decile_rank': decile,
                'decile_rank_distance': decile_dist,
                'proximity_category': proximity, 
                'num_feasible_arcs': len(arcos),
                'node_from_lat': coords[0],
                'node_from_lon': coords[1],
                'node_to_lat': coords[2],
                'node_to_lon': coords[3]
            })
    
    return pd.DataFrame(results)


def _calculate_decile(value: float, distribution: List[float]) -> int:
    """
    Calcula en qué decil cae un valor dentro de una distribución.
    
    Args:
        value: Valor a clasificar
        distribution: Lista de valores que forman la distribución
        
    Returns:
        Decil (0-9), donde 0 es el decil más bajo (valores más pequeños)
    """
    if not distribution or len(distribution) == 0:
        return 5  # Valor medio por defecto
    
    sorted_dist = sorted(distribution)
    
    # Calcular percentiles
    for decile in range(10):
        percentile = np.percentile(sorted_dist, (decile + 1) * 10)
        if value <= percentile:
            return decile
    
    return 9  # Último decil


def _get_node_coordinates(instance_data: dict, node_from: int, node_to: int) -> Tuple[float, float, float, float]:
    """
    Extrae coordenadas de nodos de la instancia.
    
    Returns:
        Tupla (lat_from, lon_from, lat_to, lon_to)
    """
    # Intentar diferentes estructuras de datos
    if "coordinates" in instance_data:
        coords = instance_data["coordinates"]
        return (
            coords[node_from][0], coords[node_from][1],
            coords[node_to][0], coords[node_to][1]
        )
    elif "nodes" in instance_data:
        nodes = instance_data["nodes"]
        return (
            nodes[node_from].get("lat", 0), nodes[node_from].get("lon", 0),
            nodes[node_to].get("lat", 0), nodes[node_to].get("lon", 0)
        )
    else:
        # Coordenadas simuladas para pruebas
        return (0.0, 0.0, 0.0, 0.0)


def get_summary_metrics(analysis_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula métricas resumen clave para validar la hipótesis.
    
    Returns:
        Diccionario con métricas agregadas
    """
    total_arcs = len(analysis_df)
    
    if 'longitud arco' in analysis_df.columns:
        arcos_cortos = (analysis_df['longitud arco'] == 'arco corto').sum()
    else:
        print("⚠️ La columna 'longitud arco' no existe en analysis_df")
    
    print(analysis_df.columns)

    
    # Contar arcos por categoría de proximidad
    near_min = (analysis_df['proximity_category'] == 'mas cerca del min').sum()
    near_max = (analysis_df['proximity_category'] == 'mas cerca del max').sum()
    arcos_cortos = (analysis_df['longitud arco'] == 'arco corto').sum()
    arcos_largos = (analysis_df['longitud arco'] == 'arco largo').sum()
    # Estadísticas de deciles
    avg_decile = analysis_df['decile_rank'].mean()
    deciles_0_2 = (analysis_df['decile_rank'] <= 2).sum()  # Arcos "óptimos"
    deciles_7_9 = (analysis_df['decile_rank'] >= 7).sum()  # Arcos "subóptimos"
    
    # Ratios promedio
    avg_ratio_min = analysis_df['ratio_to_min'].mean()
    avg_ratio_max = analysis_df['ratio_to_max'].mean()
       # Estadísticas de deciles para distancia
    avg_decile_dist = analysis_df['decile_rank_distance'].mean()
    deciles_0_2_dist = (analysis_df['decile_rank_distance'] <= 2).sum()  # Arcos "óptimos" en distancia
    deciles_7_9_dist = (analysis_df['decile_rank_distance'] >= 7).sum()  # Arcos "subóptimos" en distancia
    
    # Ratios promedio para distancia
    avg_ratio_min_dist = analysis_df['ratio_to_min_dist'].mean()
    avg_ratio_max_dist = analysis_df['ratio_to_max_dist'].mean()
    
    
    return {
        'total_arcs': total_arcs,
        'total_routes': analysis_df['route_idx'].nunique(),
        'near_minimum_count': near_min,
        'near_maximum_count': near_max,
        'near_minimum_pct': (near_min / total_arcs * 100) if total_arcs > 0 else 0,
        'avg_decile': avg_decile,
        'avg_decile_distance': avg_decile_dist,
        'optimal_arcs_count': deciles_0_2,
        'optimal_arcs_pct': (deciles_0_2 / total_arcs * 100) if total_arcs > 0 else 0,
        'optimal_arcs_count_dist': deciles_0_2_dist,
        'optimal_arcs_pct_dist': (deciles_0_2_dist / total_arcs * 100) if total_arcs > 0 else 0,
        'suboptimal_arcs_count': deciles_7_9,
        'suboptimal_arcs_count_dist': deciles_7_9_dist,
        'avg_ratio_to_min': avg_ratio_min,
        'avg_ratio_to_max': avg_ratio_max,
        'avg_ratio_to_min_dist': avg_ratio_min_dist,
        'avg_ratio_to_max_dist': avg_ratio_max_dist,
        'short_arcs': arcos_cortos,
        'long_arcs': arcos_largos,
        'avg_feasible_arcs': analysis_df['num_feasible_arcs'].mean(),
        'total_travel_time': analysis_df['actual_travel_time'].sum()
    }


def create_decile_histogram_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara datos para el histograma de deciles (gráfico clave de la tesis).
    
    Returns:
        DataFrame listo para Plotly con conteos por decil
    """
    decile_counts = analysis_df['decile_rank'].value_counts().sort_index()
    
    return pd.DataFrame({
        'Decil': decile_counts.index,
        'Cantidad de Arcos': decile_counts.values,
        'Porcentaje': (decile_counts.values / len(analysis_df) * 100)
    })

def create_distance_decile_histogram_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara datos para el histograma de deciles de distancia.
    
    Returns:
        DataFrame listo para Plotly con conteos por decil de distancia
    """
    decile_counts = analysis_df['decile_rank_distance'].value_counts().sort_index()
    
    return pd.DataFrame({
        'Decil': decile_counts.index,
        'Cantidad de Arcos': decile_counts.values,
        'Porcentaje': (decile_counts.values / len(analysis_df) * 100)
    })

def create_route_map_data(analysis_df: pd.DataFrame) -> List[Dict]:
    """
    Prepara datos para visualizar rutas en mapa.
    
    Returns:
        Lista de diccionarios con información de cada arco para Folium
    """
    map_data = []
    
    for _, row in analysis_df.iterrows():
        # Asignar color según decil
        if row['decile_rank'] <= 2:
            color = 'green'  # Óptimo
            category = 'Óptimo (Deciles 0-2)'
        elif row['decile_rank'] <= 5:
            color = 'orange'  # Medio
            category = 'Medio (Deciles 3-5)'
        else:
            color = 'red'  # Subóptimo
            category = 'Subóptimo (Deciles 6-9)'
        
        map_data.append({
            'route_idx': row['route_idx'],
            'arc_id': row['arc_id'],
            'coords_from': (row['node_from_lat'], row['node_from_lon']),
            'coords_to': (row['node_to_lat'], row['node_to_lon']),
            'color': color,
            'category': category,
            'decile': row['decile_rank'],
            'duration': row['actual_travel_time'],
            'departure': row['departure_time']
        })
    
    return map_data


def export_results_to_excel(analysis_df: pd.DataFrame, summary_metrics: Dict, 
                            output_path: str = "resultados_analisis.xlsx"):
    """
    Exporta resultados completos a Excel (similar a metricas_arcos.py).
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Hoja 1: Análisis detallado
        analysis_df.to_excel(writer, sheet_name='Detalle_Arcos', index=False)
        
        # Hoja 2: Resumen de métricas
        summary_df = pd.DataFrame([summary_metrics])
        summary_df.to_excel(writer, sheet_name='Resumen', index=False)
        
        # Hoja 3: Distribución de deciles
        decile_dist = create_decile_histogram_data(analysis_df)
        decile_dist.to_excel(writer, sheet_name='Distribucion_Deciles', index=False)


def run_global_analysis(paired_data: Dict, epsilon: float = 0.1, cant_muestras: int = 10) -> Tuple[pd.DataFrame, Dict]:
    """
    Ejecuta análisis sobre TODAS las instancias y genera métricas globales.
    
    Returns:
        Tuple[DataFrame completo, métricas agregadas globales]
    """
    all_results = []
    instance_summaries = []
    
    for instance_name, data in paired_data.items():
        try:
            # Ejecutar análisis por instancia
            instance_df = run_full_analysis(
                instance_name=instance_name,
                instance_data=data['instance'],
                solution_data=data['solution'],
                epsilon=epsilon,
                cant_muestras=cant_muestras
            )
            
            # Agregar columna de instancia
            instance_df['instance_name'] = instance_name
            
            # Determinar tipo de instancia
            tipo = "RC" if instance_name.startswith("RC") else instance_name[0]
            instance_df['instance_type'] = tipo
            
            # Agregar a resultados globales
            all_results.append(instance_df)
            
            # Calcular resumen por instancia
            instance_summary = get_summary_metrics(instance_df)
            instance_summary['instance_name'] = instance_name
            instance_summary['instance_type'] = tipo
            instance_summaries.append(instance_summary)
            
        except Exception as e:
            print(f"⚠️ Error procesando {instance_name}: {str(e)}")
            continue
    
    # Combinar todos los resultados
    global_df = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
    
    # Métricas globales agregadas
    global_metrics = _calculate_global_metrics(global_df, instance_summaries)
    
    return global_df, global_metrics

def _calculate_global_metrics(global_df: pd.DataFrame, instance_summaries: List[Dict]) -> Dict:
    """Calcula métricas agregadas a nivel global"""
    if global_df.empty:
        return {}
    
    # Métricas por tipo de instancia
    by_type = {}
    for inst_type in global_df['instance_type'].unique():
        type_df = global_df[global_df['instance_type'] == inst_type]
        by_type[inst_type] = {
            'total_arcs': len(type_df),
            'optimal_arcs_pct': (type_df['decile_rank'] <= 2).sum() / len(type_df) * 100,
            'optimal_arcs_pct_dist': (type_df['decile_rank_distance'] <= 2).sum() / len(type_df) * 100,
            'avg_decile': type_df['decile_rank'].mean(),
            'avg_decile_dist': type_df['decile_rank_distance'].mean(),
            'near_min_pct': (type_df['proximity_category'] == 'mas cerca del min').sum() / len(type_df) * 100,
            'short_arcs_pct': (type_df['longitud arco'] == 'mas cerca de la min dist').sum() / len(type_df) * 100,
        }
    
    return {
        'total_instances': len(set(global_df['instance_name'])),
        'total_arcs': len(global_df),
        'total_routes': global_df['route_idx'].nunique(),
        'global_optimal_pct': (global_df['decile_rank'] <= 2).sum() / len(global_df) * 100,
        'global_optimal_pct_dist': (global_df['decile_rank_distance'] <= 2).sum() / len(global_df) * 100,
        'global_avg_decile': global_df['decile_rank'].mean(),
        'global_avg_decile_dist': global_df['decile_rank_distance'].mean(),
        'by_instance_type': by_type,
        'instance_summaries': instance_summaries
    }

def create_global_comparison_data(global_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Prepara datos para gráficos comparativos globales"""
    
    # 1. Deciles por tipo de instancia
    deciles_by_type = global_df.groupby(['instance_type', 'decile_rank']).size().reset_index(name='count')
    deciles_by_type['percentage'] = deciles_by_type.groupby('instance_type')['count'].transform(lambda x: x / x.sum() * 100)
    
    # 2. Deciles de distancia por tipo
    deciles_dist_by_type = global_df.groupby(['instance_type', 'decile_rank_distance']).size().reset_index(name='count')
    deciles_dist_by_type['percentage'] = deciles_dist_by_type.groupby('instance_type')['count'].transform(lambda x: x / x.sum() * 100)
    
    # 3. Resumen por instancia individual
    instance_summary = global_df.groupby('instance_name').agg({
        'decile_rank': ['mean', 'std'],
        'decile_rank_distance': ['mean', 'std'],
        'proximity_category': lambda x: (x == 'mas cerca del min').sum() / len(x) * 100,
        'longitud arco': lambda x: (x == 'mas cerca de la min dist').sum() / len(x) * 100,
        'route_idx': 'nunique',
        'actual_travel_time': 'sum'
    }).round(2)
    
    instance_summary.columns = ['avg_decile_time', 'std_decile_time', 'avg_decile_dist', 'std_decile_dist', 
                               'near_min_pct', 'short_arcs_pct', 'num_routes', 'total_time']
    instance_summary = instance_summary.reset_index()
    
    # 4. Comparación de ratios por tipo
    ratios_by_type = global_df.groupby('instance_type').agg({
        'ratio_to_min': 'mean',
        'ratio_to_max': 'mean',
        'ratio_to_min_dist': 'mean',
        'ratio_to_max_dist': 'mean',
        'num_feasible_arcs': 'mean'
    }).round(3).reset_index()
    
    return {
        'deciles_by_type': deciles_by_type,
        'deciles_dist_by_type': deciles_dist_by_type,
        'instance_summary': instance_summary,
        'ratios_by_type': ratios_by_type
    }

def export_global_analysis_excel(global_df: pd.DataFrame, global_metrics: Dict, 
                                comparison_data: Dict, output_path: str = "analisis_global_completo.xlsx"):
    """Exporta análisis global completo a Excel"""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Hoja 1: Datos completos de todos los arcos
        global_df.to_excel(writer, sheet_name='Todos_los_Arcos', index=False)
        
        # Hoja 2: Resumen global
        global_summary_df = pd.DataFrame([{
            'Total_Instancias': global_metrics['total_instances'],
            'Total_Arcos': global_metrics['total_arcs'],
            'Total_Rutas': global_metrics['total_routes'],
            'Pct_Optimos_Tiempo': global_metrics['global_optimal_pct'],
            'Pct_Optimos_Distancia': global_metrics['global_optimal_pct_dist'],
            'Decil_Promedio_Tiempo': global_metrics['global_avg_decile'],
            'Decil_Promedio_Distancia': global_metrics['global_avg_decile_dist']
        }])
        global_summary_df.to_excel(writer, sheet_name='Resumen_Global', index=False)
        
        # Hoja 3: Resumen por tipo de instancia
        type_summary_list = []
        for inst_type, metrics in global_metrics['by_instance_type'].items():
            type_summary_list.append({
                'Tipo_Instancia': inst_type,
                **metrics
            })
        type_summary_df = pd.DataFrame(type_summary_list)
        type_summary_df.to_excel(writer, sheet_name='Resumen_por_Tipo', index=False)
        
        # Hoja 4: Resumen por instancia individual
        comparison_data['instance_summary'].to_excel(writer, sheet_name='Resumen_por_Instancia', index=False)
        
        # Hoja 5: Distribución de deciles por tipo
        comparison_data['deciles_by_type'].to_excel(writer, sheet_name='Deciles_por_Tipo', index=False)
        
        # Hoja 6: Distribución de deciles de distancia por tipo
        comparison_data['deciles_dist_by_type'].to_excel(writer, sheet_name='Deciles_Dist_por_Tipo', index=False)
        
        # Hoja 7: Ratios por tipo
        comparison_data['ratios_by_type'].to_excel(writer, sheet_name='Ratios_por_Tipo', index=False)