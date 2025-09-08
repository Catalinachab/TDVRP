import pandas as pd
import matplotlib.pyplot as plt
import os

# Cargar el archivo de resultados
data_path = "data/outputs/analisis_arcos.csv"
if not os.path.exists(data_path):
    raise FileNotFoundError(f"No se encontró {data_path}. Ejecuta primero el script de análisis.")

df = pd.read_csv(data_path)

# Histograma de tau_min, tau_max, tau_mean
df[["tau_min", "tau_max", "tau_mean"]].hist(bins=30, figsize=(12, 4))
plt.suptitle("Distribución de tau_min, tau_max, tau_mean")
plt.show()

# Scatter: distancia vs tau_min
df.plot.scatter(x="distancia", y="tau_min", alpha=0.5, title="Distancia vs tau_min")
plt.show()

# Scatter: distancia vs tau_mean
df.plot.scatter(x="distancia", y="tau_mean", alpha=0.5, title="Distancia vs tau_mean")
plt.show()

# Boxplot de tau_min por cluster
if "cluster" in df.columns:
    df.boxplot(column="tau_min", by="cluster", grid=False)
    plt.title("tau_min por cluster")
    plt.suptitle("")
    plt.xlabel("cluster")
    plt.ylabel("tau_min")
    plt.show()

# Scatter: tau_min vs tau_max
plt.scatter(df["tau_min"], df["tau_max"], alpha=0.5)
plt.xlabel("tau_min")
plt.ylabel("tau_max")
plt.title("tau_min vs tau_max")
plt.show()

print("Listo. Observa los gráficos para buscar patrones visuales.")
