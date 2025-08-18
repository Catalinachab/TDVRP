
import math
import json
from typing import List, Tuple, Optional

def load_instance(path: str):
    with open(path, 'r') as f:
        inst = json.load(f)
    return inst

def build_time_dependent_functions(inst):
    """
    Returns:
      travel_time_arc(i,j,t): time to traverse arc (i->j) if departing at time t (seconds)
      travel_time_path(path, t0, service_times, end_depot): total duration of a full path if departing at t0
      horizon_span: length of the daily horizon in seconds (period)
    """
    dist = inst['distances']
    clusters = inst['clusters']
    cluster_speeds = inst['cluster_speeds']
    speed_zones = inst['speed_zones']
    horizon_span = inst['horizon'][1] - inst['horizon'][0]

    def zone_index(t: float) -> int:
        tt = t % horizon_span
        for k, (a,b) in enumerate(speed_zones):
            if a <= tt < b:
                return k
        # Edge case if exactly at the end
        return len(speed_zones)-1

    def speed_for_arc(i: int, j: int, t: float) -> float:
        cid = clusters[i][j]
        z = zone_index(t)
        return cluster_speeds[cid][z]

    def travel_time_arc(i: int, j: int, t: float) -> float:
        s = speed_for_arc(i, j, t)
        d = dist[i][j]
        if s <= 0:
            return math.inf
        return d / s

    def travel_time_path(path: List[int], t0: float, service_times: List[float], end_depot: int) -> float:
        T = 0.0
        cur = t0
        for u, v in zip(path[:-1], path[1:]):
            dt = travel_time_arc(u, v, cur)
            T += dt
            cur += dt
            if v != end_depot:
                sv = service_times[v]
                T += sv
                cur += sv
        return T

    return travel_time_arc, travel_time_path, horizon_span

def y_of_x_for_path(inst: dict, path: List[int], step: float = 60.0) -> Tuple[list, list]:
    """
    Builds the aggregated function y(x) for a full path across one daily horizon.
    x spans [0, horizon) sampled every 'step' seconds.
    y(x) = total duration if departing the path at time x.
    """
    t_arc, t_path, H = build_time_dependent_functions(inst)
    xs, ys = [], []
    t0 = 0.0
    while t0 < H - 1e-9:
        y = t_path(path, t0, inst['service_times'], inst['end_depot'])
        xs.append(t0)
        ys.append(y)
        t0 += step
    return xs, ys

def plot_y_of_x_for_path(inst: dict, path: List[int], step: float = 60.0,
                         show: bool = True, save_path: Optional[str] = None):
    """
    Plots y(x) for a given path over one day.
    - step: sampling step in seconds (e.g., 60 = 1 min)
    - show: whether to display the plot
    - save_path: if provided, saves the figure to this filepath
    """
    xs, ys = y_of_x_for_path(inst, path, step)
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        raise RuntimeError("matplotlib is required to plot y(x). Please install it.") from e

    # Single plot, no style or specific colors per guidelines
    fig = plt.figure()
    # Convert x to hours for readability
    xs_hours = [x / 3600.0 for x in xs]
    plt.plot(xs_hours, ys)
    plt.xlabel("Hora de salida (horas)")
    plt.ylabel("Duración total (segundos)")
    plt.title("y(x): duración del recorrido vs. hora de salida")
    if save_path is not None:
        fig.savefig(save_path, bbox_inches='tight')
    if show:
        plt.show()
    return fig, (xs, ys)
