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
                     epsilon: float, cant_muestras: int = 10) -> pd.DataFrame:
    """
    Ejecuta el análisis completo sobre un par instancia-solución.
    """

    results = []
    
    routes = solution_data.get("routes", [])
    if not routes:
        raise ValueError(f"La solución para {instance_name} no contiene rutas")
    
    time_departures, error = simulacion(solution_data, instance_data)
    if error:
        print(f"⚠️ Advertencia: Error en simulación de {instance_name}")
    
    for idx_ruta, route in enumerate(routes):
        path = route["path"]
        t0 = route["t0"]

        intervalos_ruta = []
        td_ruta = time_departures[idx_ruta]
        for i in range(len(td_ruta) - 1):
            inter = (td_ruta[i][2], td_ruta[i+1][2])
            intervalos_ruta.append(inter)

        arcos_utilizados = [(path[i], path[i+1]) for i in range(len(path) - 1)]
        arcos_factibles = clusters_arcos_ruta(instance_data, intervalos_ruta, arcos_utilizados)
        
        duracion_arcos_factibles = duracion_arcos(
            arcos_factibles, intervalos_ruta, instance_data, epsilon, cant_muestras
        )
        
        metricas_res, metricas_str, rels = metricas(
            arcos_factibles, duracion_arcos_factibles, time_departures, idx_ruta
        )

        distancias = instance_data["distances"]
        metricas_res_dist, metricas_str_dist, _ = metrica_distancia(arcos_factibles, distancias, path)

        for idx_arco, (intervalo, arcos) in enumerate(arcos_factibles.items()):
            arco_usado = arcos_utilizados[idx_arco]

            # ---- DURATIONS WITH SAMPLING (epsilon) ----
            dur_entries = duracion_arcos_factibles.get(intervalo, [])
            
            # ✅ usar TODAS las muestras (no solo el mean)
            duraciones = []
            for entry in dur_entries:
                if "samples" in entry["durations"]:
                    duraciones.extend([v for v in entry["durations"]["samples"] if v > 0])
                else:
                    # fallback si no hay samples (no debería pasar)
                    duraciones.append(entry["durations"]["mean"])

            # datos factibles
            min_dur = min(duraciones) if duraciones else None
            max_dur = max(duraciones) if duraciones else None
            
            # ✅ duración óptima real de la simulación
            duracion_optima = td_ruta[idx_arco][3]
            chosen_duration = duracion_optima

            # ratios
            ratio_min = chosen_duration / min_dur if (min_dur and min_dur > 0) else None
            ratio_max = chosen_duration / max_dur if (max_dur and max_dur > 0) else None

            # ✅ decil basado en TODAS las muestras factibles
            decile = _calculate_decile(chosen_duration, duraciones) if duraciones else None

            proximity = metricas_str[idx_arco] if idx_arco < len(metricas_str) else "desconocido"
            coords = _get_node_coordinates(instance_data, arco_usado[0], arco_usado[1])

            # ---- DISTANCE METRICS ----
            dists = []
            for (ii, jj) in arcos:
                dij = distancias[ii][jj]
                if dij is not None and dij > 0:
                    dists.append(dij)

            chosen_dist = distancias[arco_usado[0]][arco_usado[1]] if distancias[arco_usado[0]][arco_usado[1]] is not None else 0.0
            min_dist = min(dists) if dists else chosen_dist
            max_dist = max(dists) if dists else chosen_dist
            ratio_min_dist = (chosen_dist / min_dist) if (min_dist and min_dist > 0) else None
            ratio_max_dist = (chosen_dist / max_dist) if (max_dist and max_dist > 0) else None
            distance_decile = _calculate_decile(chosen_dist, dists) if len(dists) > 0 else None

            results.append({
                'route_idx': idx_ruta,
                'arc_idx': idx_arco,
                'arc_id': f"{arco_usado[0]}-{arco_usado[1]}",
                'node_from': arco_usado[0],
                'node_to': arco_usado[1],
                'departure_time': intervalo[0],
                'actual_travel_time': chosen_duration,
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
                'node_to_lon': coords[3],

                'chosen_distance': chosen_dist,
                'min_feasible_distance': min_dist,
                'max_feasible_distance': max_dist,
                'ratio_to_min_dist': ratio_min_dist,
                'ratio_to_max_dist': ratio_max_dist,
                'distance_decile': distance_decile,
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



def create_distance_decile_histogram_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara datos para el histograma de deciles pero en términos de DISTANCIA,
    usando la columna 'distance_decile' que agregamos en run_full_analysis.
    """
    if 'distance_decile' not in analysis_df.columns:
        raise ValueError("distance_decile no existe en analysis_df. Asegurate de actualizar run_full_analysis.")

    dec_counts = analysis_df['distance_decile'].value_counts().sort_index()
    return pd.DataFrame({
        'DecilDist': dec_counts.index,
        'Cantidad de Arcos': dec_counts.values,
        'Porcentaje': (dec_counts.values / len(analysis_df) * 100)
    })


def create_distance_histogram_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara datos para el histograma de distancias (arco corto vs largo).
    """
    dist_counts = analysis_df['longitud arco'].value_counts()

    return pd.DataFrame({
        'Categoria Distancia': dist_counts.index,
        'Cantidad de Arcos': dist_counts.values,
        'Porcentaje': (dist_counts.values / len(analysis_df) * 100)
    })


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