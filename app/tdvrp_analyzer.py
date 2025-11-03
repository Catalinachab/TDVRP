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
            
            min_dur = min(duraciones) if duraciones else duracion_optima
            max_dur = max(duraciones) if duraciones else duracion_optima
            
            # Calcular ratios
            ratio_min = duracion_optima / min_dur if min_dur > 0 else None
            ratio_max = duracion_optima / max_dur if max_dur > 0 else None
            
            # Calcular decil
            decile = _calculate_decile(duracion_optima, duraciones)
            
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
                'ratio_to_min': ratio_min,
                'ratio_to_max': ratio_max,
                'longitud arco': metricas_str_dist[idx_arco],
                'decile_rank': decile,
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
    """ avg_ratio_min_dist = analysis_df['ratio_to_min_dist'].mean()
    avg_ratio_max_dist = analysis_df['ratio_to_max_dist'].mean() """
    
    
    return {
        'total_arcs': total_arcs,
        'total_routes': analysis_df['route_idx'].nunique(),
        'near_minimum_count': near_min,
        'near_maximum_count': near_max,
        'near_minimum_pct': (near_min / total_arcs * 100) if total_arcs > 0 else 0,
        'avg_decile': avg_decile,
        'optimal_arcs_count': deciles_0_2,
        'optimal_arcs_pct': (deciles_0_2 / total_arcs * 100) if total_arcs > 0 else 0,
        'suboptimal_arcs_count': deciles_7_9,
        'avg_ratio_to_min': avg_ratio_min,
        'avg_ratio_to_max': avg_ratio_max,
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