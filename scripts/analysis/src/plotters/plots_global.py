import matplotlib.pyplot as plt
import seaborn as sns
import os
import pandas as pd
import numpy as np
from math import pi
from src.config import COLORS, FRAMEWORK_ORDER, SCENARIO_ORDER

# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de nombres de escenario → términos oficiales del documento
# ─────────────────────────────────────────────────────────────────────────────
SCENARIO_LABELS = {
    'A (Ideal)':      'A (Línea Base)',
    'B (Inestable)':  'B (Red Inestable)',
    'C (Caos)':       'C (Red Saturada)',
}

# Paleta de colores para escenarios con las claves originales Y las traducidas
SCENARIO_COLORS = {
    'A (Ideal)':                   '#2ecc71',
    'B (Inestable)':               '#f39c12',
    'C (Caos)':                    '#e74c3c',
    'A (Línea Base)':    '#2ecc71',
    'B (Red Inestable)': '#f39c12',
    'C (Red Saturada)':  '#e74c3c',
}

# Perfil alto: claves crudas que pueden aparecer en los datos
HIGH_KEYS = ['high', 'High']


def _apply_scenario_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Traduce la columna Scenario con los nombres oficiales del documento."""
    df = df.copy()
    df['Scenario'] = df['Scenario'].map(
        lambda v: SCENARIO_LABELS.get(v, v)
    )
    return df


def _style_axes(ax, title: str, xlabel: str, ylabel: str,
                title_size: int = 13):
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


def generate_all(df_sum, df_lat, graph_dir):
    # Filtrar Perfil Alto usando las claves originales del DataFrame
    df_high = df_sum[df_sum['Profile'].isin(HIGH_KEYS)].copy()
    if df_high.empty:
        return

    # Traducir escenarios para todos los subconjuntos que se usarán
    df_high_lbl = _apply_scenario_labels(df_high)

    # Orden de escenarios con las etiquetas traducidas
    scenario_display_order = [
        SCENARIO_LABELS.get(s, s) for s in SCENARIO_ORDER
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 1 · Evolución del P99 de latencia por escenario
    # ─────────────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle(
        'Evolución del P99 de latencia en los tres escenarios (Perfil Alto)',
        fontsize=15, fontweight='bold', y=0.98
    )

    for i, ep in enumerate(['CPU', 'IO']):
        ax = axes[i]
        subset = df_high_lbl[df_high_lbl['Endpoint'] == ep]

        sns.lineplot(
            data=subset,
            x='Scenario', y='Latency_P99', hue='Framework',
            palette=COLORS, marker='o', markersize=12,
            linewidth=3, ax=ax,
            hue_order=FRAMEWORK_ORDER, errorbar=None
        )

        ax.axhline(
            500, color='#e74c3c', linestyle=':', linewidth=2,
            zorder=0, label='Límite de falla transaccional (500 ms)'
        )
        ax.text(
            0, 520,
            ' Límite de SLO (500 ms)',
            color='#e74c3c', fontsize=10, fontweight='bold'
        )

        grp = (
            subset
            .groupby(['Scenario', 'Framework'], observed=False)['Latency_P99']
            .mean()
            .reset_index()
        )
        for _, row in grp.dropna().iterrows():
            sc_idx = scenario_display_order.index(row['Scenario']) \
                if row['Scenario'] in scenario_display_order else 0
            offset = 15 if row['Framework'] == 'Express' else -25
            ax.annotate(
                f"{row['Latency_P99']:.0f} ms",
                (sc_idx, row['Latency_P99']),
                textcoords='offset points', xytext=(0, offset),
                ha='center', fontsize=9, fontweight='bold',
                color=COLORS[row['Framework']]
            )

        _style_axes(
            ax,
            title=f'Endpoint: /{ep.lower()}',
            xlabel='Escenario',
            ylabel='Latencia P99 (ms)' if i == 0 else ''
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
    fig.subplots_adjust(top=0.88, bottom=0.18)
    plt.savefig(
        os.path.join(graph_dir, 'comp_01_latency_evolution.png'),
        dpi=300, facecolor=fig.get_facecolor()
    )
    plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 2 · Throughput real por escenario
    # ─────────────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle(
        'Throughput real alcanzado por escenario (Perfil Alto)',
        fontsize=15, fontweight='bold', y=0.98
    )

    for i, ep in enumerate(['CPU', 'IO']):
        ax = axes[i]
        subset = df_high_lbl[df_high_lbl['Endpoint'] == ep]

        sns.barplot(
            data=subset,
            x='Scenario', y='Throughput', hue='Framework',
            palette=COLORS, ax=ax, alpha=0.9,
            hue_order=FRAMEWORK_ORDER,
            order=scenario_display_order,
            errorbar=None, edgecolor='white'
        )

        ax.axhline(
            100, color='#27ae60', linestyle='--',
            linewidth=2, zorder=0, label='Carga inyectada (100 RPS)'
        )

        for container in ax.containers:
            ax.bar_label(
                container, fmt='%.1f', padding=3,
                fontweight='bold', color='#333333'
            )

        _style_axes(
            ax,
            title=f'Endpoint: /{ep.lower()}',
            xlabel='Escenario',
            ylabel='Throughput exitoso (RPS)' if i == 0 else ''
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
    fig.subplots_adjust(top=0.88, bottom=0.18)
    plt.savefig(
        os.path.join(graph_dir, 'comp_02_throughput.png'),
        dpi=300, facecolor=fig.get_facecolor()
    )
    plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 3 · Tasa de errores por escenario
    # ─────────────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle(
        'Tasa de errores por escenario (Perfil Alto)',
        fontsize=15, fontweight='bold', y=0.98
    )

    for i, ep in enumerate(['CPU', 'IO']):
        ax = axes[i]
        subset = df_high_lbl[df_high_lbl['Endpoint'] == ep]

        sns.barplot(
            data=subset,
            x='Scenario', y='Error_Rate', hue='Framework',
            palette=COLORS, ax=ax,
            hue_order=FRAMEWORK_ORDER,
            order=scenario_display_order,
            errorbar=None, edgecolor='white'
        )

        for container in ax.containers:
            ax.bar_label(
                container, fmt='%.1f %%', padding=3,
                fontweight='bold', color='#c0392b'
            )

        ax.set_ylim(0, 100)
        _style_axes(
            ax,
            title=f'Endpoint: /{ep.lower()}',
            xlabel='Escenario',
            ylabel='Tasa de errores (%)' if i == 0 else ''
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
    fig.subplots_adjust(top=0.88, bottom=0.18)
    plt.savefig(
        os.path.join(graph_dir, 'comp_03_error_rate.png'),
        dpi=300, facecolor=fig.get_facecolor()
    )
    plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 4 · Consumo de CPU y RAM por escenario
    # ─────────────────────────────────────────────────────────────────────────
    EP_TITLES = {
        'CPU': ('Consumo de CPU a través de los escenarios'
                ' (/cpu, Perfil Alto)'),
        'IO':  ('Consumo de CPU y RAM a través de los escenarios'
                ' (/io, Perfil Alto)'),
    }

    for ep in ['CPU', 'IO']:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            EP_TITLES[ep],
            fontsize=15, fontweight='bold', y=0.98
        )

        subset = df_high_lbl[df_high_lbl['Endpoint'] == ep]

        # Panel izquierdo: CPU
        sns.barplot(
            data=subset,
            x='Scenario', y='CPU_Mean', hue='Framework',
            palette=COLORS, ax=axes[0],
            order=scenario_display_order,
            hue_order=FRAMEWORK_ORDER,
            errorbar=None, edgecolor='white'
        )
        for c in axes[0].containers:
            axes[0].bar_label(c, fmt='%.1f %%', padding=3)

        _style_axes(
            axes[0],
            title='Consumo de CPU',
            xlabel='Escenario',
            ylabel='Uso de CPU (%)'
        )
        if axes[0].get_legend() is not None:
            axes[0].get_legend().remove()

        # Panel derecho: RAM
        sns.barplot(
            data=subset,
            x='Scenario', y='RAM_Mean', hue='Framework',
            palette=COLORS, ax=axes[1],
            order=scenario_display_order,
            hue_order=FRAMEWORK_ORDER,
            errorbar=None, edgecolor='white'
        )
        for c in axes[1].containers:
            axes[1].bar_label(c, fmt='%.0f MiB', padding=3)

        _style_axes(
            axes[1],
            title='Consumo de RAM',
            xlabel='Escenario',
            ylabel='Memoria RAM (MiB)'
        )
        if axes[1].get_legend() is not None:
            axes[1].get_legend().remove()

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels,
            loc='lower center', ncol=2,
            frameon=True, edgecolor='#d3d3d3',
            bbox_to_anchor=(0.5, 0.01), fontsize=10
        )

        plt.tight_layout()
        fig.subplots_adjust(top=0.88, bottom=0.18)
        plt.savefig(
            os.path.join(graph_dir,
                         f'comp_04_resources_{ep.lower()}.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 5 · Radares de eficiencia comparativa
    # ─────────────────────────────────────────────────────────────────────────
    def normalize(df_col, higher_better=True):
        max_v, min_v = df_col.max(), df_col.min()
        if max_v == min_v:
            return pd.Series([1.0] * len(df_col), index=df_col.index)
        return (
            (df_col - min_v) / (max_v - min_v)
            if higher_better
            else (max_v - df_col) / (max_v - min_v)
        )

    df_radar = df_high_lbl.copy()
    m_conf = {
        'Throughput':  ('Throughput',           True),
        'Latency_P99': ('Latencia P99 (Inv)',   False),
        'Error_Rate':  ('Tasa errores (Inv)',   False),
        'CPU_Mean':    ('CPU (Inv)',             False),
        'RAM_Mean':    ('RAM (Inv)',             False),
    }

    for col, (name, is_better) in m_conf.items():
        df_radar[name] = normalize(df_radar[col], is_better)

    categories = [v[0] for v in m_conf.values()]
    N = len(categories)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    for ep in ['CPU', 'IO']:
        fig, axes = plt.subplots(
            1, 3, figsize=(18, 6),
            subplot_kw=dict(polar=True)
        )
        fig.patch.set_facecolor('#FAFAFA')

        fig.suptitle(
            f'Radares de eficiencia comparativa por endpoint y escenario'
            f' — Endpoint: /{ep.lower()}  (mayor área = mejor)',
            fontsize=15, fontweight='bold', y=0.98
        )

        for i, sc_raw in enumerate(SCENARIO_ORDER):
            sc = SCENARIO_LABELS.get(sc_raw, sc_raw)
            ax = axes[i]
            ax.set_title(sc, weight='bold', position=(0.5, 1.1), fontsize=11)
            ax.set_theta_offset(pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=10)
            ax.set_yticks([0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels([])
            ax.set_ylim(0, 1.05)
            ax.set_facecolor('#FAFAFA')

            for fw in FRAMEWORK_ORDER:
                fw_data = df_radar[
                    (df_radar['Endpoint']  == ep) &
                    (df_radar['Scenario']  == sc) &
                    (df_radar['Framework'] == fw)
                ]
                if fw_data.empty:
                    continue
                values = fw_data[categories].mean().values.flatten().tolist()
                values += values[:1]

                ax.plot(
                    angles, values,
                    color=COLORS[fw], linewidth=2,
                    linestyle='solid', label=fw
                )
                ax.fill(angles, values, color=COLORS[fw], alpha=0.25)

            if i == 2:
                ax.legend(
                    loc='center left',
                    bbox_to_anchor=(1.2, 0.5),
                    frameon=False
                )

        plt.tight_layout()
        fig.subplots_adjust(top=0.82)
        plt.savefig(
            os.path.join(graph_dir, f'comp_05_radar_{ep.lower()}.png'),
            dpi=300, facecolor=fig.get_facecolor()
        )
        plt.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Gráfico 6 · Temperatura máxima de CPU
    # ─────────────────────────────────────────────────────────────────────────
    if 'CPU_Temp_Max_C' in df_sum.columns:
        grouped = (
            df_sum
            .groupby(['Endpoint', 'Framework', 'Scenario'], observed=False)
            ['CPU_Temp_Max_C']
            .max()
            .reset_index()
        )
        grouped = _apply_scenario_labels(grouped)

        for ep in ['CPU', 'IO']:
            subset = grouped[grouped['Endpoint'] == ep]
            if subset.empty or subset['CPU_Temp_Max_C'].max() <= 0:
                continue

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#FAFAFA')

            sns.barplot(
                data=subset,
                x='Framework', y='CPU_Temp_Max_C', hue='Scenario',
                palette=SCENARIO_COLORS,
                ax=ax, edgecolor='white',
                order=FRAMEWORK_ORDER,
                hue_order=scenario_display_order
            )

            ax.axhline(
                80, color='red', linestyle='--', linewidth=2,
                label='Límite operativo (80 °C)'
            )

            for container in ax.containers:
                ax.bar_label(
                    container, fmt='%.1f °C',
                    padding=3, fontsize=9, fontweight='bold'
                )

            _style_axes(
                ax,
                title=(
                    f'Temperatura máxima de CPU durante las pruebas'
                    f' del endpoint /{ep.lower()}'
                ),
                xlabel='Framework',
                ylabel='Temperatura (°C)'
            )
            ax.set_ylim(0, 85)

            if ax.get_legend() is not None:
                ax.get_legend().remove()

            handles, labels = ax.get_legend_handles_labels()
            fig.legend(
                handles, labels,
                loc='lower center', ncol=4,
                frameon=True, edgecolor='#d3d3d3',
                bbox_to_anchor=(0.5, 0.01), fontsize=10
            )

            plt.tight_layout()
            fig.subplots_adjust(top=0.88, bottom=0.18)
            plt.savefig(
                os.path.join(
                    graph_dir,
                    f'comp_06_temperature_bars_{ep.lower()}.png'
                ),
                dpi=300, facecolor=fig.get_facecolor()
            )
            plt.close()