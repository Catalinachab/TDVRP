#!/usr/bin/env python3
# ======================================================================================
#  Script: build_pwl_arc.py
#  Objetivo: Construir τ(x) para UN arco i->j.
#            τ(x) = "tiempo total de viaje si arranco a la hora x".
#
#  ¿Por qué τ(x) no es constante?
#   - Porque la VELOCIDAD cambia según la franja horaria (speed_zones).
#   - Si arrancás cerca de un cambio de franja, parte del viaje va con una velocidad,
#     y el resto con otra ⇒ el tiempo total depende de x.
#
#  ¿Qué hace el script, en una línea?
#   - Lee la instancia, toma la distancia del arco y su perfil de velocidades por franja,
#     calcula los puntos "clave" (breakpoints) de τ(x) y devuelve los pares (x, τ(x))
#     que definen una función PWL (piecewise linear).
#
#  Estructura del JSON de la instancia (lo que usamos):
#    - "speed_zones": [[a0,b0], [a1,b1], ...]  -> zonas horarias donde la velocidad es constante
#    - "clusters":     matriz NxN de ids       -> para cada arco (i,j) dice qué cluster usar
#    - "cluster_speeds":[ [v0,v1,...], ... ]  -> por cluster: velocidad en cada zona (mismo largo que speed_zones)
#    - "distances":     matriz NxN             -> distancia fija de cada arco (i,j)
#    - "horizon": [0,P] (opcional)            -> longitud del ciclo (si no está, usamos fin de la última zona)
#
#  Breakpoints de τ(x) (dónde puede cambiar la pendiente):
#    (1) Inicios de zona (a_k): cambiar x de un lado u otro del inicio cambia la velocidad inicial.
#    (2) "Preimágenes" de inicios (x tales que llegás EXACTO a un inicio): si al variar x, la llegada
#        cruza justo un borde, cambia el patrón de tramos usados y cambia la pendiente local de τ(x).
#
#  Cómo calculamos τ(x):
#    - forward: simulamos avanzar desde x, gastando distancia dentro de cada zona hasta completar D.
#    - backward: para cada inicio de zona T=a_k, "caminamos hacia atrás" distancia D para encontrar el x
#      que haría que la llegada caiga justo en T (ese x es breakpoint).
#
#  NOTA DE UNIDADES:
#    El script NO convierte unidades. Asume consistencia:
#     - speed_zones y horizon están en la misma unidad de tiempo (minutos, segundos, etc.).
#     - cluster_speeds está en "distancia por unidad de tiempo" en esas mismas unidades (por ejemplo,
#       si speed_zones está en minutos y la distancia está en "unidades de distancia", entonces
#       las velocidades deben ser "unidades de distancia por minuto").
#     - τ(x) sale en la UNIDAD DE TIEMPO de la instancia.
# ======================================================================================

import json, math, argparse, csv


# ------------------------------- Helpers de lectura -----------------------------------

def Z(I):
    """
    Extrae las zonas como lista de tuplas (a,b).
    Cada zona [a,b) marca un tramo del día con velocidad constante.
    """
    return [(float(a), float(b)) for a, b in I["speed_zones"]]


def P(I):
    """
    Devuelve el período total P (longitud del “día”).
    - Si el JSON trae "horizon": [0, P], usamos ese P.
    - Si no, usamos el fin de la última zona (b_último).
    """
    return (I["horizon"][1] - I["horizon"][0]) if "horizon" in I else Z(I)[-1][1]


# ------------------------------ Localización de zonas ---------------------------------

def zid(t, Zs, per):
    """
    Zs: es la lista de zonas de velocidades, el priemro arranca en 0 hasta 100, el segundo... etc
    per es el ultimo t
    Dada una hora t (puede ser negativa o mayor a P), devuelve el índice de la zona de velocidades
    tal que a <= t_mod < b, donde t_mod = t mod P.
    """
    t = (t % per + per) % per  # normalizamos t dentro de [0, P), basicamente si un dia tiene 24hs y entra un 25h lo convertimos en hora 1
    for i, (a, b) in enumerate(Zs):
        if a <= t < b:
            return i
    # Si t == P exacto (muy justo), caemos en la última por seguridad.
    return len(Zs) - 1


# --------------------------- Núcleo: caminar hacia ADELANTE ----------------------------

def fwd(D, x, VZ, Zs, per):
    """
    Calcula τ(x) EXACTO "caminando hacia adelante".
    Idea: arrancamos en hora t=x. Queda por recorrer "rem = D".
    En la zona actual (a,b), con velocidad v, podemos avanzar hasta el borde b:
       - distancia máxima dentro de la zona: cap = v * (b - t).
    Si rem <= cap => terminamos dentro de esta zona en tiempo rem/v.
    Si rem  > cap => usamos todo (b - t), descontamos cap de rem y saltamos a la próxima zona.
    Repetimos hasta agotar la distancia D. La suma de tiempos es τ(x).

    D: distancia del arco
    x: hora de salida
    VZ: lista de velocidades por zona para el cluster del arco (mismo largo que Zs)
    Zs: lista de zonas [(a,b), ...]
    per: periodo P (longitud del “día”)
    """
    if D <= 0:
        return 0.0

    t = (x % per + per) % per  # normalizamos x
    rem = D                    # distancia restante
    tot = 0.0                  # tiempo acumulado

    # Acotamos las iteraciones para no ciclar si hubiera datos raros.
    for _ in range(len(Zs) * 4 + 10):   # un numero cualquiera para evitar un while infinito
        i = zid(t, Zs, per)    # zona actual según t
        a, b = Zs[i]
        v = VZ[i]              # velocidad en esta zona
        if v <= 0:
            # velocidad 0 => no se puede avanzar. Marcamos infinito.
            return math.inf

        # Cuánta distancia puedo cubrir antes de chocar con el límite de zona:
        cap = v * (b - t)

        if rem <= cap + 1e-12: # sumamos ese numero por los errores de float y eso
            # Se termina dentro de esta zona: tiempo = distancia / velocidad
            return tot + rem / v

        # No alcanza dentro de esta zona: consumo todo (b - t) y paso a la siguiente
        tot += (b - t)   # tiempo usado dentro de la zona actual
        rem -= cap       # distancia que ya recorrí en esta zona
        t = b % per      # salto al inicio de la próxima zona (considerando wrap del día), se normaliza por si estas en la ultima hora del dia para que arranque en 0 devuelta

    # Si llegamos acá, algo está inconsistente (por ejemplo, D enorme y sumatoria de
    # “distancia por día” insuficiente). Devolvemos infinito como señal.
    return math.inf


# --------------------------- Núcleo: caminar hacia ATRÁS -------------------------------

def back(T, D, VZ, Zs, per):
    """
    Calcula el x tal que, saliendo a x, la llegada es EXACTO en T, tras recorrer D.

    ¿Por qué sirve? Porque "llegar en un inicio de zona" T = a_k define un breakpoint.
    Para cada inicio T, buscamos el x que “cae” justo ahí (si existe) recorriendo
    D distancia hacia atrás (como si “rebobináramos” el viaje).

    Algoritmo:
    - Partimos desde t = T.
    - En la zona inmediatamente anterior a t, podemos “recuperar hacia atrás” una distancia
      de cap = v * span, donde span es la longitud de tiempo disponible hacia atrás hasta
      el inicio de esa zona.
    - Si D <= cap, arrancó dentro de esta misma zona: x = t - (D / v).
    - Si D  > cap, saltamos al inicio de la zona (t = a) y seguimos “restando” en la zona anterior.

    Retorna:
      - x (mod P) si existe.
      - NaN si no se pudo cubrir D en un “día extendido” (no debería pasar si los datos son razonables).
    """
    t = (T % per + per) % per  # normalizamos T
    rem = D

    for _ in range(len(Zs) * 4 + 10):
        # Si estoy EXACTO en un borde, miro un poquito antes (t-ε) para caer en la zona anterior.
        i = zid(t - 1e-12, Zs, per)
        a, b = Zs[i]
        v = VZ[i]

        # span = cuánto tiempo hay yendo hacia atrás dentro de esta zona:
        #   si t está entre a y b, span = t - a
        #   si t está “cerca” de 0 y a es grande, span = (t + P) - a (considerando wrap)
        span = (t - a) if t >= a else (t + per) - a
        cap = v * span  # distancia que puedo “recuperar” hacia atrás en esta zona

        if rem <= cap + 1e-12:
            # El viaje empezó dentro de esta misma zona. Desplazo hacia atrás rem/v.
            return (t - rem / v) % per

        # Si no alcanza, salto al inicio de la zona previa y sigo “rebobinando”.
        rem -= cap
        t = a if a > 0 else per

    return float('nan')


# ------------------------ Construcción de breakpoints y PWL ----------------------------

def tau_pts(D, VZ, Zs, per):
    """
    Junta todos los breakpoints y evalúa τ(x) en ellos.
    Breakpoints = { inicios de zona } ∪ { preimágenes (x) de cada inicio T } ∪ {0}.

    Luego ordena en [0,P), y asegura que incluimos P al final para cerrar el período.
    Devuelve la lista de puntos [(x0, τ(x0)), (x1, τ(x1)), ...] en orden creciente de x.
    """
    # (1) Inicios de zona:
    B = {a % per for a, _ in Zs}

    # (2) Preimágenes de inicios: para cada inicio T=a, calculamos x = back(T, D, ...)
    for a, _ in Zs:
        x = back(a, D, VZ, Zs, per)
        if not math.isnan(x):
            # redondeo leve para evitar duplicados casi iguales por flotantes
            B.add(round(x, 9))

    # Siempre metemos 0 (no hace daño, y suele ser útil)
    B.add(0.0)

    # Normalizamos al período y ordenamos
    B = sorted({b % per for b in B})

    # Aseguramos el cierre en P (si el último no es exactamente P)
    if abs(B[-1] - per) > 1e-9:
        B.append(per)

    # Evaluamos τ(x) en cada breakpoint. Entre puntos consecutivos, τ es lineal.
    return [(x, fwd(D, x, VZ, Zs, per)) for x in B]


# ------------------------------------ Programa CLI ------------------------------------

def main():
    """
    Uso:
      python build_pwl_arc.py <instancia.json> i-j --out arc_pwl.json --csv arc_pwl.csv

    - Lee la instancia.
    - Toma D = distances[i][j] y el cluster del arco para obtener VZ (velocidades por zona).
    - Construye los puntos de la PWL τ(x) en [0, P].
    - Exporta:
        * JSON: {"period": P, "arc": "i-j", "points": [[x0,tau0],...]}
        * CSV (opcional): encabezado "x_depart,tau_duration" y filas con los puntos.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")          # ruta al archivo de instancia .json
    ap.add_argument("arc")               # arco en formato "i-j"
    ap.add_argument("--out", default="arc_pwl.json")
    ap.add_argument("--csv")
    args = ap.parse_args()

    # Cargamos instancia y extraemos lo necesario
    I   = json.load(open(args.instance))
    i, j = map(int, args.arc.split("-"))
    D   = I["distances"][i][j]           # distancia del arco i->j
    cid = I["clusters"][i][j]            # id de cluster del arco i->j
    VZ  = I["cluster_speeds"][cid]       # velocidades por zona de ese cluster
    Zs  = Z(I)                           # lista de zonas [(a,b), ...]
    per = P(I)                           # período total P

    # Calculamos los puntos (x, τ(x))
    pts = tau_pts(D, VZ, Zs, per)

    # Guardamos JSON (para C++ o inspección)
    json.dump({"period": per, "arc": f"{i}-{j}", "points": pts}, open(args.out, "w"), indent=2)

    # (Opcional) Guardamos CSV (para graficar rápido)
    if args.csv:
        w = csv.writer(open(args.csv, "w", newline=""))
        w.writerow(["x_depart", "tau_duration"])
        w.writerows(pts)


if __name__ == "__main__":
    main()
