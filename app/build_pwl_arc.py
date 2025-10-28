#!/usr/bin/env python3
# τ(x) PWL para un arco i->j (corto y al pie)
import json, math, argparse, csv

def Z(I):
    # zonas de velocidad como tuplas de floats
    return [(float(a), float(b)) for a, b in I["speed_zones"]]

def P(I):
    # periodo del horizonte o el final de la última zona si no hay horizonte
        # per es longitud total del ciclo de tiempo considerado (por ejemplo, un día, una hora, etc.). 
        # o sea, rango de tiempo sobre el que se repiten las zonas de velocidad. si no hay horizonte, 
        # es el final de la última zona
    return (I["horizon"][1] - I["horizon"][0]) if "horizon" in I else Z(I)[-1][1]

def zid(t, Zs, per):
    # índice de la zona en que cae t
    # t = (t % per + per) % per # para asegurar que t está en [0, per)
    for i, (a, b) in enumerate(Zs):
        if a <= t < b: return i
    # si t == per, cae en la última zona
    return len(Zs) - 1

def fwd(D, x, VZ, Zs, per):  # tiempo exacto recorriendo zonas
    # tiempo total para recorrer distancia D, saliendo en x
    if D <= 0: return 0.0
    #t = (x % per + per) % per; 
    t = x
    rem = D; tot = 0.0
    for _ in range(len(Zs)*4 + 10): # para evitar bucles infinitos
        # i es la zona de velocidad en la que cae t; a,b los extremos de la zona; v la velocidad de la zona
        i = zid(t, Zs, per); a, b = Zs[i]; v = VZ[i]

        if v <= 0: return math.inf # caso zona de velocidad 0 o negativa 

        cap = v * (b - t) # distancia max que se puede recorrer en esta zona
        # si se puede recorrer lo que queda en esta zona, se termina
        if rem <= cap + 1e-12: return tot + rem / v
        # si no, se recorre lo máximo posible en esta zona y se sigue
        tot += (b - t); rem -= cap; t = b % per
    # si se sale del for, es que no se ha podido recorrer la distancia D
    return math.inf

def back(T, D, VZ, Zs, per):  # x tal que distancia(x->T)=D}
    '''
    instante x tal que yendo desde x se llega a T recorriendo distancia D. si no existe, devuelve NaN'''
    #t = (T % per + per) % per
    t = T
    rem = D
    for _ in range(len(Zs)*4 + 10):
        i = zid(t - 1e-12, Zs, per); a, b = Zs[i]; v = VZ[i]
        # span es el tiempo que se puede estar en esta zona antes de llegar a t; si t (instante) es mayor o igual al inicio de la zona, se puede estar todo el tiempo de la zona, si no, se puede estar el tiempo desde el inicio de la zona hasta el final del periodo y luego desde 0 hasta t
        span = (t - a) if t >= a else (t + per) - a
        cap = v * span # dist max que se puede recorrer en esta zona hacia atrás. multiplicar por v porque se recorre a velocidad v
        if rem <= cap + 1e-12: return (t - rem / v) % per
        rem -= cap; t = a if a > 0 else per
    return float('nan')

def tau_pts(D, VZ, Zs, per):
    '''
    puntos de τ(x) para x en [0, per]. Devuelve lista de tuplas (x, τ(x)). es decir, (instante de salida, duración del viaje)
    '''
    B = {a % per for a, _ in Zs}          # inicios de zona
    for a, _ in Zs:                       # preimágenes de inicios (o sea, x tales que τ(x) es un inicio de zona)
        x = back(a, D, VZ, Zs, per)
        if not math.isnan(x): B.add(round(x, 9)) 
    B.add(0.0); B = sorted({b % per for b in B}) # asegurar que 0 está y ordenar
    if abs(B[-1] - per) > 1e-9: B.append(per) # asegurar que per está, porque es el final del intervalo
    return [(x, fwd(D, x, VZ, Zs, per)) for x in B] # calcular τ(x) para cada x en B
