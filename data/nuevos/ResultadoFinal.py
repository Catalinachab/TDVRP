
import json, csv, sys
from td_functions import load_instance, build_time_dependent_functions

def main(inst_path, path_str, step=60.0, out_csv='y_of_x.csv'):
    inst = load_instance(inst_path)
    tt_arc, tt_path, H = build_time_dependent_functions(inst)
    path = [int(x) for x in path_str.split(',')]
    xs = []
    ys = []
    t0=0.0
    while t0 < H - 1e-9:
        y = tt_path(path, t0, inst['service_times'], inst['end_depot'])
        xs.append(t0)
        ys.append(y)
        t0 += step
    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['t_depart', 'duration'])
        for a,b in zip(xs, ys):
            w.writerow([a,b])
    print(f"Wrote {out_csv} with {len(xs)} rows.")

if __name__=='__main__':
    # Example: python make_y_of_x.py /mnt/data/RC208_50.json 0,10,11,12,14,17,47,16,15,9,13,51 60 out.csv
    inst_path = sys.argv[1]
    path = sys.argv[2]
    step = float(sys.argv[3]) if len(sys.argv)>3 else 60.0
    out_csv = sys.argv[4] if len(sys.argv)>4 else 'y_of_x.csv'
    main(inst_path, path, step, out_csv)
