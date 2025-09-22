import json, math, argparse, csv
from build_pwl_arc import *

def pwl_f(t:float, i:int, j:int, instance:dict) -> tuple:
    '''
    devuelve (t, y) donde y es el tiempo de viaje en el arco (i,j) si se sale en t
    '''
    # ver entre que 2 bkpts esta t
    # calcular la pendiente = (y2-y1)/(x2-x1)
    # para ver que y corresponde a t en (t, y) de la pwl de time ...?
    #    instance_path = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    #    I = json.load(open(instance_path))
    I = instance
    D = I["distances"][i][j]
    cid = I["clusters"][i][j]
    VZ = I["cluster_speeds"][cid]
    Zs = Z(I); per = P(I)
    pts = tau_pts(D, VZ, Zs, per)
    for i in range(len(pts)-1):
        if t >= pts[i][0] and t <= pts[i+1][0]:
            m = (pts[i+1][1] - pts[i][1])/(pts[i+1][0] - pts[i][0]) #pendiente
            ord_origen = pts[i][1] - (m * pts[i][0]) #ordenada al origen
            y = m * t + ord_origen
            return y 

INFTY = 10e8; EPS = 10e-6
def epsilon_equal(a, b): return abs(a - b) < EPS
def epsilon_bigger(a, b): return a > b + EPS 
# Returns: the travel time of arc (i, j) if departing at t0.
def travel_time(instance, i, j, t0):
	c = instance["clusters"][i][j]
	T = instance["speed_zones"]
	v = instance["cluster_speeds"]

	# Find speed slot T_k that includes t0.
	k = min(i for i in range(0,len(T)) if t0 >= T[i][0] and t0 <= T[i][1])

	# Travel time algorithm from Ichoua et al.
	t = t0
	d = instance["distances"][i][j]
	tt = t + d / v[c][k]
	while tt > T[k][1]:
		d = d - v[c][k] * (T[k][1] - t)
		t = T[k][1]
		if epsilon_equal(d, 0): break
		if epsilon_bigger(d, 0) and k+1 == len(T): return INFTY
		tt = t + d / v[c][k+1]
		k = k + 1
	return tt - t0

def simulacion(solution, instance):
    '''
    devuelve el time_departures para cada ruta de esa instancia particular
    '''
    epsilon = 0.1

    # instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
    # entrar a la instancia para extraer la ventana de tiempo
    # I = json.load(open(instance))

    I = instance
    
    print(f"Instancia: {instance_name}")

    TW = I["time_windows"]
    ST = I["service_times"]
    idx_route = 0 

    res = []

    for route in solution["routes"]:
        t0 = route["t0"]
        path = route["path"]
        time_departures = []
        t_i = t0 # tiempo actual

        # recorrer la ruta y calcular los tiempos de salida de cada arco
        i = 0
        while i < (len(path)-1):
            time_window = TW[path[i]] #ventana de tiempo del cliente i 

            if time_window[0] > t_i: # si t_i esta fuera de la ventana de tiempo, hay que esperar => sumar la espera
                t_i+=(time_window[0] - t_i)
            
            # dur_viaje = pwl_f(t_i, path[i], path[i+1], instance)
            dur_viaje = travel_time(I, path[i], path[i+1], t_i)
            

            time_departures.append([path[i], path[i+1], t_i,dur_viaje])
            # t_i+=y
            ###########
            #todo: NO TENIAMOS EN CUENTA EL TIEMPO QUE TARDA EN ATENDER/SERVIR AL CLIENTE (ej. en descargar el combustible a la estacion de servicio)
            # en las instancias: cada valor en "service_times" corresponde a un nodo (cliente) del problema
            service_time = ST[path[i]] # tiempo de servicio en el cliente i
            t_i+=dur_viaje+service_time # todo: al t actual le sumo el tiempo de viaje + el tiempo de servicio en el cliente i
            ###########
            i+=1

        # si nos acercamos a la duracion total de la solucion, estamos bien.
        duration = route["duration"] 
        duracion_nuestra = (t_i - t0)
        diferencia = duracion_nuestra - duration
        if abs(diferencia) <= epsilon:
            print(
                f"[funcionó] Ruta: {idx_route}"
                f"  - Duración calculada: {(t_i - t0):.2f} | esperada:  {duration:.2f}"
            )
        else: 
            print(
                f"[no funcionó] Ruta: {idx_route}    |   Diferencia de duración: {diferencia:.2f}\n"
                f"  - Duración calculada: {(t_i - t0):.2f} | esperada:  {duration:.2f}"
            )
        idx_route+=1
        # calcular t1 = t0 + duracion arco (t0, client) si esta dentro de la ventana de tiempo
        
        res.append(time_departures)

    return res

if __name__ == "__main__":
    path_s = "TDVRP\data\instancias-dabia_et_al_2013\solutions.json"
    solutions = json.load(open(path_s))
    instance_name = "R102_100"

    for s in solutions:
        if s["instance_name"] == instance_name:
            solution = s
            break

    path_i = f"TDVRP\data\instancias-dabia_et_al_2013\{instance_name}.json"
    instance = json.load(open(path_i))
    simulacion(solution, instance)  
