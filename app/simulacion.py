import json, math, argparse, csv
from build_pwl_arc import *

def pwl_f(t: float, i: int, j: int, instance: dict) -> float:
    '''
    devuelve (t, y) donde y es el tiempo de viaje en el arco (i,j) si se sale en t usando fwd
    tq fwd es la funcion que calcula el tiempo de viaje en un arco (i,j) saliendo en t, teniendo en cuenta los cambios de velocidad según las zonas de velocidad
    '''
    I = instance
    D = I["distances"][i][j]
    cid = I["clusters"][i][j]
    VZ = I["cluster_speeds"][cid]
    Zs = Z(I)
    per = P(I)
    Zs = Z(I)
    return fwd(D, t, VZ, Zs, per)


INFTY = 10e8; EPS = 10e-6
def epsilon_equal(a, b): return abs(a - b) < EPS
def epsilon_bigger(a, b): return a > b + EPS

def simulacion(solution, instance):
    '''
    devuelve el time_departures para cada ruta de esa instancia particular
    '''
    diferencia_de_simulacion = 0.1 # tolerancia para la diferencia entre la duracion calculada y la duracion de la solucion

    I = instance
    TW = I["time_windows"]
    ST = I["service_times"]
    idx_route = 0 

    res = []
    mal = 0
    for route in solution["routes"]:
        t0 = route["t0"]
        path = route["path"]
        time_departures = []
        t_i = t0 # tiempo actual

        # recorrer la ruta y calcular los tiempos de salida de cada arco
        i = 0
        while i < (len(path)-1):
            time_window = TW[path[i]] #ventana de tiempo del cliente i 
            service_time = ST[path[i]] # tiempo de servicio en el cliente i -- en las instancias: cada valor en "service_times" corresponde a un nodo (cliente) del problema

            t_i = max(t_i, time_window[0]) + service_time # si llego antes de la ventana, espero hasta que abra + el tiempo de servicio

            dur_viaje = pwl_f(t_i, path[i], path[i+1], instance)          

            time_departures.append([path[i], path[i+1], t_i,dur_viaje])
           
            t_i += dur_viaje
            i+=1

        # si nos acercamos a la duracion total de la solucion, la simulación/replicación tiene sentido.
        duration = route["duration"] 
        duracion_nuestra = (t_i - t0)
        diferencia = duracion_nuestra - duration
        if abs(diferencia) >= diferencia_de_simulacion:
            mal+=1
        idx_route+=1
        
        res.append(time_departures)
    error = 0
    if mal > 0: 
         error=1
    return res, error

if __name__ == "__main__":
    
    path_s = f"data/nuevos/solutions.json"
    solutions = json.load(open(path_s))