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
    TW = I["time_windows"]  
    clientes = len(TW) - 2 # saco los depositos
    arcos=[] #cada pos tiene una lista de arcos q se pueden usar en ese intervalo i con 3 intervalos 
    for inter in range(len(intervalos_ruta)):
       intervalo = intervalos_ruta[inter]
       arcos.append([])
       for i in range(len(TW)):
          #quizas que juanjo chquee esto
          if TW[i][0]<=intervalo[0] and TW[i][1]>intervalo[0]: #veo que la ventana de tiempo del cliente i este dentro del intervalo que queremos analizar
            for j in range(len(TW)):
                if TW[j][0]<=intervalo[0] and TW[j][1]>intervalo[0]: #hago lo mismo con j
                    if i != j: #chequeas que sea un arco optimo
                        arcos[inter].append((i,j)) #se podría usar este arco ij =>lo guardo como una tupla
    return arcos

# intervalo: [0,10][10,20]
#arco1-2:[5,8]
#arco1-3: [4,9]
#arco4-5 : [11,18]
#lo q devuelve clusters_arcos_ruta = [[(1,2),(1,3)],[(4,5)]] 
    # primer pos de esta lista es los arcos que podes usar en intervalo [0,10]


def duracion_arcos(arcos:list[list[tuple]], intervalos_ruta:list[Tuple], instance_name:str)-> list[list[float]]:
    '''
    esta funcion recibe una lista de los arcos factibles por cada arco de una ruta de la solucion y 
    devuelve una lista de listas con las duraciones de cada arco factible
    - arcos -> list:list:tuple (ruta:intervalos:arcos) = arcos factibles para cada intervalo [lo que devuelve clusters_arcos_ruta]
    - intervalos_ruta: -> list:list (ruta:intervalos-segun-bkpts) = 
    '''
    res = [] # la lista de listas para cada intervalo
    int_idx = 0
    instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    instance  = json.load(open(instance))
    for intervalo in arcos:
        res_temporal = [] # aca ponemos la duracion de cada arco
        for arco in intervalo:
            duracion = pwl_f(intervalos_ruta[int_idx][0], arco[0], arco[1], instance) #intervalo[0] seria el t 
            res_temporal.append(duracion)
        res.append(res_temporal)
        int_idx +=1
    return res


def metricas(arcos_factibles:list[list[tuple]],duraciones, time_departures, idx_ruta):
    '''
    recibiria por intervalo todos los arcos factibles y calcula las duraciones de cada arco 
    y busca segun la duracion el minimo y el maximo de los arcos 
    y luego calcula duracion_optima/minimo y duracion_optima/maximo.
    Duda: es nada mas para un intervalo?
    '''
    ruta = time_departures[idx_ruta]
    res:List[List[Tuple]] = [] # para cada el primer valor es la (duracion_optima / minimo )y el segundo valor es la (duracion_optima / maximo) 
    res_str = []
    for i in range(len(arcos_factibles)): #recorres los intervalos
        res.append([])
        res_str.append([])
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
        if maximo == minimo:
            res_str.append("todas las duraciones son iguales")
        else:
            rel = (duracion_optima - minimo) / (maximo - minimo) #que juanjo chequee esto
            if rel < 0.5:
                res_str.append("mas cerca del min")
            else:
                res_str.append("mas cerca del max")

       

    return res, res_str
            

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


