import json, math, argparse, csv
from build_pwl_arc import *
from simulacion import *
from typing import List, Tuple

# Primero vamos a partir al horizonte en los diferentes t's de la simulación de la solución para 
# comparar cada arco de la solución con el resto de los arcos factibles de usar en ese t

soluciones = 'data/instancias-dabia_et_al_2013/solutions.json'
# simulacion devuelve un diccionario con:
# para cada instancia (clave):
    # para cada ruta (primer valor de la tupla valor):
        # time_departures (segundo valor de la tupla valor) 
        # o sea, una lista con algo asi: [((i,j), (t_i, duracion_arcoi-j)), ((j,p), (t_j, duracion_arcoj-p)), ...]


# primero tenemos que buscar los arcos factibles en ese t

with open(soluciones) as f:
    solutions = json.load(f)

# armamos los intervalos que dividen el horizonte con esos t's: [t_0, t_0+dur1-2), [t_0+dur1-2, t_0+dur1-2+dur2-3), ...
# => espacio seran los intervalos que vamos a analizar los arcos
espacio:List[Tuple] = [] 

for s in solutions:
    instance_name = s["instance_name"]
    instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    I = json.load(open(instance))
    TW = I["time_windows"]
    rutas = s["routes"]
    intervalos = simulacion(s, instance_name) #esto creo q esta mal
    arcos_utiles = [] #que cada pos sea para  
    for i in range(rutas):
        ruta = rutas[i]
        intervalos_ruta = intervalos[i]
        
        for intervalo in intervalos_ruta:
            a=1
        
    
        # el time_departures de la ruta i de la intstance_name        
        # ahora quiero acintervalos[i]arlo a espacio
             
        for i in intervalo_ruta:
             a=1
            #todos los arcos de esa isntancia que se podrian usar en ese intervalo de tiempo  
        #vemos para ese intervalo todos los arcos posibles y calculamos el tiempo que tardan 
        #y dsp comparamos con el arco elegido optimo

#tmb hay q armar los intervalos      
#arcos_utilizados va a tener q ser una lista de tuplas que son los arcos que se usaron en cada intervalo. La armamos antes de llamar a la funcion.

def clusters_arcos_ruta(instance_name, intervalos_ruta, arcos_utilizados): 
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
    for inter in range(intervalos_ruta):
       intervalo = intervalos_ruta[inter]
       arcos.append([])
       for i in range(TW):
          if TW[i][0]<=intervalo[0] and TW[i][1]>intervalo[0]: #veo que la ventana de tiempo del cliente i este dentro del intervalo que queremos analizar
            for j in range(TW):
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


def duracion_arcos(arcos, intervalos_ruta, instance_name):
    '''
    esta funcion recibe una lista de los arcos factibles por cada arco de una ruta de la solucion y 
    devuelve una lista de listas con las duraciones de cada arco factible
    - arcos -> list:list:tuple (ruta:intervalos:arcos) = arcos factibles para cada intervalo [lo que devuelve clusters_arcos_ruta]
    - intervalos_ruta: -> list:list (ruta:intervalos-segun-bkpts) = 
    '''
    res = [] # la lista de listas para cada intervalo
    int_idx = 0
    for intervalo in arcos:
        res_temporal = [] # aca ponemos la duracion de cada arco
        for arco in intervalo:
            duracion = pwl_f(intervalos_ruta[int_idx][0], arco[0], arco[1], instance_name) #intervalo[0] seria el t 
            res_temporal.append(duracion)
        res.append(res_temporal)
        int_idx +=1
    return res


def metricas(arcos_factibles, time_departures, idx_ruta):
    ruta = time_departures[idx_ruta]
    res:List[Tuple] = [] # para cada el primer valor es la (duracion_optima / minimo )y el segundo valor es la (duracion_optima / maximo) 
    res_str = []
    for i in range(arcos_factibles):
        duracion_optima = ruta[i][3]
        minimo = float('inf')
        maximo = 0
        for duracion in arcos_factibles[i]:
            if duracion > maximo:
                maximo = duracion
            if duracion < minimo:
                minimo = duracion
        res.append((duracion_optima/minimo, duracion_optima/maximo))
        
        # si duracion_optima/minimo = 1 => el arco optimo es el "mejor"
        # si duracion_optima/maximo = 1 => el arco optimo es el "peor"
        
        # para ambas divisiones: mientras mas cerca a 1, más cerca del minimo o máximo
        #   "   "       "      : dominio [0; inf]

        # visualizo que tan lejos estoy del minimo y maximo en valor absoluto
        distancia_1_min = abs(1 - (duracion_optima/minimo))
        distancia_1_max = abs(1 - (duracion_optima/maximo))
        if distancia_1_min < distancia_1_max:
            res_str.append("mas cerca del min")
        else:
            res_str.append("mas cerca del max")
    
    return res, res_str
            
    