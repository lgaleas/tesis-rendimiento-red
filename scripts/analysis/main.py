#!/usr/bin/env python3
import os
import glob
import argparse
import pandas as pd
from src.data_pipeline import run_etl
from src.stats import generate_statistical_tables
from src.plotters.base_theme import setup_premium_theme
from src.plotters import plots_baseline, plots_resilience, plots_chaos, plots_global, plots_soak, plots_mockio, plots_ramping, plots_reps, plots_architecture, plots_netem_flow

def get_dynamic_dir(base_path, prefix):
    """Encuentra la carpeta real basada en el prefijo, ignorando el timestamp."""
    matches = glob.glob(os.path.join(base_path, f"{prefix}*"))
    return matches[0] if matches else None

def main():
    parser = argparse.ArgumentParser(description="Pipeline de Análisis - FastAPI vs Express")
    parser.add_argument("--raw-dir", required=True, help="Directorio raíz del experimento (ej: /experimentos/2)")
    parser.add_argument("--out-dir", required=True, help="Directorio de salida para gráficas y tablas")
    parser.add_argument("--skip-etl", action="store_true", help="Salta la extracción principal si los CSV ya existen")
    args = parser.parse_args()

    proc_dir = os.path.join(args.out_dir, "processed")
    graph_dir = os.path.join(args.out_dir, "graphs")
    os.makedirs(proc_dir, exist_ok=True)
    os.makedirs(graph_dir, exist_ok=True)

    setup_premium_theme()

    print("[INFO] Generando Diagramas de Arquitectura...")
    plots_architecture.generate_diagrams(graph_dir)
    plots_netem_flow.generate_netem_flow_diagram(graph_dir)

    print("[INFO] Generando Validación de Mock I/O...")
    mock_dir = get_dynamic_dir(args.raw_dir, 'mock_validation')
    if mock_dir:
        plots_mockio.generate_validation(os.path.join(mock_dir, 'raw'), proc_dir, graph_dir)
    else:
        print("[WARN] No se encontró la carpeta mock_validation")

    print("[INFO] Generando Curvas de Saturación (Ramping)...")
    ramping_dir = get_dynamic_dir(args.raw_dir, 'ramping')
    if ramping_dir:
        plots_ramping.generate_capacity_curves(os.path.join(ramping_dir, 'raw'), proc_dir, graph_dir)
    else:
        print("[WARN] No se encontró la carpeta ramping")

    print("[INFO] Verificando Estabilización de Varianza (Repeticiones)...")
    scen_a_dir = get_dynamic_dir(args.raw_dir, 'scenario_A')
    if scen_a_dir:
        plots_reps.generate_stabilization_analysis(os.path.join(scen_a_dir, 'raw'), proc_dir, graph_dir)
    else:
        print("[WARN] No se encontró la carpeta scenario_A para análisis de reps")

    if not args.skip_etl:
        print("\n[INFO] Ejecutando Pipeline ETL para Escenarios Principales...")
        run_etl(args.raw_dir, proc_dir)

    print("\n[INFO] Cargando DataFrames maestros...")
    try:
        df_summary = pd.read_csv(os.path.join(proc_dir, 'master_summary.csv'))
        
        df_latencies = pd.read_csv(os.path.join(proc_dir, 'master_latencies.csv'))
        df_latencies['Time'] = pd.to_datetime(df_latencies['Time'], format='mixed')
        
        err_path = os.path.join(proc_dir, 'master_errors.csv')
        df_errors = pd.read_csv(err_path) if os.path.exists(err_path) else pd.DataFrame()
        if not df_errors.empty: df_errors['Time'] = pd.to_datetime(df_errors['Time'], format='mixed')
        
        df_resources = pd.read_csv(os.path.join(proc_dir, 'master_resources.csv'))
        
        gc_path = os.path.join(proc_dir, 'master_gc.csv')
        df_gc = pd.read_csv(gc_path) if os.path.exists(gc_path) else pd.DataFrame()
        if not df_gc.empty: df_gc['Time'] = pd.to_datetime(df_gc['Time'], format='mixed')

    except FileNotFoundError as e:
        print(f"[ERROR FATAL] No se pudo cargar un archivo base: {e}")
        return

    print("[INFO] Calculando estadísticas y tablas LaTeX...")
    generate_statistical_tables(df_summary, df_latencies, df_resources, df_gc, proc_dir)

    print("[INFO] Generando gráficas de Línea Base (A)...")
    plots_baseline.generate_all(df_summary, df_latencies, df_gc, graph_dir)

    print("[INFO] Generando gráficas de Resiliencia (B)...")
    plots_resilience.generate_all(df_summary, df_latencies, df_resources, graph_dir)

    print("[INFO] Generando gráficas de Caos Extremo (C)...")
    plots_chaos.generate_all(df_summary, df_latencies, df_errors, df_resources, df_gc, graph_dir)

    print("[INFO] Generando gráficas Globales Comparativas...")
    plots_global.generate_all(df_summary, df_latencies, graph_dir)

    print("\n[INFO] Procesando y Generando gráficas del Soak Test...")
    soak_dir = get_dynamic_dir(args.raw_dir, 'soak')
    if soak_dir:
        soak_raw_path = os.path.join(soak_dir, 'raw')

        from src.parsers import parse_resources
        soak_dfs = []
        for res_file in glob.glob(os.path.join(soak_raw_path, '*_resources.csv')):
            fw = 'FastAPI' if 'fastapi' in os.path.basename(res_file).lower() else 'Express'
            df_s = parse_resources(res_file, apply_cold_start=True)
            if not df_s.empty:
                df_s['Framework'] = fw
                soak_dfs.append(df_s)
        if soak_dfs:
            df_soak_res = pd.concat(soak_dfs, ignore_index=True)
            plots_soak.generate_all(df_soak_res, graph_dir, proc_dir, soak_raw_path) 
    else:
        print("[WARN] No se encontró la carpeta soak")

    print("\n[OK] ¡Análisis COMPLETO al 100%! Gráficas en /graphs y Tablas en /processed.")

if __name__ == "__main__":
    main()