import json, math, argparse, csv
from build_pwl_arc import *
from simulacion import *
from pathlib import Path

# Primero vamos a partir al horizonte en los diferentes t's de la simulación de la solución para 
# comparar cada arco de la solución con el resto de los arcos factibles de usar en ese t

path = 'data/instancias-dabia_et_al_2013/solutions.json'
# simulacion devuelve un diccionario con:
# para cada instancia (clave):
    # para cada ruta (primer valor de la tupla valor):
        # time_departures (segundo valor de la tupla valor) 
        # o sea, una lista con algo asi: [((i,j), (t_i, duracion_arcoi-j)), ((j,p), (t_j, duracion_arcoj-p)), ...]


# primero tenemos que buscar los arcos factibles en ese t

with open(path) as f:
    solutions = json.load(f)

# armamos los intervalos que dividen el horizonte con esos t's: [t_0, t_0+dur1-2), [t_0+dur1-2, t_0+dur1-2+dur2-3), ...
# => espacio seran los intervalos que vamos a analizar los arcos
espacio:list[tuple] = [] 

for s in solutions:
    instance_name = s["instance_name"]
    instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    I = json.load(open(instance))
    TW = I["time_windows"]
    rutas = s["routes"]
    for i in range(rutas):
        ruta = rutas[i]
    intervalos = simulacion(path, instance_name)  
    
        intervalo_ruta = sim[in    ce_name][i] # el time_departures de la ruta i de la intstance_name        
        # ahora quiero acintervalos[i]arlo a espacio
             
        for i in intervalo_ruta:
             a=1
            #todos los arcos de esa isntancia que se podrian usar en ese intervalo de tiempo  
        #vemos para ese intervalo todos los arcos posibles y calculamos el tiempo que tardan 
        #y dsp comparamos con el arco elegido optimo
       
    