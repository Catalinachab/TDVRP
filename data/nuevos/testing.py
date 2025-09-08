from build_pwl_arc import *
import json, math, argparse, csv
index_path = 'data/instancias-dabia_et_al_2013/index.json'

with open(index_path) as f:
    instances = json.load(f)
instance_path = "data/instancias-dabia_et_al_2013/C101_25.json"

I = json.load(open(instance_path))
Zs = Z(I)
per = P(I)
n = len(I["distances"]) 

D = I["distances"][0][23]
cid = I["clusters"][0][23]
VZ = I["cluster_speeds"][cid]
# Calcular puntos de τ (instante de salida, duración del viaje) para arco i->j
pts = tau_pts(D, VZ, Zs, per)

# tau_vals es la lista de duraciones del viaje
tau_vals = [tau for _, tau in pts]
# Estadísticas descriptivas
tau_min = min(tau_vals) # duración mínima del viaje
tau_max = max(tau_vals) # duración máxima del viaje
tau_mean = sum(tau_vals)/len(tau_vals) if tau_vals else float('nan') # duración media del viaje
print(tau_vals)