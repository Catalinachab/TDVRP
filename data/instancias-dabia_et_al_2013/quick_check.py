import json, sys, math

if len(sys.argv) < 4:
    print("uso: python quick_check.py <instancia.json> <i> <j>")
    sys.exit(1)

inst = json.load(open(sys.argv[1]))
i, j = int(sys.argv[2]), int(sys.argv[3])

# Datos base
P = (inst["horizon"][1]-inst["horizon"][0]) if "horizon" in inst else inst["speed_zones"][-1][1]
zones = [(float(a), float(b)) for a,b in inst["speed_zones"]]
cid = inst["clusters"][i][j]
VZ  = [float(v) for v in inst["cluster_speeds"][cid]]
D   = float(inst["distances"][i][j])

print("period:", P)
print("zones:", zones)
print("len(zones) vs len(VZ):", len(zones), len(VZ))
print("VZ (vel por zona):", VZ)
print("D (distancia i->j):", D)

def zid(t):
    t = (t % P + P) % P
    for k,(a,b) in enumerate(zones):
        if a <= t < b: return k
    return len(zones)-1

def fwd(D,t0):
    if D <= 0: return 0.0
    t = (t0 % P + P) % P; rem = D; tot = 0.0
    for _ in range(len(zones)*4+10):
        k = zid(t); a,b = zones[k]; v = VZ[k]
        cap = v*(b - t)
        if rem <= cap + 1e-12: return tot + rem/v
        tot += (b - t); rem -= cap; t = b % P
    return math.inf

# Chequeo puntual cerca de un borde
x_test = zones[0][1] - 10.0  # 10 unidades antes del primer borde
print("tau(x_test) =", fwd(D, x_test))
