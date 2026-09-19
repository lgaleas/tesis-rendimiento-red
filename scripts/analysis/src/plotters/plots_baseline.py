import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patheffects import withStroke
from src.config import COLORS, PROFILE_ORDER, FRAMEWORK_ORDER

# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de etiquetas de perfil: claves internas → términos del documento
# ─────────────────────────────────────────────────────────────────────────────
PROFILE_LABELS = {
    'low':  'Perfil Bajo',
    'medium':  'Perfil Medio',
    'high': 'Perfil Alto',
    'Low':  'Perfil Bajo',
    'Medium':  'Perfil Medio',
    'High': 'Perfil Alto',
}

# Orden para el eje X de las gráficas que usan perfiles
PROFILE_DISPLAY_ORDER = [PROFILE_LABELS.get(p, p) for p in PROFILE_ORDER]


def _apply_profile_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Reemplaza los valores de la columna Profile con sus etiquetas en español."""
    df = df.copy()
    df['Profile'] = df['Profile'].map(lambda v: PROFILE_LABELS.get(v, v))
    return df


def _style_axes(ax, title: str, xlabel: str, ylabel: str, title_size: int = 13):
    """Aplica estilo común a un eje: título, etiquetas y grid sutil."""
    ax.set_title(title, pad=12, fontsize=title_size, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(axis='y', color='#e0e0e0', linewidth=0.7, linestyle='--', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')


def generate_all(df_sum, df_lat, df_gc, graph_dir):
    df_lat_A = df_lat[df_lat['Scenario'] == 'A (Ideal)'].copy()
    df_sum_A = df_sum[df_sum['Scenario'] == 'A (Ideal)'].copy()
    df_gc_A  = df_gc[df_gc['Scenario']  == 'A (Ideal)'].copy()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 1 · CDF de latencias — Perfil Alto únicamente
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_A.empty:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Distribución Acumulada de Latencias (CDF) en el Escenario A\n'
            '(Perfil Alto — 100 RPS)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = df_lat_A[
                (df_lat_A['Endpoint'] == ep) &
                (df_lat_A['Profile']  == 'high')
            ]

            if not subset.empty:
                sns.ecdfplot(
                    data=subset, x='Latency', hue='Framework',
                    palette=COLORS, linewidth=2.5,
                    ax=ax, hue_order=FRAMEWORK_ORDER
                )

                # Línea P99
                ax.axhline(0.99, color='#e74c3c', linestyle=':',
                           linewidth=1.5, alpha=0.7, label='Límite P99 (99 %)')

                x_limit = subset['Latency'].quantile(0.998) * 1.1
                y_offsets = {'FastAPI': 0.82, 'Express': 0.65}

                for fw in FRAMEWORK_ORDER:
                    fw_data = subset[subset['Framework'] == fw]
                    if fw_data.empty:
                        continue
                    p99_val = fw_data['Latency'].quantile(0.99)
                    ax.plot(p99_val, 0.99, marker='o',
                            markersize=8, color=COLORS[fw], zorder=5)
                    ax.plot([p99_val, p99_val], [0, 0.99],
                            color=COLORS[fw], linestyle='--', alpha=0.45)
                    ax.text(
                        p99_val + x_limit * 0.03, y_offsets[fw],
                        f'P99 {fw}:\n{p99_val:.2f} ms',
                        color=COLORS[fw], fontweight='bold',
                        fontsize=10, va='center',
                        bbox=dict(facecolor='white', alpha=0.92,
                                  edgecolor=COLORS[fw],
                                  boxstyle='round,pad=0.4', linewidth=1)
                    )

                ax.set_xlim(left=0, right=x_limit)
                ax.yaxis.set_major_formatter(
                    mticker.PercentFormatter(xmax=1, decimals=0)
                )

                _style_axes(
                    ax,
                    title=f'Endpoint: /{ep.lower()}',
                    xlabel='Latencia de respuesta (ms)',
                    ylabel='Proporción acumulada de peticiones' if i == 0 else ''
                )

                if ax.get_legend() is not None:
                    ax.get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels,
                   loc='lower center', ncol=3,
                   frameon=True, edgecolor='#d3d3d3',
                   bbox_to_anchor=(0.5, 0.01), fontsize=10)

        plt.tight_layout()
        fig.subplots_adjust(top=0.88, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'baseline_01_cdf_latency.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 2 · Crecimiento de CPU vs perfil de carga
    # ─────────────────────────────────────────────────────────────────────────
    if not df_sum_A.empty:
        df_sum_A_lbl = _apply_profile_labels(df_sum_A)

        fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Crecimiento del consumo promedio de CPU\n'
            'frente al aumento de inyección de peticiones',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = df_sum_A_lbl[df_sum_A_lbl['Endpoint'] == ep]

            sns.pointplot(
                data=subset,
                x='Profile', y='CPU_Mean', hue='Framework',
                palette=COLORS, markers='o', capsize=0.1, ax=ax,
                order=PROFILE_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER,
                err_kws={'linewidth': 2},
                markersize=9, linewidth=2.2
            )

            grp = (
                subset
                .groupby(['Profile', 'Framework'], observed=False)['CPU_Mean']
                .mean()
                .unstack()
            )

            for idx, p in enumerate(PROFILE_DISPLAY_ORDER):
                if p not in grp.index:
                    continue
                val_f = grp.loc[p, 'FastAPI']
                val_e = grp.loc[p, 'Express']
                if pd.notna(val_f) and pd.notna(val_e):
                    if val_f > val_e:
                        ax.annotate(f'{val_f:.1f} %', xy=(idx, val_f),
                                    xytext=(0, 15), textcoords='offset points',
                                    ha='center', color=COLORS['FastAPI'],
                                    weight='bold', fontsize=9.5)
                        ax.annotate(f'{val_e:.1f} %', xy=(idx, val_e),
                                    xytext=(0, -18), textcoords='offset points',
                                    ha='center', color=COLORS['Express'],
                                    weight='bold', fontsize=9.5)
                    else:
                        ax.annotate(f'{val_f:.1f} %', xy=(idx, val_f),
                                    xytext=(0, -18), textcoords='offset points',
                                    ha='center', color=COLORS['FastAPI'],
                                    weight='bold', fontsize=9.5)
                        ax.annotate(f'{val_e:.1f} %', xy=(idx, val_e),
                                    xytext=(0, 15), textcoords='offset points',
                                    ha='center', color=COLORS['Express'],
                                    weight='bold', fontsize=9.5)

            y_max = subset['CPU_Mean'].max() * 1.35
            ax.set_ylim(bottom=0, top=max(y_max, 5))
            ax.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda v, _: f'{v:.0f} %')
            )

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='',
                ylabel='Consumo promedio de CPU (%)' if i == 0 else ''
            )

            if ax.get_legend() is not None:
                ax.get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels,
                   loc='lower center', ncol=2,
                   frameon=True, edgecolor='#d3d3d3',
                   bbox_to_anchor=(0.5, 0.01), fontsize=10)

        plt.tight_layout()
        fig.subplots_adjust(top=0.86, bottom=0.20)
        plt.savefig(
            os.path.join(graph_dir, 'baseline_02_cpu_scaling.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 3 · Boxplots de dispersión de latencia por perfil
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_A.empty:
        df_lat_A_lbl = _apply_profile_labels(df_lat_A)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=False)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Diagramas de caja de la dispersión de latencia por perfil de carga',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = df_lat_A_lbl[df_lat_A_lbl['Endpoint'] == ep]

            sns.boxplot(
                data=subset,
                x='Profile', y='Latency', hue='Framework',
                palette=COLORS, showfliers=False, ax=ax,
                linewidth=1.5, width=0.5,
                order=PROFILE_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER
            )

            for tick, label in enumerate(PROFILE_DISPLAY_ORDER):
                for fw in FRAMEWORK_ORDER:
                    fw_data = subset[
                        (subset['Profile'] == label) &
                        (subset['Framework'] == fw)
                    ]
                    if fw_data.empty:
                        continue
                    median_val = fw_data['Latency'].median()
                    offset_x = -0.15 if fw == 'FastAPI' else 0.15
                    ax.annotate(
                        f'{median_val:.1f} ms',
                        xy=(tick + offset_x, median_val),
                        xytext=(0, 0), textcoords='offset points',
                        ha='center', va='center', color='white',
                        fontweight='bold', fontsize=9,
                        path_effects=[
                            withStroke(linewidth=2,
                                       foreground=COLORS[fw])
                        ]
                    )

            ax.set_ylim(bottom=0)
            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='',
                ylabel='Latencia (ms) — rango intercuartílico' if i == 0 else ''
            )

            if ax.get_legend() is not None:
                ax.get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels,
                   loc='lower center', ncol=2,
                   frameon=True, edgecolor='#d3d3d3',
                   bbox_to_anchor=(0.5, 0.01), fontsize=10)

        plt.tight_layout()
        fig.subplots_adjust(top=0.90, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'baseline_03_latency_boxplot.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 4 · Correlación temporal latencia ↔ pausas GC
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_A.empty and not df_gc_A.empty:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6),
                                 sharey=True, sharex=True)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Correlación temporal entre latencia de peticiones\n'
            'y pausas de bloqueo del recolector de basura (GC)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, fw in enumerate(FRAMEWORK_ORDER):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            lat_fw = df_lat_A[
                (df_lat_A['Framework'] == fw) &
                (df_lat_A['Endpoint']  == 'CPU') &
                (df_lat_A['Profile']   == 'high')
            ].copy()

            if lat_fw.empty:
                continue

            # Scatter de latencias individuales
            ax.scatter(
                lat_fw['Relative_Time'], lat_fw['Latency'],
                color=COLORS[fw], alpha=0.30, s=14,
                edgecolors='none', zorder=2, label='Peticiones individuales'
            )

            y_top = lat_fw['Latency'].quantile(0.99) * 1.5

            # Pausas GC Stop-the-World
            gc_fw = df_gc_A[
                (df_gc_A['Framework'] == fw) &
                (df_gc_A['Endpoint']  == 'CPU') &
                (df_gc_A['Profile']   == 'high')
            ].copy()

            if not gc_fw.empty:
                gc_fw_crit = gc_fw[
                    (gc_fw['Duration'] > 1.0) |
                    (gc_fw['Type'].isin([
                        'Mark/Sweep', 'Incremental', 'Weak/Phantom'
                    ]))
                ].copy()

                t_min_k6 = lat_fw['Relative_Time'].min()
                t_max_k6 = lat_fw['Relative_Time'].max()

                t0_gc = gc_fw['Time'].min()
                gc_fw_crit['Relative_GC_Time'] = (
                    gc_fw_crit['Time'] - t0_gc
                ).dt.total_seconds()

                t_end_gc  = gc_fw['Time'].max()
                t_end_k6  = lat_fw['Time'].max()
                time_offset = (t_end_k6 - t_end_gc).total_seconds()

                gc_fw_crit['Sync_Time'] = (
                    gc_fw_crit['Relative_GC_Time']
                    + time_offset + t_max_k6
                    - gc_fw_crit['Relative_GC_Time'].max()
                )

                gc_fw_final = gc_fw_crit[
                    (gc_fw_crit['Sync_Time'] >= t_min_k6) &
                    (gc_fw_crit['Sync_Time'] <= t_max_k6)
                ]

                for _, gc in gc_fw_final.iterrows():
                    h = (
                        min(gc['Duration'] * 3, y_top)
                        if min(gc['Duration'] * 3, y_top) > 0
                        else y_top * 0.5
                    )
                    ax.plot(
                        [gc['Sync_Time'], gc['Sync_Time']], [0, h],
                        color='#e74c3c', linewidth=2,
                        alpha=0.90, zorder=3
                    )

            ax.set_xlim(
                lat_fw['Relative_Time'].min() - 1,
                lat_fw['Relative_Time'].max() + 1
            )
            ax.set_ylim(bottom=0, top=y_top)

            _style_axes(
                ax,
                title=fw,
                xlabel='Tiempo dentro de la ventana estable de medición (s)',
                ylabel='Latencia de respuesta (ms)' if i == 0 else '',
                title_size=13
            )

            legend_handles = [
                Line2D(
                    [0], [0], marker='o', color='w',
                    label='Peticiones individuales',
                    markerfacecolor=COLORS[fw],
                    markersize=8, alpha=0.8
                ),
                Line2D(
                    [0], [0], color='#e74c3c', lw=2,
                    label='Pausas Stop-the-World del GC'
                ),
            ]
            ax.legend(
                handles=legend_handles,
                loc='upper center',
                bbox_to_anchor=(0.5, -0.18),
                frameon=True, edgecolor='#d3d3d3',
                ncol=2, fontsize=10
            )

        plt.tight_layout()
        fig.subplots_adjust(top=0.86, bottom=0.22)
        plt.savefig(
            os.path.join(graph_dir, 'baseline_04_latency_gc_scatter.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()