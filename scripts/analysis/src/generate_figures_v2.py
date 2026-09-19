import os
import sys
import glob
import json
import re
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from math import pi
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ANALYSIS_DIR = os.path.dirname(_THIS_DIR)
if _ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, _ANALYSIS_DIR)

from src.parsers import parse_resources


COLORS = {'FastAPI': '#1f77b4', 'Express': '#ff7f0e'}
FRAMEWORK_ORDER = ['FastAPI', 'Express']
PROFILE_ORDER = ['low', 'medium', 'high']
SCENARIO_ORDER = ['A (Ideal)', 'B (Inestable)', 'C (Caos)']

SCENARIO_LABELS = {
    'A (Ideal)':     'A (Línea Base)',
    'B (Inestable)': 'B (Red Inestable)',
    'C (Caos)':      'C (Red Saturada)',
}
SCENARIO_DISPLAY_ORDER = [SCENARIO_LABELS[s] for s in SCENARIO_ORDER]

_PROFILE_LABELS_V2 = {
    'low': 'Perfil Bajo', 'Low': 'Perfil Bajo',
    'med': 'Perfil Medio', 'Med': 'Perfil Medio',
    'medium': 'Perfil Medio', 'Medium': 'Perfil Medio',
    'high': 'Perfil Alto', 'High': 'Perfil Alto',
}
_PROFILE_DISPLAY_ORDER_V2 = [_PROFILE_LABELS_V2.get(p, p) for p in PROFILE_ORDER]


def setup_theme():
    sns.set_theme(style="whitegrid", rc={
        "axes.spines.right": False,
        "axes.spines.top": False,
        "grid.alpha": 0.4,
        "grid.linestyle": "--",
        "axes.edgecolor": "#b0b0b0",
        "patch.linewidth": 1.5
    })
    plt.rcParams.update({'font.size': 11.5, 'axes.titlesize': 15,
                          'axes.labelsize': 13})


def _style_axes(ax, title, xlabel, ylabel, title_size=22):
    ax.set_title(title, pad=10, fontsize=title_size, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=19)
    ax.set_ylabel(ylabel, fontsize=19)
    ax.tick_params(axis='both', labelsize=17.5)
    ax.grid(axis='y', color='#e0e0e0', linewidth=0.7, linestyle='--', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')
    ax.set_facecolor('#FAFAFA')


def get_dynamic_dir(base_path, prefix):
    matches = glob.glob(os.path.join(base_path, f"{prefix}*"))
    return matches[0] if matches else None


TC = {
    "bg":          "#F7F9FC",
    "host_fill":   "#F0F4F8",  "host_edge":   "#4A5568",
    "docker_fill": "#EBF4FB",  "docker_edge": "#7BAFD4",
    "cont_fill":   "#FFFFFF",  "cont_edge":   "#A0AEC0",
    "netem_fill":  "#FFF8E1",  "netem_edge":  "#D4890A",
    "app_fill":    "#E8F4FD",  "app_edge":    "#3A8FC8",
    "mock_fill":   "#E8F8F0",  "mock_edge":   "#2D9E6B",
    "load_fill":   "#EAECEE",  "load_edge":   "#6C7A89",
    "txt":         "#1A202C",  "muted":       "#4A5568",
}
TOPO_NS = {
    "netem": (TC["netem_fill"], TC["netem_edge"]),
    "app":   (TC["app_fill"],   TC["app_edge"]),
    "mock":  (TC["mock_fill"],  TC["mock_edge"]),
    "load":  (TC["load_fill"],  TC["load_edge"]),
}
FONT = "DejaVu Sans"
TOPO_FS_SCALE = 1.28


def _topo_rbox(ax, x, y, w, h, fc, ec, lw=1.8, rs=0.015, z=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={rs}",
        fc=fc, ec=ec, lw=lw, zorder=z))


def _topo_node(ax, x, y, w, h, sk, label, sub=None, fs=12, sfs=10, lw=2, rs=0.012, z=3):
    fs, sfs = fs * TOPO_FS_SCALE, sfs * TOPO_FS_SCALE
    fc, ec = TOPO_NS[sk] if isinstance(sk, str) else sk
    _topo_rbox(ax, x, y, w, h, fc, ec, lw=lw, rs=rs, z=z)
    cx, cy = x + w / 2, y + h / 2
    if sub:
        ax.text(cx, cy + h * .15, label, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=TC["txt"], fontfamily=FONT, zorder=z + 1)
        ax.text(cx, cy - h * .22, sub, ha="center", va="center",
                fontsize=sfs, color=TC["muted"], fontfamily=FONT, zorder=z + 1)
    else:
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=TC["txt"], fontfamily=FONT, zorder=z + 1)


def _topo_connect(ax, x0, y0, x1, y1, color, label=None, lw=1.9):
    if abs(y0 - y1) < 0.005:
        ax.annotate("", xy=(x1, y0), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=15), zorder=4)
    else:
        ax.plot([x0, x1], [y0, y0], color=color, lw=lw, zorder=4)
        ax.annotate("", xy=(x1, y1), xytext=(x1, y0),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=15), zorder=4)
    if label:
        fs = 10.5 * TOPO_FS_SCALE
        ax.text((x0 + x1) / 2, y0 + .05, label, ha="center", va="center", fontsize=fs,
                color=color, fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.93), zorder=6)


def generate_topology_diagram(graph_dir):
    fig, ax = plt.subplots(figsize=(12, 7.2))
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    fig.patch.set_facecolor(TC["bg"]); ax.set_facecolor(TC["bg"])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    _topo_rbox(ax, .01, .02, .98, .96, TC["host_fill"], TC["host_edge"], lw=1.4, rs=.020, z=1)
    ax.text(.5, .945, "Host Físico — Ubuntu 24.04 LTS", ha="center", va="center",
            fontsize=14.5 * TOPO_FS_SCALE, fontweight="bold", color=TC["host_edge"], fontfamily=FONT)

    ax.add_patch(FancyBboxPatch((.045, .075), .91, .815,
        boxstyle="round,pad=0,rounding_size=0.018",
        fc=TC["docker_fill"], ec=TC["docker_edge"], lw=1.1, linestyle=(0, (6, 4)), zorder=2))
    ax.text(.5, .852, "Red Virtual Docker  (Bridge Network)", ha="center", va="center",
            fontsize=12.5 * TOPO_FS_SCALE, color=TC["docker_edge"], fontfamily=FONT)

    _topo_rbox(ax, .275, .135, .45, .665, TC["cont_fill"], TC["cont_edge"], lw=1.4, rs=.016, z=3)
    ax.text(.50, .765, "Contenedor  (Express / FastAPI)", ha="center", va="center",
            fontsize=12.5 * TOPO_FS_SCALE, fontweight="bold", color=TC["muted"], fontfamily=FONT)

    NW, NH = .305, .16
    NX = .50 - NW / 2
    Y_ETH, Y_IFB, Y_APP = .590, .368, .170

    _topo_node(ax, NX, Y_ETH, NW, NH, "netem", "eth0", "qdisc egress · ingress mirred", fs=12.5, sfs=10, z=4)
    _topo_node(ax, NX, Y_IFB, NW, NH, "netem", "ifb0  (Ingress)", "qdisc ingress (netem)", fs=12.5, sfs=10.5, z=4)
    _topo_node(ax, NX, Y_APP, NW, NH, "app", "Proceso Aplicación", "Core 1 ó 2", fs=12.5, sfs=10.5, z=4)

    ax.annotate("", xy=(.50, Y_IFB + NH), xytext=(.50, Y_ETH),
        arrowprops=dict(arrowstyle="-|>", color=TC["netem_edge"], lw=1.7, mutation_scale=13), zorder=5)
    ax.text(.50 + .078, (Y_ETH + Y_IFB + NH) / 2, "tc filter\nmirred redirect",
            ha="center", va="center", fontsize=9.5 * TOPO_FS_SCALE, color=TC["netem_edge"], fontfamily=FONT,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.93), zorder=6)

    ax.annotate("", xy=(.50, Y_APP + NH), xytext=(.50, Y_IFB),
        arrowprops=dict(arrowstyle="-|>", color=TC["app_edge"], lw=1.7, mutation_scale=13), zorder=5)
    ax.text(.50, (Y_IFB + Y_APP + NH) / 2, "Ingress ↓", ha="center", va="center",
            fontsize=10.5 * TOPO_FS_SCALE, color=TC["app_edge"], fontfamily=FONT,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.93), zorder=6)

    RX = NX + NW + .038
    EY = Y_ETH + NH * .2
    ax.plot([NX + NW, RX], [Y_APP + NH * .5] * 2, color=TC["netem_edge"], lw=1.7, zorder=5)
    ax.plot([RX, RX], [Y_APP + NH * .5, EY], color=TC["netem_edge"], lw=1.7, zorder=5)
    ax.annotate("", xy=(NX + NW, EY), xytext=(RX, EY),
        arrowprops=dict(arrowstyle="-|>", color=TC["netem_edge"], lw=1.7, mutation_scale=13), zorder=5)
    ax.text(RX + .044, (Y_APP + NH * .5 + EY) / 2, "Egress ↑", ha="center", va="center",
            fontsize=10.5 * TOPO_FS_SCALE, color=TC["netem_edge"], fontfamily=FONT,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.93), zorder=6)

    _topo_node(ax, .068, Y_ETH, .175, NH, "load", "Inyector k6", "Cores 3, 11", fs=12.5, sfs=10.5, z=4)
    _topo_connect(ax, .068 + .175, Y_ETH + NH / 2, NX, Y_ETH + NH / 2, TC["load_edge"], "Petición HTTP")

    _topo_node(ax, .757, Y_ETH, .175, NH, "mock", "Mock I/O", "Nginx · Cores 4, 12", fs=12.5, sfs=10.5, z=4)
    _topo_connect(ax, NX + NW, Y_ETH + NH / 2, .757, Y_ETH + NH / 2, TC["mock_edge"], "fetch / httpx")

    path = os.path.join(graph_dir, "1_topologia_infraestructura.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=TC["bg"], edgecolor="none")
    plt.close(fig)
    print(f"[OK] {path}")


NC = {
    "bg":        "#F7F9FC",
    "host_bg":   "#EDF2F7", "host_bd":   "#4A5568",
    "netem_bg":  "#FFF8E1", "netem_bd":  "#D4890A",
    "app_bg":    "#E8F4FD", "app_bd":    "#3A8FC8",
    "docker_bg": "#EBF4FB", "docker_bd": "#7BAFD4",
    "txt_dark":  "#1A202C", "txt_sub":   "#4A5568",
    "ingress":   "#27AE60", "egress":    "#E74C3C",
}
NETEM_FS_SCALE = 1.48


def _rbox(ax, x, y, w, h, fc, ec, lw=1.9, rsize=0.018, zorder=3):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={rsize}",
        fc=fc, ec=ec, lw=lw, zorder=zorder
    ))


def _node(ax, x, y, w, h, fc, ec, label, sublabel=None,
          fs=10.5, sfs=8.8, lw=1.9, rsize=0.018, zorder=3):
    fs, sfs = fs * NETEM_FS_SCALE, sfs * NETEM_FS_SCALE
    _rbox(ax, x, y, w, h, fc, ec, lw=lw, rsize=rsize, zorder=zorder)
    cx, cy = x + w / 2, y + h / 2
    if sublabel:
        n_lines = sublabel.count('\n') + 1
        label_y = cy + h * (0.20 if n_lines > 1 else 0.15)
        sub_y = cy - h * (0.10 if n_lines > 1 else 0.16)
        ax.text(cx, label_y, label, ha='center', va='center',
                fontsize=fs, fontweight='bold', color=NC["txt_dark"],
                fontfamily=FONT, zorder=zorder + 1)
        ax.text(cx, sub_y, sublabel, ha='center', va='center',
                fontsize=sfs, color=NC["txt_sub"], fontfamily=FONT,
                zorder=zorder + 1, linespacing=1.5)
    else:
        ax.text(cx, cy, label, ha='center', va='center',
                fontsize=fs, fontweight='bold', color=NC["txt_dark"],
                fontfamily=FONT, zorder=zorder + 1)


def _arrow_h(ax, x0, y, x1, color, lw=3.0, zorder=5):
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                 mutation_scale=24), zorder=zorder)


def _arrow_v(ax, x, y0, y1, color, lw=2.4, zorder=5):
    ax.annotate("", xy=(x, y1), xytext=(x, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                 mutation_scale=24), zorder=zorder)


def _float_lbl(ax, x, y, text, fs=9.6, color=None, zorder=7, fw='bold'):
    fs = fs * NETEM_FS_SCALE
    ax.text(x, y, text, ha='center', va='center', fontsize=fs,
            color=color or NC["txt_dark"], fontfamily=FONT, fontweight=fw,
            bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='none',
                      alpha=0.95), zorder=zorder)


def generate_netem_diagram(graph_dir):
    fig, ax = plt.subplots(figsize=(12, 10))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.patch.set_facecolor(NC["bg"])
    ax.set_facecolor(NC["bg"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    _rbox(ax, 0.01, 0.05, 0.105, 0.91, NC["docker_bg"], NC["docker_bd"],
          lw=1.6, rsize=0.018, zorder=1)
    ax.text(0.0625, 0.50, "benchmark_net\n(Docker Bridge)",
            ha='center', va='center', rotation=90,
            fontsize=15.5 * NETEM_FS_SCALE, fontweight='bold',
            color=NC["docker_bd"], fontfamily=FONT, zorder=2,
            linespacing=1.8)

    _rbox(ax, 0.130, 0.05, 0.860, 0.91, "#FFFFFF", NC["host_bd"],
          lw=2.2, rsize=0.020, zorder=1)
    ax.text(0.560, 0.900, "Namespace de red del contenedor",
            ha='center', va='center',
            fontsize=17.5 * NETEM_FS_SCALE, fontweight='bold',
            color=NC["txt_sub"], fontfamily=FONT, zorder=2)

    NODE_W_IF, NODE_W_NE, NODE_W_APP = 0.170, 0.205, 0.245
    NODE_H = 0.225

    X_IF, X_NE, X_APP = 0.190, 0.405, 0.685
    Y_ING, Y_EGR = 0.615, 0.220

    CY_ING = Y_ING + NODE_H / 2
    CY_EGR = Y_EGR + NODE_H / 2
    Y_APP = Y_EGR - 0.03
    H_APP = (Y_ING + NODE_H) - Y_APP + 0.03

    Y_ETH_IN = CY_EGR + 0.058
    Y_ETH_OUT = CY_EGR - 0.058

    _node(ax, X_IF, Y_ING, NODE_W_IF, NODE_H, NC["host_bg"], NC["host_bd"],
          "ifb0", "Virtual\nIngress", fs=15.5, sfs=12, zorder=3)
    _node(ax, X_NE, Y_ING, NODE_W_NE, NODE_H, NC["netem_bg"], NC["netem_bd"],
          "qdisc netem\n(Ingress)", "Retardo · Pérdida\nJitter",
          fs=13.2, sfs=10.6, zorder=3)
    _node(ax, X_IF, Y_EGR, NODE_W_IF, NODE_H, NC["host_bg"], NC["host_bd"],
          "eth0", "Interfaz física\n(entrada/salida)", fs=15.5, sfs=10.8, zorder=3)
    _node(ax, X_NE, Y_EGR, NODE_W_NE, NODE_H, NC["netem_bg"], NC["netem_bd"],
          "qdisc netem\n(Egress)", "Retardo · Pérdida\nJitter",
          fs=13.2, sfs=10.6, zorder=3)
    _node(ax, X_APP, Y_APP, NODE_W_APP, H_APP, NC["app_bg"], NC["app_bd"],
          "Microservicio", "Node.js / Python\n(Express o FastAPI)",
          fs=16, sfs=12.5, zorder=3)

    X_BRIDGE_R = 0.115

    _arrow_h(ax, X_BRIDGE_R, Y_ETH_IN, X_IF, NC["ingress"])
    _float_lbl(ax, (X_BRIDGE_R + X_IF) / 2, Y_ETH_IN + 0.06, "Ingress",
               fs=12, color=NC["ingress"])

    X_REDIR = X_IF + NODE_W_IF / 2
    _arrow_v(ax, X_REDIR, Y_ETH_IN, Y_ING, NC["ingress"], lw=2.0)
    _float_lbl(ax, X_REDIR + 0.125, (Y_ETH_IN + CY_ING) / 2,
               "tc filter\nmirred redirect", fs=12.2, color=NC["ingress"],
               fw='normal')

    _arrow_h(ax, X_IF + NODE_W_IF, CY_ING, X_NE, NC["ingress"])
    X_NE_R, X_APP_L = X_NE + NODE_W_NE, X_APP
    Y_APP_IN = Y_APP + H_APP * 0.74
    ax.annotate("", xy=(X_APP_L, Y_APP_IN), xytext=(X_NE_R, CY_ING),
                arrowprops=dict(arrowstyle="-|>", color=NC["ingress"], lw=2.8,
                                 mutation_scale=22,
                                 connectionstyle="arc3,rad=-0.25"), zorder=5)
    _float_lbl(ax, (X_NE_R + X_APP_L) / 2, CY_ING + 0.115,
               "Paquetes\ndegradados", fs=10.5, color=NC["ingress"])

    Y_APP_OUT = Y_APP + H_APP * 0.26
    ax.annotate("", xy=(X_NE_R, CY_EGR), xytext=(X_APP_L, Y_APP_OUT),
                arrowprops=dict(arrowstyle="-|>", color=NC["egress"], lw=2.8,
                                 mutation_scale=22,
                                 connectionstyle="arc3,rad=-0.25"), zorder=5)
    _float_lbl(ax, (X_NE_R + X_APP_L) / 2, CY_EGR - 0.085,
               "Tráfico saliente\n(respuestas / fetch)", fs=10.5,
               color=NC["egress"])

    _arrow_h(ax, X_NE, Y_ETH_OUT, X_IF + NODE_W_IF, NC["egress"])
    _arrow_h(ax, X_IF, Y_ETH_OUT, X_BRIDGE_R, NC["egress"])
    _float_lbl(ax, (X_BRIDGE_R + X_IF) / 2, Y_ETH_OUT - 0.06, "Egress",
               fs=12, color=NC["egress"])

    legend_patches = [
        mpatches.Patch(color=NC["ingress"], label="Tráfico ingress"),
        mpatches.Patch(color=NC["egress"],  label="Tráfico egress"),
    ]
    leg = ax.legend(handles=legend_patches, loc='lower right',
                     bbox_to_anchor=(0.975, 0.065),
                     fontsize=11.5 * NETEM_FS_SCALE, framealpha=0.96,
                     edgecolor='#CBD5E0', fancybox=True,
                     borderpad=0.6, labelspacing=0.5)
    leg.set_zorder(8)

    path = os.path.join(graph_dir, "0_arquitectura_netem_simetrico.png")
    fig.savefig(path, dpi=300, bbox_inches='tight', pad_inches=0.15,
                facecolor=NC["bg"], edgecolor='none')
    plt.close(fig)
    print(f"[OK] {path}")


def generate_baseline_04(df_lat, df_gc, graph_dir):
    fig, axes = plt.subplots(1, 2, figsize=(17.5, 8.0), sharey=True, sharex=True)
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle(
        'Correlación temporal: latencia de peticiones vs. pausas del GC',
        fontsize=24, fontweight='bold', y=1.005
    )

    for i, fw in enumerate(FRAMEWORK_ORDER):
        ax = axes[i]
        ax.set_facecolor('#FAFAFA')

        lat_fw = df_lat[
            (df_lat['Framework'] == fw) &
            (df_lat['Endpoint'] == 'CPU') &
            (df_lat['Profile'] == 'high') &
            (df_lat['Scenario'] == 'A (Ideal)')
        ].copy()
        if lat_fw.empty:
            continue
        lat_fw['Time'] = pd.to_datetime(lat_fw['Time'])

        ax.scatter(lat_fw['Relative_Time'], lat_fw['Latency'],
                   color=COLORS[fw], alpha=0.30, s=16, edgecolors='none',
                   zorder=2, label='Peticiones individuales')

        y_top = lat_fw['Latency'].quantile(0.99) * 1.5

        gc_fw = df_gc[
            (df_gc['Framework'] == fw) &
            (df_gc['Endpoint'] == 'CPU') &
            (df_gc['Profile'] == 'high') &
            (df_gc['Scenario'] == 'A (Ideal)')
        ].copy()

        if not gc_fw.empty:
            gc_fw['Time'] = pd.to_datetime(gc_fw['Time'])
            gc_fw_crit = gc_fw[
                (gc_fw['Duration'] > 1.0) |
                (gc_fw['Type'].isin(['Mark/Sweep', 'Incremental', 'Weak/Phantom']))
            ].copy()

            if not gc_fw_crit.empty:
                t_min_k6 = lat_fw['Relative_Time'].min()
                t_max_k6 = lat_fw['Relative_Time'].max()

                t0_gc = gc_fw['Time'].min()
                gc_fw_crit['Relative_GC_Time'] = (gc_fw_crit['Time'] - t0_gc).dt.total_seconds()

                t_end_gc = gc_fw['Time'].max()
                t_end_k6 = lat_fw['Time'].max()
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
                    h = min(gc['Duration'] * 3, y_top) if min(gc['Duration'] * 3, y_top) > 0 else y_top * 0.5
                    ax.plot([gc['Sync_Time'], gc['Sync_Time']], [0, h],
                            color='#e74c3c', linewidth=2, alpha=0.90, zorder=3)

        ax.set_xlim(lat_fw['Relative_Time'].min() - 1, lat_fw['Relative_Time'].max() + 1)
        ax.set_ylim(bottom=0, top=y_top)

        _style_axes(
            ax, title=fw,
            xlabel='Tiempo dentro de la ventana estable de medición (s)',
            ylabel='Latencia de respuesta (ms)' if i == 0 else '',
            title_size=22
        )

        legend_handles = [
            Line2D([0], [0], marker='o', color='w', label='Peticiones individuales',
                   markerfacecolor=COLORS[fw], markersize=13, alpha=0.85),
            Line2D([0], [0], color='#e74c3c', lw=2.6,
                   label='Pausas Stop-the-World del GC'),
        ]
        ax.legend(handles=legend_handles, loc='upper center',
                  bbox_to_anchor=(0.5, -0.16), frameon=True,
                  edgecolor='#d3d3d3', ncol=2, fontsize=17.5)

    plt.tight_layout(pad=0.6, w_pad=1.0)
    fig.subplots_adjust(top=0.88, bottom=0.22, wspace=0.05)
    path = os.path.join(graph_dir, 'baseline_04_latency_gc_scatter.png')
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] {path}")


def generate_comp_01(df_high_lbl, graph_dir):
    fig, axes = plt.subplots(1, 2, figsize=(14.3, 6.6), sharey=True)
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle('Evolución del P99 de latencia por escenario (Perfil Alto)',
                 fontsize=25.5, fontweight='bold', y=0.99)

    # Handle reutilizable para la leyenda del límite SLO (fuera del gráfico)
    slo_handle = Line2D([0], [0], color='#e74c3c', linestyle=':',
                         linewidth=2.6, label='Límite de SLO (500 ms)')

    # Offsets de las etiquetas de valor: separados en vertical Y en
    # horizontal para que nunca queden uno encima del otro, incluso
    # cuando los valores son casi idénticos (857/857, 945/945, 880/881).
    label_offsets = {
        'Express': (18, 26),
        'FastAPI': (-18, -34),
    }

    for i, ep in enumerate(['CPU', 'IO']):
        ax = axes[i]
        subset = df_high_lbl[df_high_lbl['Endpoint'] == ep]

        sns.lineplot(data=subset, x='Scenario', y='Latency_P99', hue='Framework',
                     palette=COLORS, marker='o', markersize=16, linewidth=4.2,
                     ax=ax, hue_order=FRAMEWORK_ORDER, errorbar=None)

        # Línea roja de SLO, SIN texto pegado encima (el texto va en
        # la leyenda inferior, fuera del área de trazado).
        ax.axhline(500, color='#e74c3c', linestyle=':', linewidth=2.6, zorder=0)

        # Aire extra arriba/abajo para que las etiquetas de valor y las
        # de los ejes no se corten ni se monten sobre el título.
        y_min, y_max = ax.get_ylim()
        ax.set_ylim(y_min - (y_max - y_min) * 0.05, y_max * 1.14)

        grp = (subset.groupby(['Scenario', 'Framework'], observed=False)['Latency_P99']
               .mean().reset_index())

        for _, row in grp.dropna().iterrows():
            sc_idx = SCENARIO_DISPLAY_ORDER.index(row['Scenario']) if row['Scenario'] in SCENARIO_DISPLAY_ORDER else 0
            dx, dy = label_offsets[row['Framework']]
            ax.annotate(f"{row['Latency_P99']:.0f} ms", (sc_idx, row['Latency_P99']),
                        textcoords='offset points', xytext=(dx, dy),
                        ha='center', fontsize=19.0, fontweight='bold',
                        color=COLORS[row['Framework']],
                        bbox=dict(boxstyle='round,pad=0.15', fc='white',
                                  ec='none', alpha=0.8))

        _style_axes(ax, title=f'Endpoint: /{ep.lower()}', xlabel='Escenario',
                    ylabel='Latencia P99 (ms)' if i == 0 else '',
                    title_size=23.5)

        # Etiquetas de escenario simplificadas: solo A, B, C
        ax.set_xticks(range(len(SCENARIO_DISPLAY_ORDER)))
        ax.set_xticklabels(['A', 'B', 'C'])
        ax.tick_params(axis='x', labelsize=23.5, pad=10)
        ax.tick_params(axis='y', labelsize=22.5)

        if ax.get_legend() is not None:
            ax.get_legend().remove()

    # Leyenda única fuera del gráfico: frameworks + línea de SLO
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(slo_handle)
    labels.append('Límite de SLO (500 ms)')
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=True,
               edgecolor='#d3d3d3', bbox_to_anchor=(0.5, -0.04), fontsize=19.5)

    plt.tight_layout()
    fig.subplots_adjust(top=0.83, bottom=0.24, wspace=0.08)
    path = os.path.join(graph_dir, 'comp_01_latency_evolution.png')
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] {path}")


def generate_comp_04_cpu(df_high_lbl, graph_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 7.6))
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle('Consumo de CPU y RAM por escenario (/cpu, Perfil Alto)',
                 fontsize=21, fontweight='bold', y=0.99)

    subset = df_high_lbl[df_high_lbl['Endpoint'] == 'CPU']

    # --- Gráfica de CPU (axes[0]) ---
    sns.barplot(data=subset, x='Scenario', y='CPU_Mean', hue='Framework',
                palette=COLORS, ax=axes[0], order=SCENARIO_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER, errorbar=None, edgecolor='white',
                width=0.85, gap=0.05)
    for c in axes[0].containers:
        # Aquí se aumentó el fontsize a 18.5
        axes[0].bar_label(c, fmt='%.1f %%', padding=5, fontsize=18.5, fontweight='bold')
    _style_axes(axes[0], title='CPU', xlabel='Escenario',
                ylabel='Uso de CPU (%)', title_size=21.5)
    if axes[0].get_legend() is not None:
        axes[0].get_legend().remove()

    # --- Gráfica de RAM (axes[1]) ---
    sns.barplot(data=subset, x='Scenario', y='RAM_Mean', hue='Framework',
                palette=COLORS, ax=axes[1], order=SCENARIO_DISPLAY_ORDER,
                hue_order=FRAMEWORK_ORDER, errorbar=None, edgecolor='white',
                width=0.85, gap=0.05)
    for c in axes[1].containers:
        # Aquí se aumentó el fontsize a 16
        axes[1].bar_label(c, fmt='%.0f MiB', padding=5, fontsize=16, fontweight='bold')
    _style_axes(axes[1], title='RAM', xlabel='Escenario',
                ylabel='Memoria RAM (MiB)', title_size=21.5)
    if axes[1].get_legend() is not None:
        axes[1].get_legend().remove()

    for ax in axes:
        ax.set_xticks(range(len(SCENARIO_DISPLAY_ORDER)))
        ax.set_xticklabels(['A', 'B', 'C'])
        ax.tick_params(axis='x', labelsize=21, pad=10)
        ax.tick_params(axis='y', labelsize=19.5)

    y_min0, y_max0 = axes[0].get_ylim()
    axes[0].set_ylim(y_min0, y_max0 * 1.10)

    y_min1, y_max1 = axes[1].get_ylim()
    axes[1].set_ylim(y_min1, y_max1 * 1.18)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=True,
               edgecolor='#d3d3d3', bbox_to_anchor=(0.5, -0.02), fontsize=17)

    plt.tight_layout()
    fig.subplots_adjust(top=0.88, bottom=0.20)
    path = os.path.join(graph_dir, 'comp_04_resources_cpu.png')
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] {path}")


def generate_comp_05_radar_cpu(df_high_lbl, graph_dir):
    def normalize(col, higher_better=True):
        max_v, min_v = col.max(), col.min()
        if max_v == min_v:
            return pd.Series([1.0] * len(col), index=col.index)
        return (col - min_v) / (max_v - min_v) if higher_better else (max_v - col) / (max_v - min_v)

    df_radar = df_high_lbl.copy()
    m_conf = {
        'Throughput':  ('Throughput', True),
        'Latency_P99': ('Latencia\nP99 (Inv)', False),
        'Error_Rate':  ('Tasa\nerrores (Inv)', False),
        'CPU_Mean':    ('CPU\n(Inv)', False),
        'RAM_Mean':    ('RAM\n(Inv)', False),
    }
    for col, (name, better) in m_conf.items():
        df_radar[name] = normalize(df_radar[col], better)

    categories = [v[0] for v in m_conf.values()]
    N = len(categories)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    SCENARIO_LETTER = {
        'A (Línea Base)':     'A',
        'B (Red Inestable)':  'B',
        'C (Red Saturada)':   'C',
    }

    # Figura moderada: ya no necesita tanto ancho porque las etiquetas
    # están partidas en dos líneas (ocupan menos espacio horizontal)
    fig, axes = plt.subplots(1, 3, figsize=(21, 8.5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#FAFAFA')

    fig.suptitle('Radares de eficiencia /cpu por escenario (mayor área = mejor)',
                 fontsize=37.5, fontweight='bold', y=1.05)

    for i, sc_raw in enumerate(SCENARIO_ORDER):
        sc = SCENARIO_LABELS.get(sc_raw, sc_raw)
        letra = SCENARIO_LETTER.get(sc, sc)
        ax = axes[i]

        ax.set_title(letra, weight='bold', position=(0.5, 1.30), fontsize=42)

        ax.set_theta_offset(pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=29, linespacing=1.3, ha='center')
        ax.tick_params(axis='x', pad=20)

        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels([])
        ax.set_ylim(0, 1.05)
        ax.set_facecolor('#FAFAFA')

        for fw in FRAMEWORK_ORDER:
            fw_data = df_radar[
                (df_radar['Endpoint'] == 'CPU') &
                (df_radar['Scenario'] == sc) &
                (df_radar['Framework'] == fw)
            ]
            if fw_data.empty:
                continue
            values = fw_data[categories].mean().values.flatten().tolist()
            values += values[:1]
            ax.plot(angles, values, color=COLORS[fw], linewidth=2.6,
                    linestyle='solid', label=fw)
            ax.fill(angles, values, color=COLORS[fw], alpha=0.25)

    legend_handles = [Line2D([0], [0], color=COLORS[fw], lw=3, label=fw)
                       for fw in FRAMEWORK_ORDER]
    fig.legend(handles=legend_handles, loc='lower center', ncol=2,
               frameon=True, edgecolor='#d3d3d3',
               bbox_to_anchor=(0.5, -0.03), fontsize=30)

    # wspace moderado: separa lo justo, sin dejar huecos enormes
    plt.tight_layout()
    fig.subplots_adjust(top=0.70, bottom=0.12, wspace=0.5)

    path = os.path.join(graph_dir, 'comp_05_radar_cpu.png')
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] {path}")


def generate_soak_01(df_soak_res, graph_dir):
    """
    Consumo de RAM durante el soak test.
    """
    fig, ax = plt.subplots(figsize=(13, 8.0))
    fig.patch.set_facecolor('#FFFFFF')
    
    # Fuente del título aumentada a 24
    fig.suptitle('Consumo de RAM durante el soak test (60 min)',
                 fontsize=24, fontweight='bold')

    drift_offsets = {
        'FastAPI': (-70, 34),
        'Express': (-70, -48),
    }

    for fw in FRAMEWORK_ORDER:
        df_fw = df_soak_res[df_soak_res['Framework'] == fw].copy()
        if df_fw.empty:
            continue
        time_mins = df_fw['Relative_Time'] / 60.0
        df_fw['mem_smooth'] = df_fw['mem_usage'].rolling(window=15, min_periods=1).mean()
        ax.plot(time_mins, df_fw['mem_smooth'], label=f'RAM {fw}', color=COLORS[fw], lw=2.6)

        try:
            mem_start = df_fw[time_mins >= 5]['mem_smooth'].iloc[0]
            mem_end = df_fw[time_mins <= 59]['mem_smooth'].iloc[-1]
            drift = mem_end - mem_start
            sign = "+" if drift > 0 else ""
            dx, dy = drift_offsets[fw]
            ax.annotate(
                f'{fw} Drift: {sign}{drift:.1f} MiB',
                xy=(59, mem_end), xytext=(dx, dy),
                textcoords='offset points', color=COLORS[fw],
                fontweight='bold', 
                fontsize=19, # Aumentado a 19
                ha='left', va='center',
                bbox=dict(facecolor='white', alpha=0.92,
                          edgecolor=COLORS[fw], boxstyle='round,pad=0.35'),
                arrowprops=dict(arrowstyle='-', color=COLORS[fw],
                                 lw=1.1, alpha=0.7,
                                 shrinkA=0, shrinkB=4)
            )
        except Exception:
            pass

    ax.axhline(256, color='#8e44ad', linestyle='--', linewidth=2.2,
               label='Límite del contenedor (256 MiB)')
               
    # Aumentamos fuentes de ejes a 20.5
    ax.set_xlabel('Tiempo de ejecución (minutos)', fontsize=20.5)
    ax.set_ylabel('Memoria RAM asignada (MiB)', fontsize=20.5)
    
    # Aumentamos tamaño de números en los ejes a 19
    ax.tick_params(axis='both', labelsize=19)
    ax.set_ylim(bottom=0)
    
    # Aumentamos tamaño de fuente de la leyenda a 19.5 y ajustamos margen inferior
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=3,
              frameon=False, fontsize=19.5)

    plt.tight_layout()
    path = os.path.join(graph_dir, 'soak_01_ram_stability.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] {path}")


def generate_capacity_curve_express_cpu(raw_dir, graph_dir):
    ramping_dir = get_dynamic_dir(raw_dir, 'ramping')
    if not ramping_dir:
        print("[WARN] No se encontró carpeta ramping_* en raw_dir — "
              "capacity_curve_express_cpu se omite.")
        return

    raw_path = os.path.join(ramping_dir, 'raw')
    metrics_files = glob.glob(
        os.path.join(raw_path, 'express_cpu_ramping_*_metrics.json')
    )
    if not metrics_files:
        print("[WARN] No se encontró express_cpu_ramping_*_metrics.json — "
              "capacity_curve_express_cpu se omite.")
        return

    m_file = metrics_files[0]
    EMA_SPAN = 5

    data = []
    with open(m_file, 'r') as f:
        for line in f:
            if '"http_req_duration"' in line or '"http_req_failed"' in line:
                try:
                    row = json.loads(line)
                    if row.get('type') == 'Point':
                        data.append({
                            'time': pd.to_datetime(row['data']['time']),
                            'metric': row['metric'],
                            'value': row['data']['value'],
                        })
                except Exception:
                    continue

    if not data:
        print("[WARN] Sin puntos válidos en el archivo de ramping.")
        return

    df = pd.DataFrame(data).set_index('time')

    df_duration = (df[df['metric'] == 'http_req_duration']['value']
                   .resample('1s').mean().rename('Latency_Mean_ms'))
    df_p99 = (df[df['metric'] == 'http_req_duration']['value']
              .resample('1s').quantile(0.99).rename('Latency_P99_ms'))
    df_rps = (df[df['metric'] == 'http_req_duration']['value']
              .resample('1s').count().rename('Requests_Per_Second'))
    df_err = (df[df['metric'] == 'http_req_failed']['value']
              .resample('1s').sum().rename('Errors_Count'))

    merged = pd.concat([df_rps, df_duration, df_p99, df_err], axis=1).fillna(0)
    merged = merged[merged['Requests_Per_Second'] > 0].reset_index(drop=True)
    merged['Latency_P99_ms'] = (
        merged['Latency_P99_ms'].ewm(span=EMA_SPAN, adjust=False).mean()
    )

    fig, ax1 = plt.subplots(figsize=(11, 6.6))
    fig.patch.set_facecolor('#FFFFFF')
    color_lat = COLORS['Express']

    ax1.set_xlabel('Tasa de Peticiones Inyectadas (RPS)', fontsize=22)
    ax1.set_ylabel('Latencia P99 (ms)', color=color_lat, fontsize=22)
    line1 = ax1.plot(
        merged['Requests_Per_Second'], merged['Latency_P99_ms'],
        color=color_lat, marker='.', linestyle='-', linewidth=2.4,
        label='Latencia P99 (EMA)'
    )
    ax1.tick_params(axis='y', labelcolor=color_lat, labelsize=20)
    ax1.tick_params(axis='x', labelsize=20)

    line2 = ax1.axhline(
        y=500, color='gray', linestyle='--', linewidth=1.8,
        label='Límite SLO (500 ms)'
    )
    lines = [line1[0], line2]
    labels = [l.get_label() for l in lines]

    max_err_count = merged['Errors_Count'].max()
    if max_err_count > 0:
        ax2 = ax1.twinx()
        ax2.set_ylabel('Cantidad de Errores', color='#d62728', fontsize=22)
        ax2.bar(
            merged['Requests_Per_Second'], merged['Errors_Count'],
            width=1.5, color='#d62728', alpha=0.30, label='Errores'
        )
        ax2.tick_params(axis='y', labelsize=20)
        ax2.grid(False)
        h, l = ax2.get_legend_handles_labels()
        lines += h
        labels += l

    ax1.grid(axis='y', color='#e0e0e0', linewidth=0.7, linestyle='--', zorder=0)
    ax1.spines['top'].set_visible(False)

    ax1.legend(
        lines, labels, loc='upper center',
        bbox_to_anchor=(0.5, -0.20), ncol=len(labels),
        frameon=False, fontsize=20
    )
    plt.title(
        'Capacidad Máxima (Ramping Load) — Express.js /cpu',
        pad=20, fontsize=24, fontweight='bold'
    )

    plt.tight_layout()
    # Margen inferior ampliado para acomodar la fuente grande de la leyenda y el eje X
    fig.subplots_adjust(bottom=0.32, top=0.85)
    path = os.path.join(graph_dir, 'capacity_curve_express_cpu.png')
    plt.savefig(path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] {path}")


def generate_scenario_C_violin(df_latencies, graph_dir):
    df_lat_C = df_latencies[df_latencies['Scenario'] == 'C (Caos)'].copy()
    if df_lat_C.empty:
        print("[WARN] Sin datos de Escenario C en master_latencies.csv — "
              "scenario_C_01_latency_violin_log se omite.")
        return

    df_lat_C['Profile'] = df_lat_C['Profile'].map(
        lambda v: _PROFILE_LABELS_V2.get(v, v)
    )

    fig, axes = plt.subplots(1, 2, figsize=(16.5, 9.2), sharey=True)
    fig.patch.set_facecolor('#FAFAFA')
    fig.suptitle(
        'Distribución de latencias en escala logarítmica (Escenario C)',
        fontsize=25.5, fontweight='bold', y=0.98  # Aumentado 2 puntos
    )

    for i, ep in enumerate(['CPU', 'IO']):
        ax = axes[i]
        ax.set_facecolor('#FAFAFA')

        subset = df_lat_C[df_lat_C['Endpoint'] == ep].copy()
        subset['Latency'] = np.clip(subset['Latency'], 0.1, None)

        sns.violinplot(
            data=subset, x='Profile', y='Latency', hue='Framework',
            palette=COLORS, split=True, inner='quart', cut=0,
            linewidth=1.2, ax=ax,
            order=_PROFILE_DISPLAY_ORDER_V2, hue_order=FRAMEWORK_ORDER,
            legend=False
        )

        ax.axhline(500, color='#e74c3c', linestyle=':', linewidth=1.8)
        ax.axhline(100, color='#7f8c8d', linestyle='--', linewidth=1, alpha=0.5)
        ax.text(ax.get_xlim()[1], 100, '  100 ms',
                color='#7f8c8d', va='center', ha='left', fontsize=20)  # Aumentado 2 puntos

        ax.set_yscale('log')
        ax.set_ylim(top=2000) 
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f'{y:g}'))
        ax.grid(which='minor', axis='y', color='#eeeeee', linewidth=0.4, linestyle='--')

        _style_axes(
            ax, title=f'Endpoint: /{ep.lower()}', xlabel='',
            ylabel='',  # Se deja vacío para forzar el tamaño en la siguiente línea
            title_size=23  # Aumentado 1 punto
        )
        
        # Aumentamos 2 puntos al título del eje Y específicamente
        if i == 0:
            ax.set_ylabel('Latencia (ms)', fontsize=24)

        ax.tick_params(axis='both', labelsize=24.5)

    legend_elements = [
        Line2D([0], [0], color=COLORS[fw], lw=4, label=fw)
        for fw in FRAMEWORK_ORDER
    ]
    legend_elements.append(
        Line2D([0], [0], color='#e74c3c', linestyle=':', linewidth=2.6,
               label='Límite de SLO (500 ms)')
    )
    
    fig.legend(
        handles=legend_elements, loc='lower center', ncol=3,
        frameon=True, edgecolor='#d3d3d3',
        bbox_to_anchor=(0.5, 0.0), fontsize=20  # Aumentado 1 punto
    )

    plt.tight_layout()
    fig.subplots_adjust(top=0.88, bottom=0.18) 
    path = os.path.join(graph_dir, 'scenario_C_01_latency_violin_log.png')
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] {path}")


def _compute_p99_from_metrics_v2(filepath):
    durations = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                point = json.loads(line.strip())
                if (point.get("metric") == "http_req_duration"
                        and point.get("type") == "Point"):
                    durations.append(point["data"]["value"])
            except Exception:
                continue
    return float(np.percentile(durations, 99)) if durations else 0.0


def generate_estabilizacion_reps(raw_dir, graph_dir, umbral_sd=0.10):
    scen_a_dir = get_dynamic_dir(raw_dir, 'scenario_A')
    if not scen_a_dir:
        print("[WARN] No se encontró carpeta scenario_A_* en raw_dir — "
              "estabilizacion_reps_combinada se omite.")
        return

    raw_path = Path(os.path.join(scen_a_dir, 'raw'))

    def extract_fw(fw):
        files = list(raw_path.glob(f"{fw}_cpu_A_high_*_metrics.json"))
        rep_files = []
        for f in files:
            m = re.search(rf"{fw}_cpu_A_high_(\d+)_", f.name)
            if m:
                rep_files.append((int(m.group(1)), f))
        rep_files.sort(key=lambda x: x[0])
        return [_compute_p99_from_metrics_v2(f) for _, f in rep_files]

    fastapi_p99 = extract_fw("fastapi")
    express_p99 = extract_fw("express")
    if not fastapi_p99 or not express_p99:
        print("[WARN] Repeticiones insuficientes en scenario_A/raw — "
              "estabilizacion_reps_combinada se omite.")
        return

    def cum_sd(vals):
        arr = np.array(vals)
        return [np.std(arr[:i], ddof=1) for i in range(2, len(arr) + 1)]

    fastapi_sd, express_sd = cum_sd(fastapi_p99), cum_sd(express_p99)

    def detect_stable(sd_list):
        for i in range(1, len(sd_list)):
            if all(abs(sd_list[j] - sd_list[j - 1]) < umbral_sd
                   for j in range(i, len(sd_list))):
                return i + 2
        return None

    estab_fa, estab_ex = detect_stable(fastapi_sd), detect_stable(express_sd)

    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    fig.patch.set_facecolor('#FFFFFF')

    ax.plot(range(2, len(fastapi_p99) + 1), fastapi_sd, marker="s",
            color=COLORS['FastAPI'], label="FastAPI", lw=2.3)
    ax.plot(range(2, len(express_p99) + 1), express_sd, marker="o",
            color=COLORS['Express'], label="Express", lw=2.3)

    if estab_fa:
        ax.axvspan(estab_fa, len(fastapi_p99), color=COLORS['FastAPI'],
                   alpha=0.06, label=f"Estable FastAPI (N≥{estab_fa})")
        ax.axvline(x=estab_fa, color=COLORS['FastAPI'], linestyle="--")
    if estab_ex:
        ax.axvspan(estab_ex, len(express_p99), color=COLORS['Express'],
                   alpha=0.06, label=f"Estable Express (N≥{estab_ex})")
        ax.axvline(x=estab_ex, color=COLORS['Express'], linestyle="--")

    ax.set_xlabel("Número de repeticiones (N)", fontsize=18.25)
    ax.set_ylabel("Desviación Estándar Acumulada del P99 (ms)", fontsize=18.25)
    ax.set_title(
        f"Estabilización de Varianza – Endpoint /cpu (Umbral: < {umbral_sd} ms)",
        pad=14, fontweight='bold', fontsize=21.5
    )
    ax.tick_params(axis='both', labelsize=16.95)
    ax.grid(axis='y', color='#e0e0e0', linewidth=0.7, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2,
              frameon=False, fontsize=16.3)

    plt.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    path = os.path.join(graph_dir, 'estabilizacion_reps_combinada.png')
    plt.savefig(path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[OK] {path}")


def load_real_data(proc_dir, raw_dir):
    print(f"[INFO] Cargando datos reales desde: {proc_dir}")

    summary_path = os.path.join(proc_dir, 'master_summary.csv')
    latencies_path = os.path.join(proc_dir, 'master_latencies.csv')
    gc_path = os.path.join(proc_dir, 'master_gc.csv')

    for p, name in [(summary_path, 'master_summary.csv'),
                     (latencies_path, 'master_latencies.csv')]:
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"[ERROR FATAL] No se encontró {name} en {proc_dir}. "
                f"¿Corriste main.py primero (sin --skip-etl) sobre este experimento?"
            )

    df_summary = pd.read_csv(summary_path)
    df_latencies = pd.read_csv(latencies_path)
    df_latencies['Time'] = pd.to_datetime(df_latencies['Time'], format='mixed')

    df_gc = pd.DataFrame()
    if os.path.exists(gc_path):
        df_gc = pd.read_csv(gc_path)
        if not df_gc.empty:
            df_gc['Time'] = pd.to_datetime(df_gc['Time'], format='mixed')
    else:
        print("[WARN] No se encontró master_gc.csv — baseline_04 se omitirá.")

    df_high = df_summary[df_summary['Profile'].astype(str).str.lower() == 'high'].copy()
    df_high_lbl = df_high.copy()
    df_high_lbl['Scenario'] = df_high_lbl['Scenario'].map(
        lambda v: SCENARIO_LABELS.get(v, v)
    )

    df_soak_res = pd.DataFrame()
    soak_dir = get_dynamic_dir(raw_dir, 'soak')
    if soak_dir:
        soak_raw_path = os.path.join(soak_dir, 'raw')
        soak_dfs = []
        for res_file in glob.glob(os.path.join(soak_raw_path, '*_resources.csv')):
            fw = 'FastAPI' if 'fastapi' in os.path.basename(res_file).lower() else 'Express'
            df_s = parse_resources(res_file, apply_cold_start=True)
            if not df_s.empty:
                df_s['Framework'] = fw
                soak_dfs.append(df_s)
        if soak_dfs:
            df_soak_res = pd.concat(soak_dfs, ignore_index=True)
        else:
            print("[WARN] Carpeta soak encontrada pero sin *_resources.csv legibles.")
    else:
        print("[WARN] No se encontró carpeta soak_* en raw_dir — soak_01 se omitirá.")

    return df_summary, df_latencies, df_gc, df_high_lbl, df_soak_res


def main():
    parser = argparse.ArgumentParser(
        description="Regenera las 10 figuras exactas de la defensa (menos chrome, más grande) con datos reales."
    )
    parser.add_argument("--raw-dir", required=True,
                         help="Directorio raíz del experimento crudo (el mismo --raw-dir de main.py)")
    parser.add_argument("--exp-dir", required=True,
                         help="Directorio del experimento procesado (el mismo --out-dir de main.py, "
                              "debe contener processed/master_*.csv)")
    parser.add_argument("--out-dir", default=None,
                         help="Carpeta de salida para las 10 imágenes (default: <exp-dir>/graphs_v2)")
    args = parser.parse_args()

    proc_dir = os.path.join(args.exp_dir, "processed")
    out_dir = args.out_dir or os.path.join(args.exp_dir, "graphs_v2")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    print("======================================================")
    print("[INFO] Generando las 10 figuras de la defensa — DATOS REALES")
    print(f"[INFO] processed/: {proc_dir}")
    print(f"[INFO] raw/:       {args.raw_dir}")
    print(f"[INFO] salida:     {out_dir}")
    print("[INFO] (no se modifica ninguna carpeta de graphs existente)")
    print("======================================================")

    setup_theme()

    generate_topology_diagram(out_dir)
    generate_netem_diagram(out_dir)

    df_summary, df_latencies, df_gc, df_high_lbl, df_soak_res = load_real_data(
        proc_dir, args.raw_dir
    )

    if not df_gc.empty:
        generate_baseline_04(df_latencies, df_gc, out_dir)
    else:
        print("[WARN] Omitiendo baseline_04 (sin datos de GC).")

    if not df_high_lbl.empty:
        generate_comp_01(df_high_lbl, out_dir)
        generate_comp_04_cpu(df_high_lbl, out_dir)
        generate_comp_05_radar_cpu(df_high_lbl, out_dir)
    else:
        print("[WARN] Omitiendo comp_01/comp_04/comp_05 (sin datos de Perfil Alto).")

    if not df_soak_res.empty:
        generate_soak_01(df_soak_res, out_dir)
    else:
        print("[WARN] Omitiendo soak_01 (sin datos de soak test).")

    generate_capacity_curve_express_cpu(args.raw_dir, out_dir)

    if not df_latencies.empty:
        generate_scenario_C_violin(df_latencies, out_dir)

    generate_estabilizacion_reps(args.raw_dir, out_dir)

    print("------------------------------------------------------")
    print(f"[OK] Listo. Las 10 imágenes fueron generadas en: {out_dir}")
    print("------------------------------------------------------")


if __name__ == "__main__":
    main()