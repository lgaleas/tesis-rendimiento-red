#!/usr/bin/env python3
"""
Módulo para generar el diagrama de flujo de netem (ifb0 / eth0).
Autor: Leyber Galeas
"""

import os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

C = {
    "bg":       "#F7F9FC",
    "host_bg":  "#EDF2F7", "host_bd":  "#4A5568",
    "netem_bg": "#FFF8E1", "netem_bd": "#D4890A",
    "app_bg":   "#E8F4FD", "app_bd":   "#3A8FC8",
    "docker_bg":"#EBF4FB", "docker_bd":"#7BAFD4",
    "txt_dark": "#1A202C", "txt_sub":  "#4A5568",
    "note_bg":  "#FFFDE7", "note_bd":  "#F0A500",
    "note_txt": "#3E2800",
    "title":    "#1A202C", "caption":  "#4A5568",
    "ingress":  "#27AE60", "egress":   "#E74C3C",
}
FONT = "DejaVu Sans"


def rbox(ax, x, y, w, h, fc, ec, lw=1.6, rsize=0.018, zorder=3):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={rsize}",
        fc=fc, ec=ec, lw=lw, zorder=zorder
    ))


def node(ax, x, y, w, h, fc, ec, label, sublabel=None,
         fs=10.5, sfs=8.8, lw=1.6, rsize=0.018, zorder=3):
    rbox(ax, x, y, w, h, fc, ec, lw=lw, rsize=rsize, zorder=zorder)
    cx, cy = x + w / 2, y + h / 2
    if sublabel:
        ax.text(cx, cy + h * 0.16, label,
                ha='center', va='center',
                fontsize=fs, fontweight='bold',
                color=C["txt_dark"], fontfamily=FONT, zorder=zorder + 1)
        ax.text(cx, cy - h * 0.20, sublabel,
                ha='center', va='center',
                fontsize=sfs, color=C["txt_sub"],
                fontfamily=FONT, zorder=zorder + 1)
    else:
        ax.text(cx, cy, label,
                ha='center', va='center',
                fontsize=fs, fontweight='bold',
                color=C["txt_dark"], fontfamily=FONT, zorder=zorder + 1)


def arrow_h(ax, x0, y, x1, color, lw=2.2, zorder=5):
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(
                    arrowstyle="-|>", color=color,
                    lw=lw, mutation_scale=16
                ), zorder=zorder)


def arrow_v(ax, x, y0, y1, color, lw=2.2, zorder=5):
    ax.annotate("", xy=(x, y1), xytext=(x, y0),
                arrowprops=dict(
                    arrowstyle="-|>", color=color,
                    lw=lw, mutation_scale=16
                ), zorder=zorder)


def float_lbl(ax, x, y, text, fs=9.0, color=None, zorder=7, fw='bold'):
    ax.text(x, y, text,
            ha='center', va='center',
            fontsize=fs, color=color or C["txt_dark"],
            fontfamily=FONT, fontweight=fw,
            bbox=dict(boxstyle='round,pad=0.35',
                      fc='white', ec='none', alpha=0.93),
            zorder=zorder)


def generate_netem_flow_diagram(graph_dir):
    fig, ax = plt.subplots(figsize=(14, 8.5))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.91, bottom=0.09)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Contenedor Docker Bridge (franja izquierda) ──────────────────────────
    rbox(ax, 0.01, 0.10, 0.11, 0.80,
         C["docker_bg"], C["docker_bd"], lw=1.4, rsize=0.018, zorder=1)
    ax.text(0.065, 0.50,
            "benchmark_net\n(Docker Bridge)",
            ha='center', va='center', rotation=90,
            fontsize=11, fontweight='bold',
            color=C["docker_bd"], fontfamily=FONT, zorder=2)

    # ── Contenedor Principal (namespace de red) ──────────────────────────────
    rbox(ax, 0.13, 0.10, 0.85, 0.80,
         "#FFFFFF", C["host_bd"], lw=2.0, rsize=0.020, zorder=1)
    ax.text(0.555, 0.865,
            "Espacio de nombres de red del contenedor",
            ha='center', va='center',
            fontsize=12, fontweight='bold',
            color=C["txt_sub"], fontfamily=FONT, zorder=2)

    # ─────────────────────────────────────────────────────────────────────────
    # POSICIONES base
    # Columna A: eth0 / ifb0      x=0.18,  w=0.14
    # Columna B: netem             x=0.38,  w=0.19
    # Columna C: microservicio     x=0.66,  w=0.22
    # Filas:  ingress y=0.58 h=0.17 |  egress y=0.28 h=0.17
    # ─────────────────────────────────────────────────────────────────────────

    NODE_W_IF  = 0.13
    NODE_W_NE  = 0.19
    NODE_W_APP = 0.22
    NODE_H     = 0.17

    X_IF  = 0.175
    X_NE  = 0.365
    X_APP = 0.660
    Y_ING = 0.580   # fila ingress (arriba)
    Y_EGR = 0.270   # fila egress  (abajo)

    # Centro vertical de cada fila
    CY_ING = Y_ING + NODE_H / 2
    CY_EGR = Y_EGR + NODE_H / 2

    # App ocupa ambas filas verticalmente
    Y_APP = Y_EGR - 0.03
    H_APP = (Y_ING + NODE_H) - Y_APP + 0.03

    # ── Nodos ────────────────────────────────────────────────────────────────
    # Fila Ingress
    node(ax, X_IF, Y_ING, NODE_W_IF, NODE_H,
         C["host_bg"], C["host_bd"],
         "ifb0", "Virtual Ingress", zorder=3)

    node(ax, X_NE, Y_ING, NODE_W_NE, NODE_H,
         C["netem_bg"], C["netem_bd"],
         "qdisc netem  (Ingress)", "Retardo · Pérdida · Jitter",
         fs=10, sfs=8.5, zorder=3)

    # Fila Egress
    node(ax, X_IF, Y_EGR, NODE_W_IF, NODE_H,
         C["host_bg"], C["host_bd"],
         "eth0", "Interfaz física", zorder=3)

    node(ax, X_NE, Y_EGR, NODE_W_NE, NODE_H,
         C["netem_bg"], C["netem_bd"],
         "qdisc netem  (Egress)", "Retardo · Pérdida · Jitter",
         fs=10, sfs=8.5, zorder=3)

    # Microservicio (centro derecho, abarca ambas filas)
    node(ax, X_APP, Y_APP, NODE_W_APP, H_APP,
         C["app_bg"], C["app_bd"],
         "Microservicio",
         "Node.js / Python\n(Express o FastAPI)",
         fs=11.5, sfs=9.5, zorder=3)

    # ─────────────────────────────────────────────────────────────────────────
    # FLECHAS – centradas en la mitad vertical de cada nodo
    # ─────────────────────────────────────────────────────────────────────────

    # Borde derecho del bridge → borde izquierdo de eth0/ifb0
    X_BRIDGE_R = 0.12

    # ── INGRESS (verde) ──────────────────────────────────────────────────────
    # 1. Bridge → ifb0  (directo, mismo Y)
    arrow_h(ax, X_BRIDGE_R, CY_ING, X_IF, C["ingress"])
    float_lbl(ax, (X_BRIDGE_R + X_IF) / 2, CY_ING + 0.055,
              "Ingress", fs=8.8, color=C["ingress"])

    # 2. ifb0 → netem ingress
    arrow_h(ax, X_IF + NODE_W_IF, CY_ING, X_NE, C["ingress"])

    # 3. netem ingress → microservicio (entrada superior del app)
    X_NE_R  = X_NE + NODE_W_NE
    X_APP_L = X_APP
    Y_APP_IN = Y_APP + H_APP * 0.72   # entrada superior del microservicio
    ax.annotate("",
                xy=(X_APP_L, Y_APP_IN), xytext=(X_NE_R, CY_ING),
                arrowprops=dict(
                    arrowstyle="-|>", color=C["ingress"],
                    lw=2.2, mutation_scale=16,
                    connectionstyle="arc3,rad=-0.20"
                ), zorder=5)
    float_lbl(ax, (X_NE_R + X_APP_L) / 2 + 0.012, CY_ING - 0.065,
              "Paquetes\ndegradados", fs=8.5, color=C["ingress"])

    # ── Redirección interna ifb0 ← eth0  (flecha vertical entre filas) ──────
    X_REDIR = X_IF + NODE_W_IF / 2
    arrow_v(ax, X_REDIR, Y_EGR + NODE_H, Y_ING, C["ingress"], lw=1.8)
    float_lbl(ax, X_REDIR + 0.07, (CY_EGR + CY_ING) / 2,
              "tc filter\nmirred redirect", fs=8.2,
              color=C["ingress"], fw='normal')

    # ── EGRESS (rojo) ────────────────────────────────────────────────────────
    # 4. Microservicio → netem egress (salida inferior del app)
    Y_APP_OUT = Y_APP + H_APP * 0.28  # salida inferior del microservicio
    ax.annotate("",
                xy=(X_NE_R, CY_EGR), xytext=(X_APP_L, Y_APP_OUT),
                arrowprops=dict(
                    arrowstyle="-|>", color=C["egress"],
                    lw=2.2, mutation_scale=16,
                    connectionstyle="arc3,rad=-0.20"
                ), zorder=5)
    float_lbl(ax, (X_NE_R + X_APP_L) / 2 + 0.012, CY_EGR + 0.065,
              "Tráfico saliente\n(respuestas / fetch)", fs=8.5,
              color=C["egress"])

    # 5. netem egress → eth0
    arrow_h(ax, X_NE, CY_EGR, X_IF + NODE_W_IF, C["egress"])

    # 6. eth0 → Bridge
    arrow_h(ax, X_IF, CY_EGR, X_BRIDGE_R, C["egress"])
    float_lbl(ax, (X_BRIDGE_R + X_IF) / 2, CY_EGR - 0.055,
              "Egress", fs=8.8, color=C["egress"])

    # ── NOTA EXPLICATIVA ──────────────────────────────────────────────────────
    nota = (
        "Tanto el tráfico entrante (ingress) como el saliente (egress) "
        "son encolados por qdisc netem,\n"
        "logrando que ambas direcciones experimenten las mismas condiciones "
        "de red configuradas (retardo, pérdida, jitter)."
    )
    rbox(ax, 0.14, 0.135, 0.83, 0.095,
         C["note_bg"], C["note_bd"], lw=1.2, rsize=0.012, zorder=4)
    ax.text(0.555, 0.183, nota,
            ha='center', va='center',
            fontsize=9.2, color=C["note_txt"],
            fontfamily=FONT, zorder=5)

    # ── TÍTULO Y PIE ──────────────────────────────────────────────────────────
    fig.text(0.50, 0.965,
             "Intercepción de Tráfico con Netem + IFB",
             ha='center', va='top',
             fontsize=15, fontweight='bold',
             color=C["title"], fontfamily=FONT)

    caption = ("tc qdisc netem  ·  "
               "Intermediate Functional Block (ifb0)  ·  "
               "Degradación bidireccional de red")
    fig.text(0.50, 0.025, caption,
             ha='center', va='bottom',
             fontsize=9, color=C["caption"],
             fontfamily=FONT, style='italic',
             bbox=dict(boxstyle='round,pad=0.45',
                       fc='#F0F4F8', ec='#CBD5E0', alpha=0.95))

    # ── LEYENDA ───────────────────────────────────────────────────────────────
    legend_patches = [
        mpatches.Patch(color=C["ingress"], label="Tráfico ingress"),
        mpatches.Patch(color=C["egress"],  label="Tráfico egress"),
    ]
    ax.legend(handles=legend_patches,
              loc='lower right', bbox_to_anchor=(0.99, 0.01),
              fontsize=9, framealpha=0.9,
              edgecolor='#CBD5E0', fancybox=True)

    # ── GUARDAR ───────────────────────────────────────────────────────────────
    os.makedirs(graph_dir, exist_ok=True)
    path = os.path.join(graph_dir, "0_arquitectura_netem_simetrico.png")
    fig.savefig(path, dpi=300, bbox_inches='tight',
                facecolor=C["bg"], edgecolor='none')
    plt.close(fig)
    print(f"[OK] Diagrama generado: {path}")

def generate_diagrams(graph_dir="./graphs"):
    os.makedirs(graph_dir, exist_ok=True)
    generate_netem_flow_diagram()

if __name__ == "__main__":
    generate_diagrams(sys.argv[1] if len(sys.argv) > 1 else "./graphs")