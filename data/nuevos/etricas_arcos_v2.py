#!/usr/bin/env python3
import json, math, argparse, csv, os
from build_pwl_arc import *
from simulacion import *
from typing import List, Tuple
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------------------------
# 🔹 FUNCIONES PRINCIPALES
# --------------------------------------------------------------------

def clusters_arcos_ruta_alternativo(instance_name: str, intervalos_ruta: list[Tuple], arcos_utilizados) -> dict:
    '''
    Versión alternativa: devuelve todos los arcos factibles partiendo
    desde el mismo cliente origen que la solución óptima (path[i]).
    Es decir, se fija i y se itera sobre todos los posibles destinos j.
    '''
    instance = f"data/instancias-dabia_et_al_2013/{instance_name}.json"
    I = json.load(open(instance))
    TW = I["time_windows"]
    ST = I["service_times"]

    clusters_de_arcos = {}
    for inter, arco_optimo in zip(intervalos_ruta, arcos_utilizados):
        i = arco_optimo[0]  # fijamos el mismo origen que la solución óptima
        clusters_de_arcos[inter] = []
        for j in range(len(TW)):
            if i == j:
                continue
            t_cur = TW[i][0] + ST[i]
            if (t_cur + pwl_f(t_cur, i, j, I)) <= TW[j][1]:
                clusters_de_arcos[inter].append((i, j))
    return clusters_de_arcos


def duracion_arcos(clusters_arcos: dict[tuple, list[tuple]], intervalos_ruta: list[Tuple],
                   instance_name: str, epsilon, cant_muestras) -> dict:
    '''
    Calcula las duraciones de los arcos factibles para cada intervalo.
    '''
    res_dict = {}
    instance_path = f"data/instancias-dabia_et_al_2013/{instance_name}.json"
    instance = json.load(open(instance_path))
    int_idx = 0
    for intervalo, arcos in clusters_arcos.items():
        res_dict[intervalo] = []
        for arco in arcos:
            int_epsilon = [intervalos_ruta[int_idx][0] - epsilon, intervalos_ruta[int_idx][0] + epsilon]
            d = []
            for m in range(cant_muestras):
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
    Igual que antes: calcula ratios, clasifica más cerca del min/max
    y devuelve también los valores relativos (0–1) para histogramas.
    '''
    ruta = time_departures[idx_ruta]
    res, res_str, rels = [], [], []
    for idx, (intervalo, arcos) in enumerate(arcos_factibles.items()):
        res.append([])
        duracion_optima = ruta[idx][3]
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
        if not valores_validos:
            continue
        minimo, maximo = min(valores_validos), max(valores_validos)
        ratio_min = None if minimo == 0 else duracion_optima / minimo
        ratio_max = None if maximo == 0 else duracion_optima / maximo
        res[idx].append((ratio_min, ratio_max))
        if maximo == minimo:
            rel = None
            res_str.append("todas las duraciones son iguales o nulas")
        else:
            rel = (duracion_optima - minimo) / (maximo - minimo)
            rel = max(0, min(rel, 1))
            res_str.append("mas cerca del min" if rel < 0.5 else "mas cerca del max")
        if rel is not None:
            rels.append(rel)
    return res, res_str, rels


# --------------------------------------------------------------------
# 🔹 ANÁLISIS GENERAL Y EXPORTACIÓN
# --------------------------------------------------------------------

def analizar_metricas_solutions_alternativo(solutions_file, instancias_dir,
                                            output_file="metricas_resultados_alternativo.xlsx"):
    resultados, rows = [], []
    with open(solutions_file, "r") as f:
        all_solutions = json.load(f)

    for solution in all_solutions:
        instance_name = solution["instance_name"]
        rutas = solution["routes"]
        instance_path = os.path.join(instancias_dir, instance_name + ".json")
        with open(instance_path, "r") as inst_file:
            instance_data = json.load(inst_file)
        time_departures, error = simulacion(solution, instance_data)
        epsilon, cant_muestras = 0.1, 5

        for idx_ruta, ruta in enumerate(rutas):
            path = ruta["path"]
            intervalos_ruta = [(time_departures[idx_ruta][i][2], time_departures[idx_ruta][i+1][2])
                               for i in range(len(time_departures[idx_ruta])-1)]
            arcos_utilizados = [(path[i], path[i+1]) for i in range(len(path)-1)]
            arcos_factibles = clusters_arcos_ruta_alternativo(instance_name, intervalos_ruta, arcos_utilizados)
            duracion_arcos_factibles = duracion_arcos(arcos_factibles, intervalos_ruta,
                                                      instance_name, epsilon, cant_muestras)
            metricas_res, metricas_str, _ = metricas(arcos_factibles, duracion_arcos_factibles,
                                                     time_departures, idx_ruta)
            resultados.extend(metricas_str)
            cerca_min_ruta = metricas_str.count("mas cerca del min")
            cerca_max_ruta = metricas_str.count("mas cerca del max")
            if cerca_min_ruta > cerca_max_ruta:
                string = "en general arcos elegidos están mas cerca del min"
            elif cerca_min_ruta == cerca_max_ruta:
                string = "igual cantidad de arcos elegidos cercanos al min y al max"
            else:
                string = "en general arcos elegidos están mas cerca del max"
            rows.append({
                "instancia": instance_name,
                "ruta_numero": idx_ruta,
                "cantidad de arcos": len(intervalos_ruta),
                "cerca_min_ruta": cerca_min_ruta,
                "cerca_max_ruta": cerca_max_ruta,
                "observacion": string,
                "metricas": metricas_res
            })

    cerca_min = resultados.count("mas cerca del min")
    cerca_max = resultados.count("mas cerca del max")
    resumen = {
        "Total mas cerca del min": cerca_min,
        "Total mas cerca del max": cerca_max,
        "Observacion general": "En general, está más cerca del mínimo."
        if cerca_min > cerca_max else "En general, está más cerca del máximo."
    }
    df = pd.DataFrame(rows)
    resumen_df = pd.DataFrame([resumen])
    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, index=False, sheet_name="Detalle")
        resumen_df.to_excel(writer, index=False, sheet_name="Resumen")

    print(f"✅ Archivo alternativo generado: {output_file}")


# --------------------------------------------------------------------
# 🔹 NUEVO BLOQUE: Distribución + gráficos por tipo
# --------------------------------------------------------------------

def analizar_distribucion_por_deciles_alternativo(solutions_file, instancias_dir,
                                                  output_file="metricas_distribucion_alternativo.xlsx"):
    distribucion = []
    with open(solutions_file, "r") as f:
        all_solutions = json.load(f)

    for solution in all_solutions:
        instance_name = solution["instance_name"]
        tipo = "RC" if instance_name.startswith("RC") else instance_name[0]
        rutas = solution["routes"]
        instance_path = os.path.join(instancias_dir, instance_name + ".json")
        with open(instance_path, "r") as inst_file:
            instance_data = json.load(inst_file)
        time_departures, error = simulacion(solution, instance_data)
        epsilon, cant_muestras = 0.1, 5

        for idx_ruta, ruta in enumerate(rutas):
            path = ruta["path"]
            intervalos_ruta = [(time_departures[idx_ruta][i][2], time_departures[idx_ruta][i+1][2])
                               for i in range(len(time_departures[idx_ruta])-1)]
            arcos_utilizados = [(path[i], path[i+1]) for i in range(len(path)-1)]
            arcos_factibles = clusters_arcos_ruta_alternativo(instance_name, intervalos_ruta, arcos_utilizados)
            duracion_arcos_factibles = duracion_arcos(arcos_factibles, intervalos_ruta,
                                                      instance_name, epsilon, cant_muestras)
            _, _, rels = metricas(arcos_factibles, duracion_arcos_factibles, time_departures, idx_ruta)
            for r in rels:
                if r is None:
                    continue
                decil = int(r * 10) if r < 1 else 9
                distribucion.append({
                    "instancia": instance_name,
                    "tipo": tipo,
                    "decil": f"{decil/10:.1f}-{(decil+1)/10:.1f}",
                    "valor_relativo": r
                })

    df = pd.DataFrame(distribucion)
    resumen = df.groupby(["tipo", "decil"]).size().reset_index(name="count")
    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, index=False, sheet_name="Datos crudos")
        resumen.to_excel(writer, index=False, sheet_name="Distribución por deciles")
    print(f"✅ Archivo alternativo con distribución guardado en: {output_file}")

    # gráficos por tipo
    tipos = resumen["tipo"].unique()
    for tipo in tipos:
        df_tipo = resumen[resumen["tipo"] == tipo]
        plt.figure(figsize=(8, 5))
        plt.bar(df_tipo["decil"], df_tipo["count"], color="tomato", edgecolor="black")
        plt.title(f"Distribución (ALTERNATIVA) - Tipo {tipo}")
        plt.xlabel("Decil (posición relativa)")
        plt.ylabel("Cantidad de arcos")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f"distribucion_alt_{tipo}.png", dpi=300)
        plt.close()
        print(f"📊 Gráfico alternativo guardado: distribucion_alt_{tipo}.png")


# --------------------------------------------------------------------
# 🔹 EJECUCIÓN
# --------------------------------------------------------------------

analizar_metricas_solutions_alternativo(
    "data//instancias-dabia_et_al_2013/solutions.json",
    "data/instancias-dabia_et_al_2013",
    output_file="metricas_resultados_alternativo.xlsx"
)

analizar_distribucion_por_deciles_alternativo(
    "data//instancias-dabia_et_al_2013/solutions.json",
    "data/instancias-dabia_et_al_2013",
    output_file="metricas_distribucion_alternativo.xlsx"
)
