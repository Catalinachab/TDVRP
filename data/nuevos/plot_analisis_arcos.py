import pandas as pd
import matplotlib.pyplot as plt
import os

# Cargar el archivo de resultados
data_path = "data/outputs/analisis_arcos.csv"
if not os.path.exists(data_path):
    raise FileNotFoundError(f"No se encontró {data_path}. Ejecuta primero el script de análisis.")

df = pd.read_csv(data_path)

# ? 1. Histograma de tau_min, tau_max, tau_mean
# esto es para ver la distribución de estas variables
# que patrones buscar?
    # - ¿Hay alguna relación entre tau_min, tau_max y tau_mean?
    # - ¿Cómo varían estas métricas con la distancia? intuitivamente debería haber una correlación positiva, o sea, a mayor distancia, mayor duración del viaje
    # - ¿Existen clusters de arcos preferibles? que tengan menores duraciones de viaje; o menores pendientes en el punto mínimo (slope_min), o sea que no varíen tanto según el instante de salida 
df[["tau_min", "tau_max", "tau_mean"]].hist(bins=30, figsize=(12, 4))
plt.suptitle("Distribución de tau_min, tau_max, tau_mean")
plt.show()

#? 2. Scatter: distancia vs tau_min
# que patrones buscar?
    # - ¿Hay outliers? arcos con mucha distancia pero bajo tau_min, o viceversa. a que se debe esto? ¿tal vez por la velocidad del cluster?
    # - ¿Cómo varía esto según el cluster? (si hay muchos clusters, tal vez conviene agruparlos. criterio? por ejemplo, agrupar clusters con velocidades similares con algun umbral, o por percentiles)
        # - ¿Hay clusters con velocidades similares que se comportan de manera diferente?
    # - ¿Hay arcos con pendiente muy alta en el punto mínimo (slope_min)? es decir, que varíen mucho según el instante de salida
df.plot.scatter(x="distancia", y="tau_min", alpha=0.5, title="Distancia vs tau_min")
plt.show()

#? 3. Scatter: distancia vs tau_mean
    # - similar a los de distancia vs tau_min pero con la media se suavizan los outliers
df.plot.scatter(x="distancia", y="tau_mean", alpha=0.5, title="Distancia vs tau_mean")
plt.show()

#? 4. Boxplot de tau_min por cluster
    # - ¿Hay clusters que consistentemente tienen menores tau_min? que características tienen esos clusters? puedo usar esto para elegir clusters preferibles y evitar otros
    # - ¿Cómo varía la dispersión dentro de cada cluster? (algunos clusters pueden tener mucha variabilidad en tau_min, otros pueden ser más consistentes). Si un cluster tiene mucha variabilidad, puede ser menos predecible y por lo tanto menos deseable
if "cluster" in df.columns:
    df.boxplot(column="tau_min", by="cluster", grid=False)
    plt.title("tau_min por cluster")
    plt.suptitle("")
    plt.xlabel("cluster")
    plt.ylabel("tau_min")
    plt.show()

#? 5. Scatter: tau_min vs tau_max
    # - ¿Hay alguna relación entre tau_min y tau_max? intuitivamente debería haber una correlación positiva, es decir, a mayor tau_min, mayor tau_max 
plt.scatter(df["tau_min"], df["tau_max"], alpha=0.5)
plt.xlabel("tau_min")
plt.ylabel("tau_max")
plt.title("tau_min vs tau_max")
plt.show()

print("Listo. Observa los gráficos para buscar patrones visuales.")
