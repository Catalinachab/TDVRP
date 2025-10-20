import json, math, argparse, csv
from build_pwl_arc import *
from simulacion import *
from typing import List, Tuple
import os
import pandas as pd

#Duda: intervalos_ruta:list[Tuple] es asi?


def clusters_arcos_ruta(instance_name:str, intervalos_ruta:list[Tuple], arcos_utilizados) -> list[list[tuple]]: 
    '''
    funcion que le pasas una de las rutas de una solucion de una instancia 
    y te devuelve para los intervalos de tiempo de esa ruta que arcos podría haber usado 
    para cada uno. 
    '''
    instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    I = json.load(open(instance))
    TW = I["time_windows"]  # [r_k, d_k]
    ST = I["service_times"]
    clientes = len(TW) - 2 # saco los depositos
    clusters_de_arcos={} # k, v = (intervalo de tiempo, lista de arcos que se podrían haber usado en ese intervalo de tiempo)
    for inter in range(len(intervalos_ruta)):
       intervalo = intervalos_ruta[inter]
       clusters_de_arcos[intervalo] = []
       for i in range(len(TW)):
          #quizas que juanjo chquee esto
          if TW[i][0]<=intervalo[0] and TW[i][1]>intervalo[0]: #veo que la ventana de tiempo del cliente i este dentro del intervalo que queremos analizar
            for j in range(len(TW)):
                # [r_k + s_k + pwl_f] < tw[j][1] ---> limite de factibilidad por ventana de tiempo
                t_cur = TW[i][0]+ST[i]
                if (t_cur+pwl_f(t_cur, i, j, I))<=TW[j][1]:
                    if TW[j][0]<=intervalo[0] and TW[j][1]>intervalo[0]: #hago lo mismo con j
                        if i != j: #chequeas que sea un arco optimo
                            clusters_de_arcos[intervalo].append((i,j)) #se podría usar este arco ij =>lo guardo como una tupla
    return clusters_de_arcos

# intervalo: [0,10][10,20]
#arco1-2:[5,8]
#arco1-3: [4,9]
#arco4-5 : [11,18]
#lo q devuelve clusters_arcos_ruta = [ [(1,2),(1,3)], [(4,5)] ] 
    # primer pos de esta lista es los arcos que podes usar en intervalo [0,10]


def duracion_arcos(clusters_arcos:dict[tuple, list[tuple]], intervalos_ruta:list[Tuple], instance_name:str, epsilon, cant_muestras)-> list[list[float]]:
    '''
    esta funcion recibe una lista de los arcos factibles por cada arco de una ruta de la solucion y 
    devuelve una lista de listas con las duraciones de cada arco factible

    - clusters_arcos -> list:list:tuple (ruta:intervalos:arcos) = arcos factibles para cada intervalo [lo que devuelve clusters_arcos_ruta]
    - intervalos_ruta: -> list:list (ruta:intervalos-segun-bkpts) = 
    - epsilon es la diferencia +-t que usamos para calcular los intervalos
    - cant_muestras es la cantidad de muestras que tomamos en cada intervalo para calcular la duracion del arco

        
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
    instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    instance  = json.load(open(instance))
    for intervalo, arcos in clusters_arcos.items():
        res_temporal = [] # aca ponemos la duracion de cada arco
        res_dict[intervalo] = []
        for arco in arcos:

            int_epsilon = [intervalos_ruta[int_idx][0]-epsilon, intervalos_ruta[int_idx][0]+epsilon]
            d = []
            for m in range(cant_muestras):
                # siempre calculamos la duracion partiendo de un t_i, pero ahora tenemos un intervalo del que pueden partir. ¿cómo elegimos ese t_i inicial? --> promediando varios puntos dentro del intervalo
                t_salida = int_epsilon[0] + m*(int_epsilon[1]-int_epsilon[0])/(cant_muestras-1)
                duracion = pwl_f(t_salida, arco[0], arco[1], instance) 
                d.append(duracion)
            
            dict_arco = {
                "arc": arco,
                "durations": {
                    "start": d[0],
                    "mean": sum(d)/len(d),
                    "minimo": min(d),
                    "maximo": max(d),
                    "end": d[-1]
                }
            }
            res_dict[intervalo].append(dict_arco)
        
        int_idx +=1

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


    '''
    for i in range(len(arcos_factibles)): #recorres los intervalos
        res.append([])

        duracion_optima = ruta[i][3]
        minimo = float('inf')
        maximo = 0
        for j in range(len(arcos_factibles[i])): #recorres los arcos factibles para un intervalo y t quedas con max y min
            if duraciones[i][j]!= 0 and duraciones[i][j] > maximo: 
                maximo = duraciones[i][j]
            if duraciones[i][j]!= 0 and duraciones[i][j] < minimo:
                minimo = duraciones[i][j]
        if(maximo==0):
            res[i].append((duracion_optima/minimo, None))
        else: res[i].append((duracion_optima/minimo, duracion_optima/maximo))
        
        # si duracion_optima/minimo = 1 => el arco optimo es el "mejor"
        # si duracion_optima/maximo = 1 => el arco optimo es el "peor"
        
        # para ambas divisiones: mientras mas cerca a 1, más cerca del minimo o máximo
        #   "   "       "      : dominio [0; inf]

        # visualizo que tan lejos estoy del minimo y maximo en valor absoluto         
    return res 
    '''
            

def analizar_metricas_solutions(solutions_file, instancias_dir, output_file="metricas_resultados.xlsx"):
    resultados = []
    rows = []
    with open(solutions_file, "r") as f:
        all_solutions = json.load(f)
    i=0
    for solution in all_solutions:
        instance_name = solution["instance_name"]
        rutas = solution["routes"]
        instance_path = os.path.join(instancias_dir, instance_name + ".json")
        with open(instance_path, "r") as inst_file:
            instance_data = json.load(inst_file)
        time_departures, error = simulacion(solution, instance_data)

        for idx_ruta, ruta in enumerate(rutas):
            path = ruta["path"]
            intervalos_ruta = []
            td_ruta = time_departures[idx_ruta]
            for i in range(len(td_ruta)-1):
                inter = (td_ruta[i][2], td_ruta[i+1][2])
                intervalos_ruta.append(inter)
            arcos_utilizados = [(path[i], path[i+1]) for i in range(len(path)-1)]
            arcos_factibles = clusters_arcos_ruta(instance_name, intervalos_ruta, arcos_utilizados)
            #duracion_arcos_factibles = duracion_arcos(arcos_factibles, intervalos_ruta, instance_name)
            epsilon = 0.1
            cant_muestras = 5
            duracion_arcos_factibles = duracion_arcos(arcos_factibles, intervalos_ruta, instance_name, epsilon, cant_muestras)
            metricas_res, metricas_str, _ = metricas(arcos_factibles, duracion_arcos_factibles ,time_departures, idx_ruta)
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
        "Observacion general": "En general, está más cerca del mínimo." if cerca_min > cerca_max else "En general, está más cerca del máximo."
    }
    df = pd.DataFrame(rows)
    resumen_df = pd.DataFrame([resumen])
    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, index=False, sheet_name="Detalle")
        resumen_df.to_excel(writer, index=False, sheet_name="Resumen")
    i+=1


analizar_metricas_solutions("data//instancias-dabia_et_al_2013/solutions.json", "data/instancias-dabia_et_al_2013", output_file="metricas_resultados.xlsx")


# --------------------------------------------------------------------
# 🔹 NUEVO BLOQUE: Distribución por deciles + gráficos por tipo
# --------------------------------------------------------------------
import matplotlib.pyplot as plt

def analizar_distribucion_por_deciles(solutions_file, instancias_dir, output_file="metricas_distribucion.xlsx"):
    """
    Calcula la posición relativa (0–1) de cada duración óptima dentro del rango [min, max]
    y genera una distribución por deciles, segmentada por tipo de instancia (C, R, RC).
    También guarda gráficos .png con los histogramas.
    """
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

        epsilon = 0.1
        cant_muestras = 5

        for idx_ruta, ruta in enumerate(rutas):
            path = ruta["path"]
            intervalos_ruta = [
                (time_departures[idx_ruta][i][2], time_departures[idx_ruta][i + 1][2])
                for i in range(len(time_departures[idx_ruta]) - 1)
            ]
            arcos_utilizados = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            arcos_factibles = clusters_arcos_ruta(instance_name, intervalos_ruta, arcos_utilizados)
            duracion_arcos_factibles = duracion_arcos(
                arcos_factibles, intervalos_ruta, instance_name, epsilon, cant_muestras
            )
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

    # --- crear DataFrame ---
    df = pd.DataFrame(distribucion)
    resumen = df.groupby(["tipo", "decil"]).size().reset_index(name="count")

    # --- guardar a Excel ---
    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, index=False, sheet_name="Datos crudos")
        resumen.to_excel(writer, index=False, sheet_name="Distribución por deciles")

    print(f"✅ Archivo con distribución guardado en: {output_file}")

    # --- generar gráficos por tipo ---
    tipos = resumen["tipo"].unique()
    for tipo in tipos:
        df_tipo = resumen[resumen["tipo"] == tipo]
        plt.figure(figsize=(8, 5))
        plt.bar(df_tipo["decil"], df_tipo["count"], color="steelblue", edgecolor="black")
        plt.title(f"Distribución por deciles - Tipo {tipo}")
        plt.xlabel("Decil (posición relativa)")
        plt.ylabel("Cantidad de arcos")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f"distribucion_{tipo}.png", dpi=300)
        plt.close()
        print(f"📊 Gráfico guardado: distribucion_{tipo}.png")


# Ejecutar el nuevo análisis con gráficos
analizar_distribucion_por_deciles(
    "data//instancias-dabia_et_al_2013/solutions.json",
    "data/instancias-dabia_et_al_2013",
    output_file="metricas_distribucion.xlsx"
)
