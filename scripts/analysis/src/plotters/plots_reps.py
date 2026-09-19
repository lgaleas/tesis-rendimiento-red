import os, re, json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def compute_p99(filepath):
    durations = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try: 
                point = json.loads(line.strip())
                if point.get("metric") == "http_req_duration" and point.get("type") == "Point":
                    durations.append(point["data"]["value"])
            except: continue
    return float(np.percentile(durations, 99)) if durations else 0.0

def generate_stabilization_analysis(raw_dir, proc_dir, graph_dir, umbral_sd=0.10):
    raw_path = Path(raw_dir)
    
    def extract_fw(fw):
        files = list(raw_path.glob(f"{fw}_cpu_A_high_*_metrics.json"))
        rep_files = []
        for f in files:
            m = re.search(rf"{fw}_cpu_A_high_(\d+)_", f.name)
            if m: rep_files.append((int(m.group(1)), f))
        rep_files.sort(key=lambda x: x[0])
        return [compute_p99(f) for _, f in rep_files]

    fastapi_p99 = extract_fw("fastapi")
    express_p99 = extract_fw("express")
    if not fastapi_p99 or not express_p99: return

    def cum_sd(vals):
        arr = np.array(vals)
        return [np.std(arr[:i], ddof=1) for i in range(2, len(arr) + 1)]

    fastapi_sd, express_sd = cum_sd(fastapi_p99), cum_sd(express_p99)
    
    def detect_stable(sd_list):
        for i in range(1, len(sd_list)):
            if all(abs(sd_list[j] - sd_list[j-1]) < umbral_sd for j in range(i, len(sd_list))):
                return i + 2
        return None

    estab_fa, estab_ex = detect_stable(fastapi_sd), detect_stable(express_sd)
    min_req = max(estab_fa, estab_ex) if estab_fa and estab_ex else None

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(range(2, len(fastapi_p99) + 1), fastapi_sd, marker="s", color="#1f77b4", label="FastAPI", lw=2)
    ax.plot(range(2, len(express_p99) + 1), express_sd, marker="o", color="#ff7f0e", label="Express", lw=2)

    if estab_fa:
        ax.axvspan(estab_fa, len(fastapi_p99), color="#1f77b4", alpha=0.05, label=f"Estable FastAPI (N$\geq${estab_fa})")
        ax.axvline(x=estab_fa, color="#1f77b4", linestyle="--")
    if estab_ex:
        ax.axvspan(estab_ex, len(express_p99), color="#ff7f0e", alpha=0.05, label=f"Estable Express (N$\geq${estab_ex})")
        ax.axvline(x=estab_ex, color="#ff7f0e", linestyle="--")

    ax.set_xlabel("Número de repeticiones (N)")
    ax.set_ylabel("Desviación Estándar Acumulada del P99 (ms)")
    ax.set_title(f"Estabilización de Varianza – Endpoint /cpu (Umbral: < {umbral_sd} ms)", pad=15, fontweight='bold')

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
    
    plt.tight_layout()

    fig.subplots_adjust(bottom=0.25)
    plt.savefig(os.path.join(graph_dir, 'estabilizacion_reps_combinada.png'), dpi=300)
    plt.close()

    with open(os.path.join(proc_dir, "tabla_estabilizacion.tex"), "w", encoding="utf-8") as f:
        f.write(r"\begin{table}[h]" + "\n" + r"\centering" + "\n" + r"\caption{Estabilización de la Desviación Estándar (SD)}" + "\n" + r"\begin{tabular}{lcccc}" + "\n" + r"\hline" + "\n" + r"\textbf{Reps.} & \textbf{P99 FastAPI} & \textbf{SD FastAPI} & \textbf{P99 Express} & \textbf{SD Express} \\" + "\n" + r"\hline" + "\n")
        f.write(f"1 & {fastapi_p99[0]:.2f} & --- & {express_p99[0]:.2f} & --- \\\\\n")
        for i in range(1, min(len(fastapi_p99), len(express_p99))):
            f_sd = f"{fastapi_sd[i-1]:.4f}" if i-1 < len(fastapi_sd) else "---"
            e_sd = f"{express_sd[i-1]:.4f}" if i-1 < len(express_sd) else "---"
            f.write(f"{i+1} & {fastapi_p99[i]:.2f} & {f_sd} & {express_p99[i]:.2f} & {e_sd} \\\\\n")
        f.write(r"\hline" + "\n" + r"\end{tabular}" + "\n" + r"\end{table}")