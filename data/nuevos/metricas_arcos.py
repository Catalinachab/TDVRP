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


def metricas(arcos_factibles:dict,duraciones:dict, time_departures, idx_ruta):
    '''
    recibiria por intervalo todos los arcos factibles y calcula las duraciones de cada arco 
    y busca segun la duracion el minimo y el maximo de los arcos 
    y luego calcula duracion_optima/minimo y duracion_optima/maximo.

    arcos_factibles: dict { intervalo_tuple: [(i,j), ...], ... }
    duraciones: dict { intervalo_tuple: [ { "arc": (i,j), "durations": {"start":..,"mean":..,"minimo": .., "maximo:..,"end":..} }, ... ], ... }
    '''
    ruta = time_departures[idx_ruta]
    res:List[List[Tuple]] = [] # en cada tupla el primer valor es la (duracion_optima / minimo ) y el segundo valor es la (duracion_optima / maximo) 

    res_str = []
    for idx, (intervalo, arcos) in enumerate(arcos_factibles.items()):
        res.append([])
        duracion_optima = ruta[idx][3]
        minimo = float('inf')
        maximo = 0.0

        dur_entries = duraciones.get(intervalo, [])
        for entry in dur_entries:
            val = entry.get("durations", {}).get("mean", 0.0)
            if val != 0 and val > maximo:
                maximo = val
            if val != 0 and val < minimo:
                minimo = val

        if minimo == float('inf'):
            minimo = 0.0

        ratio_min = None if minimo == 0 else duracion_optima / minimo
        ratio_max = None if maximo == 0 else duracion_optima / maximo

        res[idx].append((ratio_min, ratio_max))

        if maximo == minimo:
            res_str.append("todas las duraciones son iguales")
        else:
            denom = (maximo - minimo)
            # evitar división por cero (ya cubrimos caso maximo==minimo arriba)
            rel = 0.0 if denom == 0 else (duracion_optima - minimo) / denom
            res_str.append("mas cerca del min" if rel < 0.5 else "mas cerca del max")
    # res es a qué decil pertenece el optimo para cada intervalo??
    return res, res_str
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
            duracion_arcos_factibles = duracion_arcos(arcos_factibles, intervalos_ruta, instance_name)
            metricas_res, metricas_str = metricas(arcos_factibles, duracion_arcos_factibles ,time_departures, idx_ruta)
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


