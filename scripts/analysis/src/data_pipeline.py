import os, glob
import pandas as pd
import numpy as np
from src.parsers import parse_k6_summary, parse_k6_metrics_and_errors, parse_resources, parse_gc_events
from src.config import FRAMEWORK_ORDER, PROFILE_ORDER, SCENARIO_ORDER

def extract_scenario(base_dir, scenario_label):
    raw_dir = os.path.join(base_dir, 'raw')
    logs_dir = os.path.join(base_dir, 'logs')
    if not os.path.exists(raw_dir): return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    sum_data, lats, errs, res, gcs = [], [], [], [], []
    for sum_file in glob.glob(os.path.join(raw_dir, '*_summary.json')):
        basename = os.path.basename(sum_file)
        parts = basename.split('_')
        if len(parts) < 4: continue

        fw = 'FastAPI' if parts[0].lower() == 'fastapi' else 'Express'
        ep, profile = parts[1].upper(), parts[3]

        tp, err_rate = parse_k6_summary(sum_file)
        df_lat, df_err = parse_k6_metrics_and_errors(sum_file.replace('_summary.json', '_metrics.json'))
        p99 = float(np.percentile(df_lat['Latency'], 99)) if not df_lat.empty else 0.0

        df_res = parse_resources(sum_file.replace('_summary.json', '_resources.csv'))
        cpu = df_res['cpu_percent'].mean() if not df_res.empty and 'cpu_percent' in df_res.columns else 0.0
        ram = df_res['mem_usage'].mean() if not df_res.empty and 'mem_usage' in df_res.columns else 0.0
        tcp = df_res['tcp_conns'].max() if not df_res.empty and 'tcp_conns' in df_res.columns else 0.0
        temp = df_res['cpu_temp_c'].max() if not df_res.empty and 'cpu_temp_c' in df_res.columns else 0.0

        df_gc = parse_gc_events(os.path.join(logs_dir, basename.replace('_summary.json', '_container.log')), fw)

        sum_data.append({
            'Scenario': scenario_label, 'Framework': fw, 'Endpoint': ep, 'Profile': profile,
            'Throughput': tp, 'Error_Rate': err_rate, 'Latency_P99': p99,
            'CPU_Mean': cpu, 'RAM_Mean': ram, 'TCP_Max': tcp, 'CPU_Temp_Max_C': temp
        })

        for df, lst in zip([df_lat, df_err, df_res, df_gc], [lats, errs, res, gcs]):
            if not df.empty:
                df['Scenario'] = scenario_label
                df['Framework'] = fw
                df['Endpoint'] = ep
                df['Profile'] = profile
                lst.append(df)

    return (pd.DataFrame(sum_data),
            pd.concat(lats, ignore_index=True) if lats else pd.DataFrame(),
            pd.concat(errs, ignore_index=True) if errs else pd.DataFrame(),
            pd.concat(res, ignore_index=True) if res else pd.DataFrame(),
            pd.concat(gcs, ignore_index=True) if gcs else pd.DataFrame())

def run_etl(raw_base_dir, proc_dir):
    scenarios_map = {'A': 'A (Ideal)', 'B': 'B (Inestable)', 'C': 'C (Caos)'}
    all_sum, all_lat, all_err, all_res, all_gc = [], [], [], [], []

    for sc_folder, sc_label in scenarios_map.items():
        # BÚSQUEDA DINÁMICA DE LA CARPETA (Ignora el timestamp)
        matches = glob.glob(os.path.join(raw_base_dir, f'scenario_{sc_folder}_*'))
        if matches:
            sc_path = matches[0]
            print(f"  -> Extrayendo {sc_label} desde: {os.path.basename(sc_path)}")
            s, l, e, r, g = extract_scenario(sc_path, sc_label)
            all_sum.append(s); all_lat.append(l); all_err.append(e); all_res.append(r); all_gc.append(g)
        else:
            print(f"[WARN] No se encontró carpeta para el escenario {sc_label}")

    filenames = ['master_summary.csv', 'master_latencies.csv', 'master_errors.csv', 'master_resources.csv', 'master_gc.csv']
    for df_list, filename in zip([all_sum, all_lat, all_err, all_res, all_gc], filenames):
        if df_list:
            df = pd.concat([d for d in df_list if not d.empty], ignore_index=True)
            if not df.empty:
                if 'Framework' in df.columns: df['Framework'] = pd.Categorical(df['Framework'], categories=FRAMEWORK_ORDER, ordered=True)
                if 'Profile' in df.columns: df['Profile'] = pd.Categorical(df['Profile'], categories=PROFILE_ORDER, ordered=True)
                if 'Scenario' in df.columns: df['Scenario'] = pd.Categorical(df['Scenario'], categories=SCENARIO_ORDER, ordered=True)
                df.to_csv(os.path.join(proc_dir, filename), index=False)