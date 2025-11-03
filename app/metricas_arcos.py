import json, math, argparse, csv
from build_pwl_arc import *
from simulacion import *
from typing import List, Tuple
import pandas as pd

#Duda: intervalos_ruta:list[Tuple] es asi?
#?Duda: habria que usar la de clusters_arcos alterntiva? 
#? La que devuelve todos los arcos factibles partiendodesde el mismo cliente origen que la solución óptima (path[i]). 

#
def clusters_arcos_ruta(instance_data: dict, intervalos_ruta: list[Tuple], arcos_utilizados) -> dict[tuple, list[tuple]]: 
    '''
    funcion que le pasas una de las rutas de una solucion de una instancia 
    y te devuelve para los intervalos de tiempo de esa ruta que arcos podría haber usado 
    para cada uno.
    
    Args:
        instance_data: Diccionario con datos de la instancia (EN MEMORIA)
        intervalos_ruta: Lista de tuplas con intervalos de tiempo
        arcos_utilizados: Lista de arcos usados en la ruta
    '''
    I = instance_data 
    TW = I["time_windows"]  # [r_k, d_k]
    ST = I["service_times"]
    clientes = len(TW) - 2 # saco los depositos
    clusters_de_arcos = {} # k, v = (intervalo de tiempo, lista de arcos que se podrían haber usado en ese intervalo de tiempo)
    
    for inter in range(len(intervalos_ruta)):
        intervalo = intervalos_ruta[inter]
        clusters_de_arcos[intervalo] = []
        for i in range(len(TW)):
            #quizas que juanjo chquee esto
            if TW[i][0] <= intervalo[0] and TW[i][1] > intervalo[0]: #veo que la ventana de tiempo del cliente i este dentro del intervalo que queremos analizar
                for j in range(len(TW)):
                    # [r_k + s_k + pwl_f] < tw[j][1] ---> limite de factibilidad por ventana de tiempo
                    t_cur = TW[i][0] + ST[i]
                    if (t_cur + pwl_f(t_cur, i, j, I)) <= TW[j][1]:
                        if TW[j][0] <= intervalo[0] and TW[j][1] > intervalo[0]: #hago lo mismo con j
                            if i != j: #chequeas que sea un arco optimo
                                clusters_de_arcos[intervalo].append((i, j)) #se podría usar este arco ij =>lo guardo como una tupla
    return clusters_de_arcos


def duracion_arcos(clusters_arcos: dict[tuple, list[tuple]], intervalos_ruta: list[Tuple], 
                   instance_data: dict, epsilon: float, cant_muestras: int) -> dict:
    '''
    esta funcion recibe una lista de los arcos factibles por cada arco de una ruta de la solucion y 
    devuelve una lista de listas con las duraciones de cada arco factible

    Args:
        clusters_arcos: dict de arcos factibles por intervalo
        intervalos_ruta: lista de intervalos de tiempo
        instance_data: Diccionario con datos de la instancia (EN MEMORIA)
        epsilon: diferencia ±t para calcular intervalos
        cant_muestras: cantidad de muestras por intervalo
        
    Retorna un diccionario:
      {
        intervalo_tuple: [
            {
              "arc": (i, j),
              "durations": {"start": float, "mean": float, "end": float}
            },
            ...
        ],
        ...
      }
    '''
    res_dict = {}
    int_idx = 0
    instance = instance_data  # ✅ Ya no lee archivo
    
    for intervalo, arcos in clusters_arcos.items():
        res_temporal = [] # aca ponemos la duracion de cada arco
        res_dict[intervalo] = []
        for arco in arcos:
            int_epsilon = [intervalos_ruta[int_idx][0] - epsilon, intervalos_ruta[int_idx][0] + epsilon]
            d = []
            for m in range(cant_muestras):
                # siempre calculamos la duracion partiendo de un t_i, pero ahora tenemos un intervalo del que pueden partir. ¿cómo elegimos ese t_i inicial? --> promediando varios puntos dentro del intervalo
                t_salida = int_epsilon[0] + m * (int_epsilon[1] - int_epsilon[0]) / (cant_muestras - 1)
                duracion = pwl_f(t_salida, arco[0], arco[1], instance) 
                d.append(duracion)
            
            dict_arco = {
                "arc": arco,
                "durations": {
                    "start": d[0],
                    "mean": sum(d) / len(d),
                    "minimo": min(d),
                    "maximo": max(d),
                    "end": d[-1]
                }
            }
            res_dict[intervalo].append(dict_arco)
        
        int_idx += 1

    return res_dict


def metricas(arcos_factibles: dict, duraciones: dict, time_departures, idx_ruta):
    '''
    Calcula ratios, clasifica más cerca del min/max (como antes)
    y además devuelve las posiciones relativas (rels) para análisis por deciles.
    '''
    ruta = time_departures[idx_ruta]
    res: List[List[Tuple]] = []   # [(ratio_min, ratio_max)] por intervalo
    res_str = []                  # texto descriptivo por intervalo
    rels = []                     # lista plana de valores relativos (0–1)

    for idx, (intervalo, arcos) in enumerate(arcos_factibles.items()):
        res.append([])
        duracion_optima = ruta[idx][3]

        # juntar todos los valores posibles
        todos_los_valores = []
        dur_entries = duraciones.get(intervalo, [])
        for entry in dur_entries:
            durs = entry.get("durations", {})
            todos_los_valores.extend([
                durs.get("start", 0.0),
                durs.get("mean", 0.0),
                durs.get("minimo", 0.0),
                durs.get("maximo", 0.0),
                durs.get("end", 0.0),
            ])

        valores_validos = [v for v in todos_los_valores if v and v > 0]

        if valores_validos:
            minimo = min(valores_validos)
            maximo = max(valores_validos)
        else:
            minimo, maximo = 0.0, 0.0

        ratio_min = None if minimo == 0 else duracion_optima / minimo
        ratio_max = None if maximo == 0 else duracion_optima / maximo
        res[idx].append((ratio_min, ratio_max))

        # cálculo relativo para histograma
        if maximo == minimo or (maximo == 0 and minimo == 0):
            rel = None
            res_str.append("todas las duraciones son iguales o nulas")
        else:
            rel = (duracion_optima - minimo) / (maximo - minimo)
            rel = max(0, min(rel, 1))  # asegurar entre 0 y 1
            res_str.append("mas cerca del min" if rel < 0.5 else "mas cerca del max")

        if rel is not None:
            rels.append(rel)

    # devuelvo TODO lo anterior + rels nuevos
    return res, res_str, rels

def metrica_distancia(arcos_factibles: dict, distancias, path):
    
    res: List[List[Tuple]] = []   # [(ratio_min, ratio_max)] por intervalo
    res_str = []                  # texto descriptivo por intervalo
    rels = []                     # lista plana de valores relativos (0–1)

    for idx, (intervalo, arcos) in enumerate(arcos_factibles.items()):
        res.append([])
        distancia_optima = path[idx]
        minimo = 100000000
        maximo = 0
        prom = 0
        for arco in arcos:
            i, j = arco
            dist = distancias[i][j]
            if dist<minimo: minimo = dist
            if dist>maximo: maximo = dist
            prom +=dist
        prom = prom/len(arcos)

        ratio_min = None if minimo == 0 else distancia_optima / minimo
        ratio_max = None if maximo == 0 else distancia_optima / maximo
        res[idx].append((ratio_min, ratio_max))

        # cálculo relativo para histograma
        if maximo == minimo or (maximo == 0 and minimo == 0):
            rel = None
            res_str.append("todas las distancias son iguales o nulas")
        else:
            rel = (distancia_optima - minimo) / (maximo - minimo)
            rel = max(0, min(rel, 1))  # asegurar entre 0 y 1
            res_str.append("arco corto" if rel < 0.5 else "arco largo") #entiendo que arco corto seria que es un arco mas cerca del arco de minima distancia
            #res_str.append("mas cerca de la min dist" if rel < 0.5 else "mas cerca de la max dist")

        if rel is not None:
            rels.append(rel)

    # devuelvo TODO lo anterior + rels nuevos
    return res, res_str, rels

