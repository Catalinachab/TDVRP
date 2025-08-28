#!/usr/bin/env python3
# τ(x) PWL para un arco i->j (corto y al pie)
import json, math, argparse, csv

def Z(I):
    return [(float(a), float(b)) for a, b in I["speed_zones"]]

def P(I):
    return (I["horizon"][1] - I["horizon"][0]) if "horizon" in I else Z(I)[-1][1]

def zid(t, Zs, per):
    t = (t % per + per) % per
    for i, (a, b) in enumerate(Zs):
        if a <= t < b: return i
    return len(Zs) - 1

def fwd(D, x, VZ, Zs, per):  # tiempo exacto recorriendo zonas
    if D <= 0: return 0.0
    t = (x % per + per) % per; rem = D; tot = 0.0
    for _ in range(len(Zs)*4 + 10):
        i = zid(t, Zs, per); a, b = Zs[i]; v = VZ[i]
        if v <= 0: return math.inf
        cap = v * (b - t)
        if rem <= cap + 1e-12: return tot + rem / v
        tot += (b - t); rem -= cap; t = b % per
    return math.inf

def back(T, D, VZ, Zs, per):  # x tal que distancia(x->T)=D
    t = (T % per + per) % per; rem = D
    for _ in range(len(Zs)*4 + 10):
        i = zid(t - 1e-12, Zs, per); a, b = Zs[i]; v = VZ[i]
        span = (t - a) if t >= a else (t + per) - a
        cap = v * span
        if rem <= cap + 1e-12: return (t - rem / v) % per
        rem -= cap; t = a if a > 0 else per
    return float('nan')

def tau_pts(D, VZ, Zs, per):
    B = {a % per for a, _ in Zs}          # inicios de zona
    for a, _ in Zs:                       # preimágenes de inicios
        x = back(a, D, VZ, Zs, per)
        if not math.isnan(x): B.add(round(x, 9))
    B.add(0.0); B = sorted({b % per for b in B})
    if abs(B[-1] - per) > 1e-9: B.append(per)
    return [(x, fwd(D, x, VZ, Zs, per)) for x in B]

import json, csv, os

def main():
    index_path = 'data/instancias-dabia_et_al_2013/index.json'
    with open(index_path) as f:
        instances = json.load(f)   # esto es una lista de diccionarios
        
    # ! Cómo iterar sobre los arcos??? Qué arcos hay que mirar para comparar?
    arc = "7_12"
    i, j = map(int, arc.split("_"))

    for inst in instances:
        instance_name = inst["file_name"]
        instance_path = "data/instancias-dabia_et_al_2013/" + instance_name

        out_path = f"data/outputs/{instance_name}_arc_{arc}.json"
        csv_path = f"data/outputs/{instance_name}_arc_{arc}.csv"

        # Cargar instancia
        I = json.load(open(instance_path))
        D = I["distances"][i][j]
        cid = I["clusters"][i][j]
        VZ = I["cluster_speeds"][cid]
        Zs = Z(I); per = P(I)

        # Calcular puntos
        pts = tau_pts(D, VZ, Zs, per)

        # Asegurar carpeta outputs
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Guardar resultados
        with open(out_path, "w") as f_json:
            json.dump({"period": per, "arc": f"{i}-{j}", "points": pts}, f_json, indent=2)

        with open(csv_path, "w", newline="") as f_csv:
            w = csv.writer(f_csv)
            w.writerow(["x_depart", "tau_duration"])
            w.writerows(pts)

if __name__ == "__main__":
    main()  
