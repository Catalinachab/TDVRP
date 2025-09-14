from build_pwl_arc import *
import json, math, argparse, csv
index_path = 'data/instancias-dabia_et_al_2013/index.json'
#!/usr/bin/env python3

def pwl_f(t:float, i:int, j:int, instance_name:str) -> tuple:
   '''
   devuelve (t, y) donde y es el tiempo de viaje en el arco (i,j) si se sale en t
   '''
   # ver entre que 2 bkpts esta t
   # calcular la pendiente = (y2-y1)/(x2-x1)
   # para ver que y corresponde a t en (t, y) de la pwl de time ...?
   instance_path = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
   I = json.load(open(instance_path))
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


with open(index_path) as f:
    instances = json.load(f)
instance_path = "data/instancias-dabia_et_al_2013/C101_25.json"

I = json.load(open(instance_path))
Zs = Z(I)
per = P(I)
n = len(I["distances"]) 

D = I["distances"][0][23] #me dice la distancia desde 0 a 23
cid = I["clusters"][0][23] #me dice a que cluster de velocidad pertenece el arco de 0 a 23
VZ = I["cluster_speeds"][cid] #velocidades de ese cluster. Cual eligo?
speed_zones = I["speed_zones"]
speed_zones = [(float(a), float(b)) for a, b in I["speed_zones"]]
t0 = 7222.49975624939 #valor que dice en la solucion(ni idea de donde saca este t0)

ciclo_tiempo_tot = I["horizon"][1] -  I["horizon"][0]
# Encontrar el índice de la speed zone en la que está t0
speed_zone_idx=0
for i, (start, end) in enumerate(speed_zones): 
    if start <= t0 < end:
        speed_zone_idx = i
print(speed_zone_idx)
#las speed zones dividen el horizonte en intervalos de tiempo => tengo que ver en que speed zone estoy y dsp tomar del cluster de vel la velocidad correspondietne a esa speed zone

velocidad = VZ[speed_zone_idx]
print(velocidad)
print(D)
tiempo_arc_posta = D / velocidad 


tiempo_arc_pwl =pwl_f(t0, 0,23,"C101_25")

print("tiempo que tardo de 0 --> 23 segun PWL:",tiempo_arc_pwl," tiempo real",tiempo_arc_posta )


print("-"*100)

#me lo hizo copilot chequear
def test_simple():
    # Datos de tu instancia
    D = 130.0
    VZ = [1.16667, 0.666667, 1.33333, 0.833333, 1]
    Zs = [(0.0, 2472.0), (2472.0, 3708.0), (3708.0, 8652.0), (8652.0, 9888.0), (9888.0, 12360.0)]
    per = 12360.0
    
    # Test directo de fwd()
    resultado = fwd(D, 0, VZ, Zs, per)
    print(f"fwd(130, 0, ...) = {resultado}")
    print(f"Debería ser ≈ 111.43")
    
    # Test de tu función tau_pts
    puntos = tau_pts(D, VZ, Zs, per)
    punto_cero = next((tau for x, tau in puntos if abs(x) < 1e-6), None)
    print(f"τ(0) desde tau_pts = {punto_cero}")

test_simple()
print("=== TEST FUNCIÓN fwd() ===")
# Debería dar ≈111.43
resultado_fwd = fwd(D, 0, VZ, Zs, per)
print(f"fwd(130, 0, ...) = {resultado_fwd}")
print(f"Esperado ≈ 111.43")
print(f"Diferencia: {abs(resultado_fwd - 111.43)}")

print("\n=== TEST PUNTOS PWL ===")
pts = tau_pts(D, VZ, Zs, per)
print(f"Número de puntos generados: {len(pts)}")
print("Primeros 5 puntos:")
for i, (x, y) in enumerate(pts[:5]):
    print(f"  {i}: t={x:.3f} → τ={y:.6f}")

# Buscar el punto en t=0
punto_cero = None
for x, y in pts:
    if abs(x) < 1e-6:
        punto_cero = y
        break

print(f"\nτ(0) desde puntos PWL: {punto_cero}")
print(f"fwd(0) directo: {resultado_fwd}")
print(f"¿Son iguales? {abs(punto_cero - resultado_fwd) < 1e-6 if punto_cero else False}")
#dudas:
# - es todo en segundos? las speeds es por segundo o es km por hora o km por segundo