# TDVRP

## Arquitectura
- `app/`
  - `app.py`                       : Tool de análisis como WebApp de Streamlit
  - `tdvrp_analyzer.py`            : Análisis y evaluación de soluciones TDVRP.
  - `build_pwl_arc.py`             : Herramientas para construir funciones PWL para arcos (de acá usamos la función fwd para la simulación).
  - `simulacion.py`                : Módulos para simular rutas y tiempos dependientes.
  - `metricas_arcos.py`            : Cálculo de métricas.
  - `input_prueba`                 : Ejemplos de input para la tool


- `/data`
  - `/instancias-dabia_et_al_2013` : instancias y soluciones que usamos para las pruebas
  - `/nuevos`                      : código original sobre el que trabajamos
  - `/outputs`                     : resultados de métricas de las pruebas
  - `/repo_gonzalo`                : código que tomamos como inspiración.
      - `/code`:
        * Hay una clase vrp_instance.h, para usar algunas ideas.
        * El pre-cálculo de las funciones de tiempo de viaje para las instancias es un preprocesamiento, se calcula en preprocess_travel_times.cpp
        * El manejo de funciones pwl y otras clases básicas están en math.
        * Un par de clases simples para el manejo de soluciones están en vrp.   