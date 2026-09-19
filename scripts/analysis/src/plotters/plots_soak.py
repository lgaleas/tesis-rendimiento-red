import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import glob
import pandas as pd
from matplotlib.patheffects import withStroke
from src.config import COLORS, FRAMEWORK_ORDER
from src.stats import export_latex 
from src.parsers import parse_k6_metrics_and_errors, parse_gc_events

def generate_all(df_soak_res, graph_dir, proc_dir, soak_raw_dir):
    if df_soak_res.empty:
        return

    if 'mem_usage' in df_soak_res.columns:
        fig, ax = plt.subplots(figsize=(14, 6))
        fig.suptitle('Consumo de RAM durante el soak test', fontsize=16, fontweight='bold')
        
        for fw in FRAMEWORK_ORDER:
            df_fw = df_soak_res[df_soak_res['Framework'] == fw].copy()
            if not df_fw.empty:
                time_mins = df_fw['Relative_Time'] / 60.0
                df_fw['mem_smooth'] = df_fw['mem_usage'].rolling(window=15, min_periods=1).mean()
                ax.plot(time_mins, df_fw['mem_smooth'], label=f'RAM {fw}', color=COLORS[fw], lw=2)
                
                try:
                    mem_start = df_fw[time_mins >= 5]['mem_smooth'].iloc[0]
                    mem_end = df_fw[time_mins <= 59]['mem_smooth'].iloc[-1]
                    drift = mem_end - mem_start
                    drift_sign = "+" if drift > 0 else ""
                    ax.annotate(f'{fw} Drift: {drift_sign}{drift:.1f} MiB', 
                                xy=(59, mem_end), xytext=(-50, 15 if drift > 0 else -15),
                                textcoords='offset points', color=COLORS[fw], fontweight='bold',
                                bbox=dict(facecolor='white', alpha=0.8, edgecolor=COLORS[fw], boxstyle='round,pad=0.3'))
                except: pass

        ax.axhline(256, color='#8e44ad', linestyle='--', linewidth=2, label='Límite del contenedor (256 MiB)')
        ax.set_xlabel('Tiempo de ejecución (Minutos)')
        ax.set_ylabel('Memoria RAM Asignada (MiB)')
        ax.set_ylim(bottom=0)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, 'soak_01_ram_stability.png'), dpi=300, bbox_inches='tight')
        plt.close()

    k6_files = glob.glob(os.path.join(soak_raw_dir, '*_soak_io_B_metrics.json'))
    if not k6_files: return

    lat_data, err_data = {}, {}
    for fw in FRAMEWORK_ORDER:
        fw_file = [f for f in k6_files if fw.lower() in f.lower()]
        if fw_file:
            df_lat, df_err = parse_k6_metrics_and_errors(fw_file[0], apply_cold_start=True)
            if not df_lat.empty: lat_data[fw] = df_lat
            if not df_err.empty: err_data[fw] = df_err

    if not lat_data: return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    fig.suptitle('Estabilidad de la latencia durante el soak test', fontsize=16, fontweight='bold')
    
    for i, fw in enumerate(FRAMEWORK_ORDER):
        if fw in lat_data:
            ax = axes[i]
            df = lat_data[fw].copy()
            df['Minute'] = df['Relative_Time'] // 60
            grouped = df.groupby('Minute')['Latency']
            
            med_idx, med_vals = grouped.median().index, grouped.median().values
            p99_idx, p99_vals = grouped.quantile(0.99).index, grouped.quantile(0.99).values
            
            ax.plot(med_idx, med_vals, label='Mediana (P50)', color='#2ecc71', lw=2)
            ax.plot(p99_idx, p99_vals, label='Extremo (P99)', color=COLORS[fw], lw=2)
            
            if len(med_idx) > 0:
                ax.annotate(f'{med_vals[-1]:.0f} ms', xy=(med_idx[-1], med_vals[-1]), xytext=(5, 0), textcoords='offset points', color='#27ae60', fontweight='bold', va='center')
                ax.annotate(f'{p99_vals[-1]:.0f} ms', xy=(p99_idx[-1], p99_vals[-1]), xytext=(5, 0), textcoords='offset points', color=COLORS[fw], fontweight='bold', va='center')
            
            global_p50 = df['Latency'].median()
            global_p99 = df['Latency'].quantile(0.99)
            ax.text(0.05, 0.95, f'Global P50: {global_p50:.1f} ms\nGlobal P99: {global_p99:.1f} ms', 
                    transform=ax.transAxes, va='top', ha='left', fontsize=11, fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor=COLORS[fw], boxstyle='round,pad=0.5'))

            ax.axhline(500, color='#e74c3c', linestyle=':', linewidth=2, label='SLO (>500ms)')
            ax.set_title(f'Comportamiento {fw}', pad=10)
            ax.set_xlabel('Tiempo de ejecución (Minutos)')
            if i == 0: ax.set_ylabel('Latencia (ms)')
            ax.set_ylim(bottom=0)
            ax.set_xlim(right=66) 
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    plt.tight_layout()
    plt.savefig(os.path.join(graph_dir, 'soak_02_latency_degradation.png'), dpi=300, bbox_inches='tight')
    plt.close()

    if err_data:
        fig, ax = plt.subplots(figsize=(14, 6))
        fig.suptitle('Tasa de errores por minuto en el soak test', fontsize=16, fontweight='bold')
        
        for fw in FRAMEWORK_ORDER:
            if fw in err_data:
                df = err_data[fw].copy()
                df['Minute'] = df['Relative_Time'] // 60
                
                error_rate_per_min = df.groupby('Minute')['Failed'].mean() * 100
                global_mean_rate = df['Failed'].mean() * 100
                
                ax.plot(error_rate_per_min.index, error_rate_per_min.values, 
                        label=f'{fw} (Evolución)', color=COLORS[fw], lw=2)
                ax.axhline(global_mean_rate, color=COLORS[fw], linestyle='--', lw=2, alpha=0.8,
                           label=f'{fw} Media ({global_mean_rate:.2f}%)')
            
        ax.set_xlabel('Tiempo de ejecución (Minutos)')
        ax.set_ylabel('Tasa de Error (%)')
        ax.set_ylim(bottom=0)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, 'soak_03_cumulative_errors.png'), dpi=300, bbox_inches='tight')
        plt.close()

    all_lat = []
    for fw in FRAMEWORK_ORDER:
        if fw in lat_data:
            df = lat_data[fw].copy()
            df['Framework'] = fw
            all_lat.append(df)
            
    if all_lat:
        df_all = pd.concat(all_lat)
        fig, ax = plt.subplots(figsize=(10, 6))
        df_all['Latency'] = np.clip(df_all['Latency'], 0.1, 1400)
        
        sns.violinplot(data=df_all, x='Framework', y='Latency', hue='Framework', palette=COLORS, inner="quart", cut=0, linewidth=1.2, ax=ax, order=FRAMEWORK_ORDER, legend=False)
        ax.axhline(500, color='#e74c3c', linestyle=':', linewidth=1.5, label='Falla Transaccional (>500ms)')
        
        for idx, fw in enumerate(FRAMEWORK_ORDER):
            fw_data = df_all[df_all['Framework'] == fw]
            if not fw_data.empty:
                median_val = fw_data['Latency'].median()
                txt = ax.text(idx, median_val, f'{median_val:.0f}ms', ha='center', va='center', color='white', fontweight='bold', fontsize=11)
                txt.set_path_effects([withStroke(linewidth=3, foreground=COLORS[fw])])

        ax.set_title('Distribución de latencias', fontsize=15, fontweight='bold', pad=15)
        ax.set_ylabel('Latencia (ms) [Escala Lineal]')
        ax.set_xlabel('')
        ax.set_ylim(bottom=0, top=1500)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False)
        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, 'soak_04_latency_violin.png'), dpi=300, bbox_inches='tight')
        plt.close()

    summary = []
    for fw in FRAMEWORK_ORDER:
        if fw in lat_data:
            p99 = lat_data[fw]['Latency'].quantile(0.99)
            err_rate = 0
            if fw in err_data:
                total_errs = (err_data[fw]['Failed'] == 1).sum()
                total_reqs = len(err_data[fw])
                err_rate = (total_errs / total_reqs) * 100 if total_reqs > 0 else 0
            
            max_sec = lat_data[fw]['Relative_Time'].max()
            rps = len(lat_data[fw]) / max_sec if max_sec > 0 else 0
            
            df_fw_res = df_soak_res[df_soak_res['Framework'] == fw]
            max_ram, drift, tcp_max, temp_mean = 0, 0, 0, 0
            if not df_fw_res.empty:
                if 'mem_usage' in df_fw_res.columns:
                    max_ram = df_fw_res['mem_usage'].max()
                    try:
                        time_mins = df_fw_res['Relative_Time'] / 60.0
                        mem_smooth = df_fw_res['mem_usage'].rolling(window=15, min_periods=1).mean()
                        drift = mem_smooth[time_mins <= 59].iloc[-1] - mem_smooth[time_mins >= 5].iloc[0]
                    except: pass
                if 'tcp_conns' in df_fw_res.columns: tcp_max = df_fw_res['tcp_conns'].max()
                if 'cpu_temp_c' in df_fw_res.columns: temp_mean = df_fw_res['cpu_temp_c'].mean()
            
            summary.append({
                'Framework': fw, 'P99 (ms)': p99, 'Error Rate (%)': err_rate, 'Throughput (RPS)': rps,
                'RAM Max (MiB)': max_ram, 'RAM Drift (MiB)': drift, 'TCP Max': tcp_max, 'Temp Media (°C)': temp_mean
            })
            
    if summary:
        df_sum = pd.DataFrame(summary).round(2)
        export_latex(df_sum, os.path.join(proc_dir, 'soak_summary_table.tex'), 
                     "Resultados consolidados de estabilidad a largo plazo (soak test de 60 min a 50 RPS)", "tab:soak_summary")
        df_sum.to_csv(os.path.join(proc_dir, 'soak_summary_table.csv'), index=False)

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('Resumen global del soak test', fontsize=16, fontweight='bold', y=1.05)

        sns.barplot(data=df_sum, x='Framework', y='P99 (ms)', hue='Framework', palette=COLORS, ax=axes[0], edgecolor='white', order=FRAMEWORK_ORDER, legend=False)
        axes[0].set_title('Latencia P99 Global', pad=10)
        axes[0].set_ylabel('Latencia (ms)')
        axes[0].set_xlabel('')
        
        sns.barplot(data=df_sum, x='Framework', y='Error Rate (%)', hue='Framework', palette=COLORS, ax=axes[1], edgecolor='white', order=FRAMEWORK_ORDER, legend=False)
        axes[1].set_title('Tasa de Error Total', pad=10)
        axes[1].set_ylabel('Porcentaje de Falla (%)')
        axes[1].set_xlabel('')

        for ax_i, metric in zip(axes, ['P99 (ms)', 'Error Rate (%)']):
            for hue_idx, container in enumerate(ax_i.containers):
                if hue_idx >= len(FRAMEWORK_ORDER): continue 
                fw_name = FRAMEWORK_ORDER[hue_idx] 
                for bar in container:
                    row = df_sum[df_sum['Framework'] == fw_name]
                    if not row.empty:
                        val = row[metric].values[0]
                        unit = 'ms' if metric == 'P99 (ms)' else '%'
                        color = '#c0392b' if metric == 'Error Rate (%)' and val > 0.5 else '#333333'
                        ax_i.annotate(f'{val:.1f}{unit}', xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()), xytext=(0, 5), textcoords="offset points", ha='center', va='bottom', color=color, fontweight='bold')

        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, 'soak_05_summary_bars.png'), dpi=300, bbox_inches='tight')
        plt.close()

    if 'tcp_conns' in df_soak_res.columns:
        fig, ax = plt.subplots(figsize=(14, 6))
        fig.suptitle('Conexiones TCP durante el soak test', fontsize=16, fontweight='bold')
        
        for fw in FRAMEWORK_ORDER:
            df_fw = df_soak_res[df_soak_res['Framework'] == fw].copy()
            if not df_fw.empty:
                time_mins = df_fw['Relative_Time'] / 60.0
                df_fw['tcp_smooth'] = df_fw['tcp_conns'].rolling(window=15, min_periods=1).mean()
                ax.plot(time_mins, df_fw['tcp_smooth'], label=f'TCP {fw}', color=COLORS[fw], lw=2)
                
        ax.set_xlabel('Tiempo de ejecución (Minutos)')
        ax.set_ylabel('Conexiones en estado ESTABLISHED')
        ax.set_ylim(bottom=0)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, 'soak_06_tcp_timeseries.png'), dpi=300, bbox_inches='tight')
        plt.close()

    if 'cpu_temp_c' in df_soak_res.columns:
        for fw in FRAMEWORK_ORDER:
            subset = df_soak_res[df_soak_res['Framework'] == fw].copy()
            if subset.empty: continue

            subset['Relative_Min'] = subset['Relative_Time'] / 60.0
            fig, ax = plt.subplots(figsize=(14, 5))
            subset_sorted = subset.sort_values('Relative_Min')

            ax.scatter(subset_sorted['Relative_Min'], subset_sorted['cpu_temp_c'], color=COLORS[fw], alpha=0.35, s=6, edgecolors='none', label='Medición puntual')
            grouped = subset_sorted.groupby(np.floor(subset_sorted['Relative_Min']), observed=False)['cpu_temp_c'].mean()
            ax.plot(grouped.index, grouped.values, color=COLORS[fw], lw=2, label='Tendencia (Media)')

            ax.axhline(80, color='#e74c3c', linestyle='--', linewidth=2, label='Umbral de seguridad (80 °C)')
            ax.set_title(f'Estabilidad térmica de {fw} durante el soak test', fontsize=15, fontweight='bold', pad=15)
            ax.set_xlabel('Tiempo de ejecución (Minutos)')
            ax.set_ylabel('Temperatura (°C)')
            ax.set_xlim(0, 60)
            ax.set_ylim(30, max(45, subset_sorted['cpu_temp_c'].max() + 5)) 
            
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
            plt.tight_layout()
            plt.savefig(os.path.join(graph_dir, f'soak_07_temperature_{fw.lower()}.png'), dpi=300, bbox_inches='tight')
            plt.close()

    perc_list = []
    for fw in FRAMEWORK_ORDER:
        if fw in lat_data and not lat_data[fw].empty:
            lat_s = lat_data[fw]['Latency']
            perc_list.append({
                'Framework': fw,
                'P50': lat_s.median(),
                'P90': lat_s.quantile(0.90),
                'P95': lat_s.quantile(0.95),
                'P99': lat_s.quantile(0.99)
            })
            
    if perc_list:
        df_perc = pd.DataFrame(perc_list).round(2)
        export_latex(df_perc, os.path.join(proc_dir, 'soak_latency_percentiles.tex'),
                     "Percentiles de latencia en el soak test (peticiones exitosas)", "tab:soak_percentiles")
        df_perc.to_csv(os.path.join(proc_dir, 'soak_latency_percentiles.csv'), index=False)

    soak_logs_dir = os.path.join(os.path.dirname(soak_raw_dir), 'logs')
    gc_list = []
    
    for fw in FRAMEWORK_ORDER:
        log_files = glob.glob(os.path.join(soak_logs_dir, f'*{fw.lower()}*_container.log'))
        if log_files:
            df_gc = parse_gc_events(log_files[0], fw)
            if not df_gc.empty:
                gc_list.append({
                    'Framework': fw,
                    'Total Ciclos': len(df_gc),
                    'Tiempo Total (ms)': df_gc['Duration'].sum(),
                    'Dur. Promedio (ms)': df_gc['Duration'].mean(),
                    'Dur. Máxima (ms)': df_gc['Duration'].max()
                })
                
    if gc_list:
        df_gc_stats = pd.DataFrame(gc_list)
        
        for col in ['Tiempo Total (ms)', 'Dur. Promedio (ms)', 'Dur. Máxima (ms)']:
            df_gc_stats[col] = df_gc_stats[col].apply(lambda x: '<0.01' if 0 < x < 0.01 else round(x, 2))

        export_latex(df_gc_stats, os.path.join(proc_dir, 'soak_gc_stats.tex'),
                     "Actividad del GC durante el soak test (60 min)", "tab:soak_gc")
        df_gc_stats.to_csv(os.path.join(proc_dir, 'soak_gc_stats.csv'), index=False)

    if 'cpu_temp_c' in df_soak_res.columns:
        temp_soak_list = []
        for fw in FRAMEWORK_ORDER:
            df_fw_res = df_soak_res[df_soak_res['Framework'] == fw]
            if not df_fw_res.empty:
                temp_soak_list.append({
                    'Framework': fw,
                    'Temp. Media': df_fw_res['cpu_temp_c'].mean(),
                    'Temp. Máxima': df_fw_res['cpu_temp_c'].max()
                })
        
        if temp_soak_list:
            df_temp_soak = pd.DataFrame(temp_soak_list).round(2)
            export_latex(df_temp_soak, os.path.join(proc_dir, 'soak_temperature_stats.tex'),
                         "Estadísticas de temperatura durante el soak test", "tab:temp_soak")
            df_temp_soak.to_csv(os.path.join(proc_dir, 'soak_temperature_stats.csv'), index=False)