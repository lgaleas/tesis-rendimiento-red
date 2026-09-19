import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os
import numpy as np
from matplotlib.patheffects import withStroke
from matplotlib.lines import Line2D
from src.config import COLORS, PROFILE_ORDER, FRAMEWORK_ORDER

# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de etiquetas de perfil → términos oficiales del documento
# Cubre las variantes 'low', 'Low', 'medium', 'Medium', 'med', 'Med',
# 'high', 'High' que puedan aparecer en los datos.
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

# RPS objetivo por perfil (para la línea de meta en el gráfico 1)
TARGET_RPS_MAP = {
    'low':    10,
    'medium': 50,
    'med':    50,
    'high':   100,
}


def _apply_profile_labels(df):
    """Traduce la columna Profile sin modificar el DataFrame original."""
    df = df.copy()
    df['Profile'] = df['Profile'].map(lambda v: PROFILE_LABELS.get(v, v))
    return df


def _style_axes(ax, title, xlabel, ylabel, title_size=13):
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


def generate_all(df_sum, df_lat, df_res, graph_dir):
    df_lat_B = df_lat[df_lat['Scenario'] == 'B (Inestable)'].copy()
    df_sum_B = df_sum[df_sum['Scenario'] == 'B (Inestable)'].copy()
    df_res_B = df_res[df_res['Scenario'] == 'B (Inestable)'].copy()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 1 · Throughput y tasa de errores
    # ─────────────────────────────────────────────────────────────────────────
    if not df_sum_B.empty:
        df_sum_B_lbl = _apply_profile_labels(df_sum_B)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Throughput frente a metas de inyección y tasas de fallo\n'
            'Peticiones exitosas vs. meta',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]

            subset = (
                df_sum_B_lbl[df_sum_B_lbl['Endpoint'] == ep]
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
                hue_order=FRAMEWORK_ORDER
            )

            # Líneas de meta de inyección
            for idx, raw_p in enumerate(PROFILE_ORDER):
                target = TARGET_RPS_MAP.get(raw_p.lower(), None)
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

            if ax.get_legend() is not None:
                ax.get_legend().remove()

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
            os.path.join(graph_dir, 'scenario_B_01_throughput_errors.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 2 · Diagramas de violín — distribución bimodal y límite 500 ms
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_B.empty:
        df_lat_B_lbl = _apply_profile_labels(df_lat_B)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=False)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Diagramas de violín mostrando la distribución bimodal\n'
            'y el límite de falla transaccional (500 ms)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]

            subset = df_lat_B_lbl[df_lat_B_lbl['Endpoint'] == ep].copy()
            subset['Latency'] = np.clip(subset['Latency'], 0.1, 1400)

            sns.violinplot(
                data=subset,
                x='Profile', y='Latency', hue='Framework',
                palette=COLORS, split=True, inner='quart',
                cut=0, linewidth=1.2, ax=ax,
                order=PROFILE_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER
            )

            ax.axhline(
                500, color='#e74c3c', linestyle=':', linewidth=1.5,
                label='Límite de falla transaccional (500 ms)'
            )

            for tick, label in enumerate(PROFILE_DISPLAY_ORDER):
                for fw in FRAMEWORK_ORDER:
                    fw_data = subset[
                        (subset['Profile']   == label) &
                        (subset['Framework'] == fw)
                    ]
                    if fw_data.empty:
                        continue
                    median_val = fw_data['Latency'].median()
                    offset_x   = -0.15 if fw == 'FastAPI' else 0.15
                    txt = ax.text(
                        tick + offset_x, median_val,
                        f'{median_val:.0f} ms',
                        ha='center', va='center',
                        color='white', fontweight='bold', fontsize=9
                    )
                    txt.set_path_effects(
                        [withStroke(linewidth=2.5,
                                    foreground=COLORS[fw])]
                    )
                    p99_val = fw_data['Latency'].quantile(0.99)
                    ax.text(
                        tick + offset_x, p99_val + 20,
                        f'P99 {p99_val:.0f} ms',
                        ha='center', va='bottom',
                        color=COLORS[fw], fontweight='bold', fontsize=7
                    )

            ax.set_ylim(bottom=0, top=1500)
            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='',
                ylabel='Latencia (ms) — escala lineal' if i == 0 else ''
            )

            if ax.get_legend() is not None:
                ax.get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc='lower center', ncol=3,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.86, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_B_02_latency_violin.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 3 · Evolución temporal de conexiones TCP — Perfil Alto
    # ─────────────────────────────────────────────────────────────────────────
    if not df_res_B.empty and 'tcp_conns' in df_res_B.columns:
        # Filtrar Perfil Alto usando las claves originales del DataFrame
        high_keys = [k for k, v in PROFILE_LABELS.items() if v == 'Perfil Alto']
        df_tcp_high = df_res_B[df_res_B['Profile'].isin(high_keys)]

        fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Evolución temporal de las conexiones TCP\n'
            'en estado ESTABLISHED (Perfil Alto)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]
            subset = df_tcp_high[df_tcp_high['Endpoint'] == ep]

            if not subset.empty:
                sns.lineplot(
                    data=subset,
                    x='Relative_Time', y='tcp_conns', hue='Framework',
                    palette=COLORS, linewidth=2.5, ax=ax,
                    hue_order=FRAMEWORK_ORDER, errorbar=None
                )

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='Tiempo del experimento (segundos)',
                ylabel='Conexiones TCP en estado ESTABLISHED' if i == 0 else ''
            )

            if ax.get_legend() is not None:
                ax.get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc='lower center', ncol=2,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.86, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_B_03_tcp_temporal.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 4 · Evolución temporal comparativa Mediana / P95
    # ─────────────────────────────────────────────────────────────────────────
    if not df_lat_B.empty and 'Relative_Time' in df_lat_B.columns:
        high_keys = [k for k, v in PROFILE_LABELS.items() if v == 'Perfil Alto']

        fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            'Evolución temporal comparativa entre la latencia\n'
            'Mediana y el P95 durante el experimento',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, ep in enumerate(['CPU', 'IO']):
            ax = axes[i]

            lat_sub = df_lat_B[
                (df_lat_B['Endpoint'] == ep) &
                (df_lat_B['Profile'].isin(high_keys))
            ].copy()

            if not lat_sub.empty:
                lat_sub['Window'] = lat_sub['Relative_Time'].apply(
                    lambda x: int(x)
                )
                lat_agg = (
                    lat_sub
                    .groupby(['Window', 'Framework'])['Latency']
                    .agg(
                        Median='median',
                        P95=lambda x: np.percentile(x, 95),
                        P99=lambda x: np.percentile(x, 99),
                    )
                    .reset_index()
                )

                for fw in FRAMEWORK_ORDER:
                    fw_lat = lat_agg[lat_agg['Framework'] == fw]
                    if fw_lat.empty:
                        continue
                    ax.plot(
                        fw_lat['Window'], fw_lat['Median'],
                        color=COLORS[fw], linewidth=2,
                        label=f'Mediana {fw}'
                    )
                    ax.plot(
                        fw_lat['Window'], fw_lat['P95'],
                        color=COLORS[fw], linewidth=1.5,
                        linestyle='--', alpha=0.65,
                        label=f'P95 {fw}'
                    )
                    ax.plot(
                        fw_lat['Window'], fw_lat['P99'],
                        color=COLORS[fw], linewidth=1.2,
                        linestyle=':', alpha=0.80,
                        label=f'P99 {fw}'
                    )

            _style_axes(
                ax,
                title=f'Endpoint: /{ep.lower()}',
                xlabel='Tiempo del experimento (segundos)',
                ylabel='Latencia (ms)' if i == 0 else ''
            )

            if ax.get_legend() is not None:
                ax.get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc='lower center', ncol=4,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.86, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir, 'scenario_B_04_latency_temporal.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()