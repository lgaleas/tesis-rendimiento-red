import os, glob, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.config import FRAMEWORK_ORDER

def generate_capacity_curves(raw_dir, proc_dir, graph_dir):
    metrics_files = glob.glob(os.path.join(raw_dir, '*_ramping_*_metrics.json'))
    if not metrics_files: return
    
    tabla_resumen = []
    EMA_SPAN = 5 

    for m_file in metrics_files:
        basename = os.path.basename(m_file)
        parts = basename.split('_')
        framework, endpoint = parts[0].capitalize(), parts[1].upper()
        fw_label = 'FastAPI' if framework.lower() == 'fastapi' else 'Express'

        data = []
        with open(m_file, 'r') as f:
            for line in f:
                if '"http_req_duration"' in line or '"http_req_failed"' in line:
                    try:
                        row = json.loads(line)
                        if row.get('type') == 'Point':
                            data.append({'time': pd.to_datetime(row['data']['time']), 'metric': row['metric'], 'value': row['data']['value']})
                    except: continue

        if not data: continue
        df = pd.DataFrame(data).set_index('time')
        duration_sec = (df.index.max() - df.index.min()).total_seconds()

        df_duration = df[df['metric'] == 'http_req_duration']['value'].resample('1s').mean().rename('Latency_Mean_ms')
        df_p99 = df[df['metric'] == 'http_req_duration']['value'].resample('1s').quantile(0.99).rename('Latency_P99_ms')
        df_rps = df[df['metric'] == 'http_req_duration']['value'].resample('1s').count().rename('Requests_Per_Second')
        df_err = df[df['metric'] == 'http_req_failed']['value'].resample('1s').sum().rename('Errors_Count')

        merged = pd.concat([df_rps, df_duration, df_p99, df_err], axis=1).fillna(0)
        merged = merged[merged['Requests_Per_Second'] > 0].reset_index(drop=True)
        merged.to_csv(os.path.join(proc_dir, basename.replace('_metrics.json', '_capacity.csv')), index=False)

        sustainable = merged[(merged['Errors_Count'] == 0) & (merged['Latency_P99_ms'] < 500)]
        max_sust_rps = sustainable['Requests_Per_Second'].max() if not sustainable.empty else 0
        p99_at_max_sust = sustainable.loc[sustainable['Requests_Per_Second'].idxmax(), 'Latency_P99_ms'] if not sustainable.empty else None

        saturated = merged[(merged['Errors_Count'] > 0) | (merged['Latency_P99_ms'] >= 500)]
        if not saturated.empty:
            sat_rps = saturated['Requests_Per_Second'].iloc[0]
            p99_at_sat = saturated['Latency_P99_ms'].iloc[0]
            errores_at_sat = saturated['Errors_Count'].iloc[0]
        else:
            sat_rps = p99_at_sat = errores_at_sat = None

        tabla_resumen.append({'framework': fw_label, 'endpoint': endpoint, 'max_sust_rps': max_sust_rps, 'p99_at_max_sust': p99_at_max_sust, 'sat_rps': sat_rps, 'p99_at_sat': p99_at_sat, 'errores_at_sat': errores_at_sat, 'max_rps': merged['Requests_Per_Second'].max(), 'duration_sec': duration_sec})

        merged_smooth = merged.copy()
        merged_smooth['Latency_P99_ms'] = merged_smooth['Latency_P99_ms'].ewm(span=EMA_SPAN, adjust=False).mean()

        fig, ax1 = plt.subplots(figsize=(10, 6))
        color_lat = '#1f77b4' if fw_label == 'FastAPI' else '#ff7f0e'
        
        ax1.set_xlabel('Tasa de Peticiones Inyectadas (RPS)', fontsize=12)
        ax1.set_ylabel('Latencia P99 (ms)', color=color_lat, fontsize=12)
        line1 = ax1.plot(merged_smooth['Requests_Per_Second'], merged_smooth['Latency_P99_ms'], color=color_lat, marker='.', linestyle='-', linewidth=2, label='Latencia P99 (EMA)')
        ax1.tick_params(axis='y', labelcolor=color_lat)

        max_lat_smooth = merged_smooth['Latency_P99_ms'].max()
        max_err_count = merged['Errors_Count'].max()
        is_saturated = max_lat_smooth >= 500 or max_err_count > 0

        lines, labels = line1, [l.get_label() for l in line1]
        if is_saturated:
            line2 = ax1.axhline(y=500, color='gray', linestyle='--', label='Límite SLO (500ms)')
            lines.append(line2); labels.append(line2.get_label())
            if max_err_count > 0:
                ax2 = ax1.twinx()
                ax2.set_ylabel('Cantidad de Errores', color='#d62728', fontsize=12)
                ax2.bar(merged_smooth['Requests_Per_Second'], merged_smooth['Errors_Count'], width=1.5, color='#d62728', alpha=0.3, label='Errores')
                ax2.grid(False)
                h, l = ax2.get_legend_handles_labels()
                lines += h; labels += l
        else:
            ax1.set_ylim(0, max(max_lat_smooth * 1.5, 25))
            ax1.text(0.02, 0.92, '[OK] Prueba Estable: No superó el límite SLO (500ms)', transform=ax1.transAxes, color='green', fontweight='bold', bbox=dict(facecolor='white', alpha=0.9, edgecolor='green', boxstyle='round,pad=0.5'))

        ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=len(labels), frameon=False)
        plt.title(f'Capacidad Máxima (Ramping Load) - {fw_label} /{endpoint}', pad=15, fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        fig.subplots_adjust(bottom=0.20)
        plt.savefig(os.path.join(graph_dir, f'capacity_curve_{fw_label.lower()}_{endpoint.lower()}.png'), dpi=300)
        plt.close()

    if tabla_resumen:
        latex_path = os.path.join(proc_dir, 'tabla_capacidad.tex')
        with open(latex_path, 'w', encoding='utf-8') as f:
            f.write(r"\begin{table}[h]" + "\n" + r"\centering" + "\n" + r"\caption{Capacidad máxima y punto de saturación}" + "\n" + r"\label{tab:capacidad}" + "\n" + r"\begin{tabular}{lccccccc}" + "\n" + r"\hline" + "\n" + r"Framework & Endpoint & RPS máx & P99 Sost (ms) & RPS sat. & P99 Sat (ms) & Errores & RPS Pico \\" + "\n" + r"\hline" + "\n")
            for r in tabla_resumen:
                f.write(f"{r['framework']} & {r['endpoint']} & {r['max_sust_rps']:.1f} & {r['p99_at_max_sust'] or 0:.1f} & {r['sat_rps'] or 0:.1f} & {r['p99_at_sat'] or 0:.1f} & {r['errores_at_sat'] or 0} & {r['max_rps']:.1f} \\\\\n")
            f.write(r"\hline" + "\n" + r"\end{tabular}" + "\n" + r"\end{table}" + "\n")