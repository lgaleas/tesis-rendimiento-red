import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
import pandas as pd
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from matplotlib.patheffects import withStroke
from src.config import COLORS, PROFILE_ORDER, FRAMEWORK_ORDER

# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de etiquetas de perfil → términos oficiales del documento
# ─────────────────────────────────────────────────────────────────────────────
PROFILE_LABELS = {
    'low':    'Perfil Bajo',
    'Low':    'Perfil Bajo',
    'med':    'Perfil Medio',
    'Med':    'Perfil Medio',
    'medium': 'Perfil Medio',
    'Medium': 'Perfil Medio',
    'high':   'Perfil Alto',
    'High':   'Perfil Alto',
}

PROFILE_DISPLAY_ORDER = [PROFILE_LABELS.get(p, p) for p in PROFILE_ORDER]

TARGET_RPS_MAP = {
    'low':    10,
    'med':    50,
    'medium': 50,
    'high':   100,
}

# Claves crudas que corresponden a "Perfil Alto"
HIGH_KEYS = [k for k, v in PROFILE_LABELS.items() if v == 'Perfil Alto']


def _apply_profile_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Traduce la columna Profile sin modificar el DataFrame original."""
    df = df.copy()
    df['Profile'] = df['Profile'].map(lambda v: PROFILE_LABELS.get(v, v))
    return df


def _style_axes(ax, title: str, xlabel: str, ylabel: str, title_size: int = 13):
    """Estilo visual común: fondo claro, grid sutil, spines suavizados."""
    ax.set_title(title, pad=12, fontsize=title_size, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(axis='y', color='#e0e0e0', linewidth=0.7,
            linestyle='--', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')
    ax.set_facecolor('#FAFAFA')


def generate_all(df_sum, df_lat, df_err, df_res, df_gc, graph_dir):
    df_lat_C = df_lat[df_lat['Scenario'] == 'C (Caos)'].copy()
    df_sum_C = df_sum[df_sum['Scenario'] == 'C (Caos)'].copy()
    df_res_C = df_res[df_res['Scenario'] == 'C (Caos)'].copy()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 1 · Violines en escala logarítmica
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_C.empty:
        df_lat_C_lbl = _apply_profile_labels(df_lat_C)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Distribución de latencias en escala logarítmica (Escenario C)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = df_lat_C_lbl[df_lat_C_lbl['Endpoint'] == ep].copy()
            subset['Latency'] = np.clip(subset['Latency'], 0.1, None)

            sns.violinplot(
                data=subset,
                x='Profile', y='Latency', hue='Framework',
                palette=COLORS, split=True, inner='quart',
                cut=0, linewidth=1.2, ax=ax,
                order=PROFILE_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER,
                legend=False
            )

            ax.axhline(500, color='#e74c3c', linestyle=':', linewidth=1.5)
            ax.text(
                ax.get_xlim()[1], 500,
                '  Límite SLO (500 ms)',
                color='#e74c3c', va='center', ha='left',
                fontsize=9, fontweight='bold'
            )
            ax.axhline(100, color='#7f8c8d', linestyle='--',
                       linewidth=1, alpha=0.5)
            ax.text(
                ax.get_xlim()[1], 100,
                '  100 ms',
                color='#7f8c8d', va='center', ha='left', fontsize=9
            )

            ax.set_yscale('log')
            ax.yaxis.set_major_formatter(
                ticker.FuncFormatter(lambda y, _: f'{y:g}')
            )

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='',
                ylabel='Latencia (ms) — escala logarítmica' if i == 0 else ''
            )
            # El grid sobre escala log necesita también líneas menores visibles
            ax.grid(which='minor', axis='y', color='#eeeeee',
                    linewidth=0.4, linestyle='--')

        legend_elements = [
            Line2D([0], [0], color=COLORS[fw], lw=4, label=fw)
            for fw in FRAMEWORK_ORDER
        ]
        fig.legend(
            handles=legend_elements,
            loc='lower center', ncol=2,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.88, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_C_01_latency_violin_log.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 2 · Throughput y tasa de errores
    # ─────────────────────────────────────────────────────────────────────────
    if not df_sum_C.empty:
        df_sum_C_lbl = _apply_profile_labels(df_sum_C)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Throughput y tasa de errores en el Escenario C\n'
            'Peticiones exitosas',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = (
                df_sum_C_lbl[df_sum_C_lbl['Endpoint'] == ep]
                .groupby(['Profile', 'Framework'], observed=False)
                .agg(Throughput=('Throughput', 'mean'),
                     Error_Rate=('Error_Rate', 'mean'))
                .reset_index()
            )

            sns.barplot(
                data=subset,
                x='Profile', y='Throughput', hue='Framework',
                palette=COLORS, ax=ax, edgecolor='white',
                order=PROFILE_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER,
                legend=False
            )

            # Líneas de meta de inyección
            for idx, raw_p in enumerate(PROFILE_ORDER):
                target = TARGET_RPS_MAP.get(raw_p.lower())
                if target is not None:
                    ax.plot(
                        [idx - 0.4, idx + 0.4], [target, target],
                        color='#27ae60', linestyle='--',
                        linewidth=2, zorder=3
                    )

            # Anotaciones por barra
            for hue_idx, container in enumerate(ax.containers):
                if hue_idx >= len(FRAMEWORK_ORDER):
                    continue
                fw_name = FRAMEWORK_ORDER[hue_idx]

                for bar_idx, bar in enumerate(container):
                    if bar_idx >= len(PROFILE_DISPLAY_ORDER):
                        continue
                    profile_display = PROFILE_DISPLAY_ORDER[bar_idx]
                    row = subset[
                        (subset['Framework'] == fw_name) &
                        (subset['Profile']   == profile_display)
                    ]
                    if row.empty:
                        continue
                    err_val = row['Error_Rate'].values[0]
                    tp_val  = row['Throughput'].values[0]

                    if err_val > 0.5:
                        ax.annotate(
                            f'Falla:\n{err_val:.1f} %',
                            xy=(bar.get_x() + bar.get_width() / 2,
                                bar.get_height()),
                            xytext=(0, 5),
                            textcoords='offset points',
                            ha='center', va='bottom',
                            color='#c0392b', fontweight='bold', fontsize=9
                        )
                    else:
                        ax.annotate(
                            f'{tp_val:.1f} rps',
                            xy=(bar.get_x() + bar.get_width() / 2,
                                bar.get_height()),
                            xytext=(0, 3),
                            textcoords='offset points',
                            ha='center', va='bottom',
                            color='#333333', fontsize=9
                        )

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='',
                ylabel='Throughput (peticiones por segundo)' if i == 0 else ''
            )

        custom_lines = [
            plt.Rectangle((0, 0), 1, 1,
                           fc=COLORS['FastAPI'], edgecolor='none'),
            plt.Rectangle((0, 0), 1, 1,
                           fc=COLORS['Express'], edgecolor='none'),
            Line2D([0], [0], color='#27ae60', lw=2, linestyle='--'),
        ]
        fig.legend(
            custom_lines,
            ['FastAPI', 'Express', 'Metas de inyección'],
            loc='lower center', ncol=3,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.88, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_C_02_throughput_errors.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 3 · Evolución de conexiones TCP — Perfil Alto
    # ─────────────────────────────────────────────────────────────────────────
    if not df_res_C.empty and 'tcp_conns' in df_res_C.columns:
        df_tcp_high = df_res_C[df_res_C['Profile'].isin(HIGH_KEYS)]

        fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Evolución de conexiones TCP en el Escenario C (Perfil Alto)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = df_tcp_high[df_tcp_high['Endpoint'] == ep]
            if not subset.empty:
                sns.lineplot(
                    data=subset,
                    x='Relative_Time', y='tcp_conns', hue='Framework',
                    palette=COLORS, linewidth=2.5, ax=ax,
                    hue_order=FRAMEWORK_ORDER,
                    errorbar=None, legend=False
                )

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='Tiempo del experimento (segundos)',
                ylabel='Conexiones TCP en estado ESTABLISHED' if i == 0 else ''
            )

        legend_elements = [
            Line2D([0], [0], color=COLORS[fw], lw=2, label=fw)
            for fw in FRAMEWORK_ORDER
        ]
        fig.legend(
            handles=legend_elements,
            loc='lower center', ncol=2,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.88, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_C_03_tcp_temporal.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 4 · Histograma de latencias — Perfil Alto
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_C.empty:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Histograma de latencias en el Escenario C (Perfil Alto)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            ax.set_facecolor('#FAFAFA')

            subset = df_lat_C[
                (df_lat_C['Endpoint'] == ep) &
                (df_lat_C['Profile'].isin(HIGH_KEYS))
            ]

            if not subset.empty:
                x_limit = subset['Latency'].quantile(0.999)

                sns.histplot(
                    data=subset,
                    x='Latency', hue='Framework',
                    palette=COLORS, element='step',
                    fill=True, bins=50, alpha=0.3,
                    ax=ax, common_norm=False,
                    hue_order=FRAMEWORK_ORDER,
                    legend=False
                )

                ax.axvline(1000, color='#c0392b',
                           linestyle='-', linewidth=2, alpha=0.9)
                ax.text(
                    1020, ax.get_ylim()[1] * 0.90,
                    'Timeout (1 s)',
                    color='#c0392b', va='top', ha='left',
                    fontsize=11, fontweight='bold', rotation=90
                )

                y_pos = {'FastAPI': 0.85, 'Express': 0.75}
                for fw in FRAMEWORK_ORDER:
                    fw_data = subset[subset['Framework'] == fw]
                    if fw_data.empty:
                        continue
                    p99_val = fw_data['Latency'].quantile(0.99)
                    ax.axvline(
                        p99_val, color=COLORS[fw],
                        linestyle='--', linewidth=2, alpha=0.8
                    )
                    ax.text(
                        p99_val - 15,
                        ax.get_ylim()[1] * y_pos[fw],
                        f'P99 {fw}: {p99_val:.0f} ms',
                        color=COLORS[fw], ha='right', va='center',
                        fontsize=10, fontweight='bold',
                        bbox=dict(facecolor='white', alpha=0.7,
                                  edgecolor='none', pad=0.5)
                    )

                ax.set_xlim(left=0, right=max(x_limit, 1100))

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='Latencia (ms)',
                ylabel='Frecuencia (cantidad de peticiones)' if i == 0 else ''
            )

        custom_lines = [
            Line2D([0], [0], color=COLORS['FastAPI'], lw=4),
            Line2D([0], [0], color=COLORS['Express'], lw=4),
            Line2D([0], [0], color='#c0392b', lw=2, linestyle='-'),
        ]
        fig.legend(
            custom_lines,
            ['FastAPI', 'Express', 'Timeout (1 s)'],
            loc='lower center', ncol=3,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.88, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_C_04_latency_histogram.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 5 · Series temporales P99 + tasa de fallos — Perfil Alto
    # ─────────────────────────────────────────────────────────────────────────
    df_err_C = (
        df_err[df_err['Scenario'] == 'C (Caos)'].copy()
        if not df_err.empty else pd.DataFrame()
    )

    if not df_lat_C.empty and not df_err_C.empty:
        for ep in ['CPU', 'IO']:
            fig, (ax1, ax2) = plt.subplots(
                2, 1, figsize=(15, 8),
                sharex=True,
                gridspec_kw={'height_ratios': [2, 1]}
            )
            fig.patch.set_facecolor('#FAFAFA')

            fig.suptitle(
                f'Evolución temporal del rendimiento en el Escenario C\n'
                f'bajo el Perfil Alto (Endpoint: /{ep.lower()})',
                fontsize=15, fontweight='bold', y=0.98
            )

            lat_sub = df_lat_C[
                (df_lat_C['Endpoint'] == ep) &
                (df_lat_C['Profile'].isin(HIGH_KEYS))
            ].copy()

            err_sub = df_err_C[
                (df_err_C['Endpoint'] == ep) &
                (df_err_C['Profile'].isin(HIGH_KEYS))
            ].copy()

            if not lat_sub.empty and not err_sub.empty:
                max_sec = (
                    min(lat_sub['Relative_Time'].max(),
                        err_sub['Relative_Time'].max()) - 1
                )
                lat_sub = lat_sub[lat_sub['Relative_Time'] <= max_sec]
                err_sub = err_sub[err_sub['Relative_Time'] <= max_sec]

            # ── Panel superior: latencia P99 ──────────────────────────────
            if not lat_sub.empty:
                lat_sub['Window'] = lat_sub['Relative_Time'].apply(int)
                lat_agg = (
                    lat_sub
                    .groupby(['Window', 'Framework'], observed=False)['Latency']
                    .quantile(0.99)
                    .reset_index()
                )
                for fw in FRAMEWORK_ORDER:
                    fw_lat = lat_agg[lat_agg['Framework'] == fw]
                    ax1.plot(
                        fw_lat['Window'], fw_lat['Latency'],
                        color=COLORS[fw], linewidth=2,
                        label=f'{fw} (P99)'
                    )

            ax1.set_facecolor('#FAFAFA')
            ax1.set_ylabel('Latencia P99 (ms)', fontsize=12)
            ax1.axhline(
                500, color='#e74c3c', linestyle=':', linewidth=1.5,
                alpha=0.8, label='Límite SLO (500 ms)'
            )
            ax1.axhline(
                1000, color='#c0392b', linestyle='-', linewidth=2,
                alpha=0.9, label='Timeout (1 s)'
            )
            ax1.set_ylim(bottom=0, top=1100)
            ax1.legend(loc='lower right', frameon=True, ncol=2)
            ax1.grid(True, linestyle='--', alpha=0.3, color='#e0e0e0')
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)

            # ── Panel inferior: tasa de fallos ────────────────────────────
            if not err_sub.empty:
                err_sub['Window'] = err_sub['Relative_Time'].apply(int)
                err_agg = (
                    err_sub
                    .groupby(['Window', 'Framework'], observed=False)['Failed']
                    .mean()
                    .reset_index()
                )
                err_agg['Failed_Pct'] = err_agg['Failed'] * 100

                for fw in FRAMEWORK_ORDER:
                    fw_err = err_agg[err_agg['Framework'] == fw]
                    ax2.plot(
                        fw_err['Window'], fw_err['Failed_Pct'],
                        color=COLORS[fw], linestyle='-',
                        linewidth=2, alpha=0.8, label=fw
                    )

            ax2.set_facecolor('#FAFAFA')
            ax2.set_ylabel('Tasa de fallos (%)', fontsize=12)
            ax2.set_xlabel(
                'Tiempo del experimento (segundos)', fontsize=12
            )
            ax2.set_ylim(bottom=0, top=105)
            ax2.axhline(
                5, color='#7f8c8d', linestyle=':',
                linewidth=1.5, label='Tolerancia máxima (5 %)'
            )
            ax2.legend(loc='upper right', frameon=True, ncol=3)
            ax2.grid(True, linestyle='--', alpha=0.3, color='#e0e0e0')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)

            plt.tight_layout()
            fig.subplots_adjust(top=0.90)
            plt.savefig(
                os.path.join(
                    graph_dir,
                    f'scenario_C_05_timeseries_{ep.lower()}.png'
                ),
                dpi=300, facecolor=fig.get_facecolor()
            )
            plt.close()