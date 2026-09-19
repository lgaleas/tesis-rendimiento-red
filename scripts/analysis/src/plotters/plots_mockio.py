import sys, os, json, pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def generate_validation(raw_dir, proc_dir, graph_dir):
    summary_file = os.path.join(raw_dir, 'mock_validation_summary.json')
    res_file = os.path.join(raw_dir, 'mock_validation_resources.csv')

    if not os.path.exists(summary_file) or not os.path.exists(res_file):
        print("[WARN] Datos de Mock I/O no encontrados. Omitiendo validación.")
        return

    with open(summary_file) as f:
        k6_summary = json.load(f)
    metrics = k6_summary.get('metrics', {})
    latency_avg = metrics.get('http_req_duration', {}).get('avg', 0)
    latency_p95 = metrics.get('http_req_duration', {}).get('p(95)', 0)
    throughput = metrics.get('http_reqs', {}).get('rate', 0)
    error_rate = metrics.get('http_req_failed', {}).get('value', 0) * 100

    df_res = pd.read_csv(res_file)
    df_res['timestamp'] = pd.to_datetime(df_res['timestamp'], format='mixed', errors='coerce')
    start_time_res = df_res['timestamp'].iloc[0]
    df_res['Seconds_Elapsed'] = (df_res['timestamp'] - start_time_res).dt.total_seconds()
    
    cpu_max = df_res['cpu_percent'].max() if 'cpu_percent' in df_res.columns else 0
    cpu_avg = df_res['cpu_percent'].mean() if 'cpu_percent' in df_res.columns else 0
    mem_max = df_res['mem_usage'].max() if 'mem_usage' in df_res.columns else 0
    mem_avg = df_res['mem_usage'].mean() if 'mem_usage' in df_res.columns else 0
    tcp_max = df_res['tcp_conns'].max() if 'tcp_conns' in df_res.columns else 0

    # CORRECCIÓN 1: Tabla LaTeX actualizada a MiB
    tabla = f"""\\begin{{table}}[H]
\\centering
\\caption{{Comportamiento de \\texttt{{mock\\_io}} bajo carga de validación (500 RPS).}}
\\label{{tab:mock_capacity}}
\\begin{{tabular}}{{|l|c|}}
\\hline
\\textbf{{Métrica}} & \\textbf{{Valor}} \\\\ \\hline
Latencia Promedio & {latency_avg:.4f} ms \\\\ \\hline
Latencia P95      & {latency_p95:.4f} ms \\\\ \\hline
Throughput Medio  & {throughput:.1f} RPS \\\\ \\hline
Tasa de Errores   & {error_rate:.2f} \\% \\\\ \\hline
CPU (Máximo / Promedio) & {cpu_max:.2f} \\% / {cpu_avg:.2f} \\% \\\\ \\hline
RAM (Máximo / Promedio) & {mem_max:.2f} MiB / {mem_avg:.2f} MiB \\\\ \\hline
Conexiones TCP Máximas & {tcp_max} \\\\ \\hline
\\end{{tabular}}
\\end{{table}}
"""
    with open(os.path.join(proc_dir, 'mock_validation_table.tex'), 'w', encoding='utf-8') as f:
        f.write(tabla)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(r'Rendimiento Base de mock_io (Meta: 500 RPS)', fontsize=15, y=1.02, fontweight='bold')

    ax1.bar(['Throughput (RPS)'], [throughput], color='#2ecc71', width=0.4, edgecolor='white')
    ax1.axhline(y=500, color='gray', linestyle='--', alpha=0.7, label='Meta (500 RPS)')
    ax1.text(0, throughput * 0.5, f'{throughput:.1f}', ha='center', color='white', fontweight='bold', fontsize=12)
    ax1.set_ylim(0, max(600, throughput * 1.2))
    ax1.set_ylabel('Peticiones por Segundo')
    ax1.set_title('Tasa de Transferencia Exitosa', pad=10)
    ax1.legend(loc='upper right', frameon=False)

    lat_labels, lat_values = ['Promedio', 'P95'], [latency_avg, latency_p95]
    bars2 = ax2.bar(lat_labels, lat_values, color=['#3498db', '#2980b9'], width=0.5, edgecolor='white')
    for bar in bars2:
        val = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, val + (max(lat_values)*0.05), f'{val:.4f}', ha='center', va='bottom', fontweight='bold', color='#333')

    y_max_lat = max(lat_values) * 1.3 if max(lat_values) > 0 else 1
    ax2.set_ylim(0, y_max_lat)
    ax2.set_ylabel('Latencia (ms)')
    ax2.set_title('Tiempos de Respuesta', pad=10)
    
    plt.tight_layout()
    plt.savefig(os.path.join(graph_dir, 'mock_validate_k6_summary.png'), dpi=300, bbox_inches='tight')
    plt.close()

    if not df_res.empty:
        fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
        fig.suptitle('Consumo de Recursos de mock_io bajo 500 RPS', fontsize=15, fontweight='bold', y=1.02)

        if 'cpu_percent' in df_res.columns:
            ax = axes[0, 0]
            ax.plot(df_res['Seconds_Elapsed'], df_res['cpu_percent'], color='#e74c3c', lw=2)
            ax.fill_between(df_res['Seconds_Elapsed'], df_res['cpu_percent'], color='#e74c3c', alpha=0.1)
            ax.set_title('Uso de CPU (%)', pad=10)
            ax.set_ylabel('CPU %')
            ax.set_ylim(0, max(5, cpu_max * 1.5))
            ax.text(0.02, 0.95, f'Límite Docker: 100% (1 core)\nMáximo real: {cpu_max:.2f}%',
                    transform=ax.transAxes, va='top', fontsize=9)

        if 'mem_usage' in df_res.columns:
            ax = axes[0, 1]
            ax.plot(df_res['Seconds_Elapsed'], df_res['mem_usage'], color='#9b59b6', lw=2)
            ax.fill_between(df_res['Seconds_Elapsed'], df_res['mem_usage'], color='#9b59b6', alpha=0.1)
            
            # CORRECCIÓN 2: Título, eje Y, y textos interiores actualizados a MiB
            ax.set_title('Uso de Memoria RAM (MiB)', pad=10)
            ax.set_ylabel('MiB')
            ax.set_ylim(0, max(20, mem_max * 1.5))
            ax.text(0.02, 0.95, f'Límite Docker: 256 MiB\nMáximo real: {mem_max:.2f} MiB',
                    transform=ax.transAxes, va='top', fontsize=9)

        if 'cpu_temp_c' in df_res.columns:
            ax = axes[1, 0]
            ax.plot(df_res['Seconds_Elapsed'], df_res['cpu_temp_c'], color='#e67e22', lw=2)
            ax.fill_between(df_res['Seconds_Elapsed'], df_res['cpu_temp_c'], color='#e67e22', alpha=0.1)
            ax.set_title('Temperatura del CPU (°C)', pad=10)
            ax.set_ylabel('°C')
            ax.set_xlabel('Tiempo (Segundos)')
            
            temp_max = df_res['cpu_temp_c'].max()
            temp_min = df_res['cpu_temp_c'].min()
            ax.set_ylim(max(0, temp_min - 5), temp_max + 5)

        if 'tcp_conns' in df_res.columns:
            ax = axes[1, 1]
            ax.plot(df_res['Seconds_Elapsed'], df_res['tcp_conns'], color='#34495e', lw=2)
            ax.fill_between(df_res['Seconds_Elapsed'], df_res['tcp_conns'], color='#34495e', alpha=0.1)
            ax.set_title('Conexiones TCP Activas', pad=10)
            ax.set_ylabel('Conexiones')
            ax.set_xlabel('Tiempo (Segundos)')
            ax.set_ylim(0, max(5, tcp_max * 1.5))

        plt.tight_layout()
        plt.savefig(os.path.join(graph_dir, 'mock_validate_resources_dashboard.png'), dpi=300, bbox_inches='tight')
        plt.close()