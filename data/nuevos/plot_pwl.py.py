#!/usr/bin/env python3
import sys, pandas as pd, matplotlib.pyplot as plt
if len(sys.argv)<2:
    print("uso: python plot_pwl.py arc_3_5_pwl.csv"); sys.exit(1)
df = pd.read_csv(sys.argv[1])
plt.figure()
plt.plot(df["x_depart"], df["tau_duration"])
plt.xlabel("Hora de salida x (mismo tiempo que instancia)")
plt.ylabel("Duración τ(x)")
plt.title(sys.argv[1])
plt.tight_layout()
plt.show()
