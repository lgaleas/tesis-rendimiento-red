import os
import pandas as pd
from scipy import stats
from src.config import SLO_MS

def export_latex(df, filepath, caption, label):
    try:
        tex_str = df.style.format(precision=2).to_latex(caption=caption, label=label)
    except AttributeError:
        tex_str = df.to_latex(index=False, float_format="%.2f", caption=caption, label=label)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(tex_str)

def generate_statistical_tables(df_summary, df_latencies, df_resources, df_gc, proc_dir):
    stats_results = []
    df_high = df_summary[df_summary['Profile'] == 'high']

    metrics_to_test = {
        'Latency_P99': 'Latencia P99 (ms)',
        'Throughput': 'Throughput (RPS)',
        'CPU_Mean': 'Uso CPU (%)',
        'RAM_Mean': 'Uso RAM (MB)'
    }

    for sc in df_high['Scenario'].unique():
        for ep in ['CPU', 'IO']:
            for metric_col, metric_label in metrics_to_test.items():
                if metric_col not in df_high.columns: continue

                fa_data = df_high[(df_high['Endpoint'] == ep) & (df_high['Scenario'] == sc) & (df_high['Framework'] == 'FastAPI')][metric_col].dropna()
                ex_data = df_high[(df_high['Endpoint'] == ep) & (df_high['Scenario'] == sc) & (df_high['Framework'] == 'Express')][metric_col].dropna()

                if len(fa_data) >= 3 and len(ex_data) >= 3:
                    _, p_shap_f = stats.shapiro(fa_data)
                    _, p_shap_e = stats.shapiro(ex_data)
                    normal_dist = (p_shap_f >= 0.05) and (p_shap_e >= 0.05)

                    if normal_dist:
                        _, p_val = stats.ttest_ind(fa_data, ex_data, equal_var=False)
                        test_name = "T-Student (Welch)"
                    else:
                        _, p_val = stats.mannwhitneyu(fa_data, ex_data, alternative='two-sided')
                        test_name = "Mann-Whitney U"

                    # Nombres de columnas ajustados para que coincidan con el formato exacto de tu tabla LaTeX
                    stats_results.append({
                        'Escenario': sc, 
                        'Endpoint': ep, 
                        'Métrica': metric_label,
                        'Shapiro FastAPI': '<0.001' if p_shap_f < 0.001 else f"{p_shap_f:.4f}",
                        'Shapiro Express': '<0.001' if p_shap_e < 0.001 else f"{p_shap_e:.4f}",
                        'Normalidad': "Sí" if normal_dist else "No",
                        'Prueba': test_name, 
                        'P-Valor': '<0.001' if p_val < 0.001 else f"{p_val:.4f}",
                        'Significativo': "Sí" if p_val < 0.05 else "No"
                    })

    if stats_results:
        df_stats = pd.DataFrame(stats_results)
        df_stats.to_csv(os.path.join(proc_dir, 'tabla_significancia.csv'), index=False)
        export_latex(df_stats, os.path.join(proc_dir, 'tabla_significancia.tex'), "Análisis de significancia estadística (Perfil High)", "tab:significancia")

    scenarios_map = {'A': 'A (Ideal)', 'B': 'B (Inestable)', 'C': 'C (Caos)'}

    for sc_id, sc_name in scenarios_map.items():
        df_sc = df_summary[df_summary['Scenario'] == sc_name]
        if not df_sc.empty:
            agg_dict = {
                'Latency_P99': ['mean', 'std'],
                'Throughput': ['mean'],
                'Error_Rate': ['mean'],
                'CPU_Mean': ['mean', 'std'],
                'RAM_Mean': ['mean', 'std']
            }
            if 'TCP_Max' in df_sc.columns: agg_dict['TCP_Max'] = ['mean']
            if 'CPU_Temp_Max_C' in df_sc.columns: agg_dict['CPU_Temp_Max_C'] = ['max']

            df_grouped = df_sc.groupby(['Endpoint', 'Framework', 'Profile'], observed=False).agg(agg_dict).reset_index()
            df_grouped.columns = ['_'.join(col).strip('_') for col in df_grouped.columns.values]
            df_grouped = df_grouped.round(2)

            df_grouped.to_csv(os.path.join(proc_dir, f'scenario_{sc_id}_summary_table.csv'), index=False)
            export_latex(df_grouped, os.path.join(proc_dir, f'scenario_{sc_id}_summary_table.tex'), f"Resumen de métricas - Escenario {sc_id}", f"tab:scenario_{sc_id}_summary")

        df_lat_sc = df_latencies[df_latencies['Scenario'] == sc_name]
        if not df_lat_sc.empty:
            percentiles = df_lat_sc.groupby(['Endpoint', 'Framework', 'Profile'], observed=False)['Latency'].quantile([0.5, 0.9, 0.95, 0.99]).unstack().reset_index()
            percentiles.columns = ['Endpoint', 'Framework', 'Profile', 'P50_ms', 'P90_ms', 'P95_ms', 'P99_ms']
            export_latex(percentiles.round(2), os.path.join(proc_dir, f'scenario_{sc_id}_latency_percentiles.tex'), f"Percentiles latencia - Escenario {sc_id}", f"tab:scenario_{sc_id}_percentiles")

        if not df_gc.empty:
            df_gc_sc = df_gc[(df_gc['Scenario'] == sc_name) & (df_gc['Profile'] == 'high')]
            if not df_gc_sc.empty:
                gc_stats = df_gc_sc.groupby(['Endpoint', 'Framework'], observed=False).agg(
                    Total_Ciclos=('Duration', 'count'),
                    Tiempo_Total_ms=('Duration', 'sum'),
                    Duracion_Promedio_ms=('Duration', 'mean'),
                    Duracion_Maxima_ms=('Duration', 'max')
                ).reset_index()

                # Formateo honesto: si hay actividad real (>0) pero es menor a 0.01ms, mostrar <0.01
                for col in ['Tiempo_Total_ms', 'Duracion_Promedio_ms', 'Duracion_Maxima_ms']:
                    gc_stats[col] = gc_stats[col].apply(lambda x: '<0.01' if 0 < x < 0.01 else round(x, 2))

                export_latex(gc_stats, os.path.join(proc_dir, f'scenario_{sc_id}_gc_stats.tex'), f"GC (100 RPS) - Escenario {sc_id}", f"tab:scenario_{sc_id}_gc")

    if not df_high.empty:
        agg_cross = {
            'Throughput': 'mean',
            'Latency_P99': 'mean',
            'Error_Rate': 'mean',
            'CPU_Mean': 'mean',
            'RAM_Mean': 'mean'
        }
        if 'TCP_Max' in df_high.columns: agg_cross['TCP_Max'] = 'mean'
        if 'CPU_Temp_Max_C' in df_high.columns: agg_cross['CPU_Temp_Max_C'] = 'max'

        df_cross = df_high.groupby(['Endpoint', 'Scenario', 'Framework'], observed=False).agg(agg_cross).reset_index().round(2)
        
        df_cross.to_csv(os.path.join(proc_dir, 'cross_scenario_high_summary.csv'), index=False)
        export_latex(df_cross, os.path.join(proc_dir, 'cross_scenario_high_summary.tex'), 
                     "Resumen Consolidado a través de Escenarios (Carga High 100 RPS)", "tab:cross_scenario_high")

        df_radar_input = df_cross[['Endpoint', 'Scenario', 'Framework', 'Throughput', 'Latency_P99', 'Error_Rate', 'CPU_Mean', 'RAM_Mean']].copy()
        df_radar_input.rename(columns={'Throughput': 'Throughput (RPS)', 'Latency_P99': 'P99 (ms)', 'Error_Rate': 'Errores (%)', 'CPU_Mean': 'CPU (%)', 'RAM_Mean': 'RAM (MB)'}, inplace=True)
        
        df_radar_input.to_csv(os.path.join(proc_dir, 'radar_input_data.csv'), index=False)
        export_latex(df_radar_input, os.path.join(proc_dir, 'radar_input_data.tex'), 
                     "Métricas Base Alimentando el Gráfico Radial de Eficiencia (Carga High)", "tab:radar_input")

    if not df_resources.empty and 'cpu_temp_c' in df_resources.columns:
        temp_grouped = df_resources.groupby(['Scenario', 'Endpoint', 'Framework'], observed=False)['cpu_temp_c'].agg(
            Temp_Media='mean',
            Temp_Max='max'
        ).reset_index().round(2)
        
        temp_grouped.rename(columns={'Scenario': 'Escenario', 'Temp_Media': 'Temp. Media (°C)', 'Temp_Max': 'Temp. Máx (°C)'}, inplace=True)
        temp_grouped.to_csv(os.path.join(proc_dir, 'tabla_temperaturas.csv'), index=False)
        export_latex(temp_grouped, os.path.join(proc_dir, 'tabla_temperaturas.tex'), "Temperaturas de CPU (°C) por escenario, endpoint y framework.", "tab:temp_scenarios")

    if not df_latencies.empty:
        df_lat_high = df_latencies[df_latencies['Profile'] == 'high'].copy()
        
        if not df_lat_high.empty:
            df_lat_high['Violacion_SLO'] = df_lat_high['Latency'] > SLO_MS

            slo_grouped = df_lat_high.groupby(['Scenario', 'Endpoint', 'Framework'], observed=False).agg(
                Total_Peticiones=('Latency', 'count'),
                Violaciones_SLO=('Violacion_SLO', 'sum')
            ).reset_index()

            slo_grouped['Exceso_SLO_%'] = (slo_grouped['Violaciones_SLO'] / slo_grouped['Total_Peticiones'] * 100).round(2)

            slo_grouped.rename(columns={'Scenario': 'Escenario'}, inplace=True)

            slo_grouped.to_csv(os.path.join(proc_dir, 'tabla_slo_exceedance.csv'), index=False)
            export_latex(slo_grouped, os.path.join(proc_dir, 'tabla_slo_exceedance.tex'), 
                         f"Porcentaje de peticiones que exceden el SLO en carga alta ({SLO_MS} ms)", "tab:slo_exceedance")

    print("[INFO] Todas las tablas .tex y .csv generadas correctamente en 'processed/'.")