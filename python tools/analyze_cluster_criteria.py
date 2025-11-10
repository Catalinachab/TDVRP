
import json, os, math
from collections import Counter, defaultdict

DATA_DIR = "data/instancias-dabia_et_al_2013"
OUT_PATH = "data/cluster_analysis_report.json"

def load_instances(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_len_matrix(mat):
    try:
        return len(mat)
    except Exception:
        return 0

def analyze_instance(filepath):
    with open(filepath, "r", encoding="utf-8") as fh:
        I = json.load(fh)

    name = I.get("instance_name", os.path.basename(filepath))
    coords = I.get("coordinates") or []
    clusters = I.get("clusters") or []
    distances = I.get("distances") or []
    # Determine vertex_count using a robust priority:
    # 1) clusters matrix length (most reliable for arc-level labels)
    # 2) explicit vertex_count field
    # 3) coordinates length
    # 4) distances length (square matrix expected)
    # 5) digraph.vertex_count
    vertex_count = 0
    if isinstance(clusters, list) and len(clusters):
        vertex_count = len(clusters)
    else:
        vertex_count = I.get("vertex_count") or 0
        if not vertex_count and coords:
            vertex_count = len(coords)
        if not vertex_count and isinstance(distances, list) and len(distances):
            vertex_count = len(distances)
        if not vertex_count and isinstance(I.get("digraph"), dict):
            vertex_count = I["digraph"].get("vertex_count", vertex_count) or vertex_count

    # Prepare counters and containers
    arc_counts = Counter()
    arc_lengths_by_cluster = defaultdict(list)
    per_node_clusters = [Counter() for _ in range(vertex_count)]

    # Iterate arcs defensively: if clusters matrix shorter, use its available rows/cols
    for i in range(vertex_count):
        for j in range(vertex_count):
            if i == j:
                continue
            cid = None
            # try reading clusters[i][j] if present
            try:
                cid = clusters[i][j]
            except Exception:
                # fall back: maybe clusters is transposed/rect, or missing -> skip
                cid = None

            if cid is None:
                # if clusters missing but there is a cluster id encoded elsewhere, skip
                continue

            arc_counts[cid] += 1

            # record distance if available and valid
            try:
                d = distances[i][j]
                if isinstance(d, (int, float)):
                    arc_lengths_by_cluster[cid].append(d)
            except Exception:
                pass

            # per-node dominant cluster (use source node i)
            if i < len(per_node_clusters):
                per_node_clusters[i][cid] += 1

    # per-node dominant cluster and node centroids per cluster
    node_dominant = {}
    cluster_nodes = defaultdict(list)
    for node_idx, ctr in enumerate(per_node_clusters):
        if not ctr:
            continue
        cid, _ = ctr.most_common(1)[0]
        node_dominant[node_idx] = cid
        if coords and node_idx < len(coords):
            cluster_nodes[cid].append(coords[node_idx])

    cluster_spatial_summary = {}
    for cid, pts in cluster_nodes.items():
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cluster_spatial_summary[cid] = {
            "num_nodes": len(pts),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
            "centroid": [sum(xs)/len(xs), sum(ys)/len(pts)]
        }

    avg_len = {cid: (sum(lst)/len(lst) if lst else None) for cid, lst in arc_lengths_by_cluster.items()}

    # Debug hint if no arcs were found (helps detect why report had empty arc_counts)
    debug = None
    if not arc_counts:
        debug = {
            "note": "no arcs counted: clusters matrix may be missing or empty; check 'clusters' shape in the instance file",
            "clusters_present": bool(clusters),
            "clusters_len": safe_len_matrix(clusters),
            "coords_len": len(coords),
            "distances_len": len(distances),
            "reported_vertex_count_field": I.get("vertex_count", None)
        }

    return {
        "instance": name,
        "vertex_count": vertex_count,
        "cluster_count": I.get("cluster_count", None),
        "arc_counts": dict(arc_counts),
        "avg_arc_length_by_cluster": avg_len,
        "cluster_spatial_summary": cluster_spatial_summary,
        "time_horizon": I.get("horizon"),
        "service_times_sample": I.get("service_times", [])[:5],
        "debug": debug
    }

def main():
    index_path = os.path.join(DATA_DIR, "index.json")
    index = load_instances(index_path)
    results = []
    for entry in index:
        fname = entry.get("file_name")
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"⚠️ missing file: {path}")
            continue
        results.append(analyze_instance(path))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print short summary
    for r in results:
        arcs = r.get('arc_counts') or {}
        print(f"{r['instance']}: clusters={r['cluster_count']}, arcs_per_cluster={arcs if arcs else '{}'}, horizon={r['time_horizon']}")
        if r.get("debug"):
            print("  DEBUG:", r["debug"])
    print(f"\nReport saved to: {OUT_PATH}")

if __name__ == '__main__':
    main()