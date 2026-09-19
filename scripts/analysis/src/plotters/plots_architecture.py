import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FONT = "DejaVu Sans"

C = {
    "bg":          "#F7F9FC",
    "host_fill":   "#F0F4F8",  "host_edge":   "#4A5568",
    "docker_fill": "#EBF4FB",  "docker_edge": "#7BAFD4",
    "cont_fill":   "#FFFFFF",  "cont_edge":   "#A0AEC0",
    "netem_fill":  "#FFF8E1",  "netem_edge":  "#D4890A",
    "app_fill":    "#E8F4FD",  "app_edge":    "#3A8FC8",
    "mock_fill":   "#E8F8F0",  "mock_edge":   "#2D9E6B",
    "load_fill":   "#EAECEE",  "load_edge":   "#6C7A89",
    "txt":         "#1A202C",  "muted":       "#4A5568",
    "note_fill":   "#FFFDE7",  "note_edge":   "#F0A500",
    "note_txt":    "#3E2800",
    "lifeline":    "#CBD5E0",  "step":        "#9AA5B4",
    "caption":     "#4A5568",
}

NS = {
    "netem": (C["netem_fill"], C["netem_edge"]),
    "app":   (C["app_fill"],   C["app_edge"]),
    "mock":  (C["mock_fill"],  C["mock_edge"]),
    "load":  (C["load_fill"],  C["load_edge"]),
}

# ── Primitives ────────────────────────────────────────────────────────────────

def rbox(ax, x, y, w, h, fc, ec, lw=1.8, rs=0.015, z=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={rs}",
        fc=fc, ec=ec, lw=lw, zorder=z))

def arrow(ax, x0, x1, y, color, lw=1.9, z=4):
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=14),
        zorder=z)

def save(fig, path):
    fig.savefig(path, dpi=180, bbox_inches="tight",
                facecolor=C["bg"], edgecolor="none")
    plt.close(fig)
    print(f"[OK] {path}")

def caption_bar(fig, lines, fs=12):
    fig.text(0.5, 0.005, "  ·  ".join(lines),
        ha="center", va="bottom", fontsize=fs, color=C["caption"],
        fontfamily=FONT, style="italic",
        bbox=dict(boxstyle="round,pad=0.35", fc="#F0F4F8", ec="#CBD5E0", alpha=0.95))

# ── Diagram 1: Topology ───────────────────────────────────────────────────────

def _node(ax, x, y, w, h, sk, label, sub=None, fs=13, sfs=11, lw=2, rs=0.012, z=3):
    fc, ec = NS[sk] if isinstance(sk, str) else sk
    rbox(ax, x, y, w, h, fc, ec, lw=lw, rs=rs, z=z)
    cx, cy = x + w/2, y + h/2
    if sub:
        ax.text(cx, cy + h*.15, label, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=C["txt"], fontfamily=FONT, zorder=z+1)
        ax.text(cx, cy - h*.22, sub, ha="center", va="center",
                fontsize=sfs, color=C["muted"], fontfamily=FONT, zorder=z+1)
    else:
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=C["txt"], fontfamily=FONT, zorder=z+1)

def _connect(ax, x0, y0, x1, y1, color, label=None, lw=1.7):
    if abs(y0 - y1) < 0.005:
        ax.annotate("", xy=(x1, y0), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=13), zorder=4)
    else:
        ax.plot([x0, x1], [y0, y0], color=color, lw=lw, zorder=4)
        ax.annotate("", xy=(x1, y1), xytext=(x1, y0),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=13), zorder=4)
    if label:
        ax.text((x0+x1)/2, y0+.045, label, ha="center", va="center", fontsize=10,
                color=color, fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.92), zorder=6)

def diagrama_topologia(out):
    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.subplots_adjust(left=.01, right=.99, top=.98, bottom=.08)
    fig.patch.set_facecolor(C["bg"]); ax.set_facecolor(C["bg"])
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")

    rbox(ax,.01,.06,.98,.86, C["host_fill"],C["host_edge"], lw=1.4, rs=.025, z=1)
    ax.text(.5,.953,"Host Físico — Ubuntu 24.04 LTS", ha="center", va="center",
            fontsize=13, fontweight="bold", color=C["host_edge"], fontfamily=FONT)
    ax.add_patch(FancyBboxPatch((.05,.12),.89,.73,
        boxstyle="round,pad=0,rounding_size=0.02",
        fc=C["docker_fill"], ec=C["docker_edge"], lw=1.1, linestyle=(0,(6,4)), zorder=2))
    ax.text(.5,.868,"Red Virtual Docker  (Bridge Network)", ha="center", va="center",
            fontsize=12, color=C["docker_edge"], fontfamily=FONT)
    rbox(ax,.28,.17,.44,.63, C["cont_fill"],C["cont_edge"], lw=1.4, rs=.018, z=3)
    ax.text(.50,.825,"Contenedor  (Express / FastAPI)", ha="center", va="center",
            fontsize=12, fontweight="bold", color=C["muted"], fontfamily=FONT)

    NW, NH = .30, .14;  NX = .50 - NW/2
    Y_ETH, Y_IFB, Y_APP = .615, .415, .210
    _node(ax, NX, Y_ETH, NW, NH, "netem", "eth0  (Egress)",     "qdisc egress",                    fs=13, sfs=11, z=4)
    _node(ax, NX, Y_IFB, NW, NH, "netem", "ifb0  (Ingress)",    "qdisc ingress · tc filter mirred", fs=13, sfs=11, z=4)
    _node(ax, NX, Y_APP, NW, NH, "app",   "Proceso Aplicación", "Core 1 ó 2",                      fs=13, sfs=11, z=4)

    ax.annotate("", xy=(.50, Y_APP+NH), xytext=(.50, Y_IFB),
        arrowprops=dict(arrowstyle="-|>", color=C["app_edge"], lw=1.6, mutation_scale=12), zorder=5)
    ax.text(.50, (Y_IFB+Y_APP+NH)/2, "Ingress ↓", ha="center", va="center", fontsize=10,
            color=C["app_edge"], fontfamily=FONT,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.92), zorder=6)

    RX = NX+NW+.038;  EY = Y_ETH+NH*.2
    ax.plot([NX+NW, RX], [Y_APP+NH*.5]*2, color=C["netem_edge"], lw=1.6, zorder=5)
    ax.plot([RX, RX], [Y_APP+NH*.5, EY],  color=C["netem_edge"], lw=1.6, zorder=5)
    ax.annotate("", xy=(NX+NW, EY), xytext=(RX, EY),
        arrowprops=dict(arrowstyle="-|>", color=C["netem_edge"], lw=1.6, mutation_scale=12), zorder=5)
    ax.text(RX+.042, (Y_APP+NH*.5+EY)/2, "Egress ↑", ha="center", va="center", fontsize=10,
            color=C["netem_edge"], fontfamily=FONT,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.92), zorder=6)

    _node(ax,.063, Y_IFB,.178, NH,"load","Inyector k6",  "Cores 3, 11",         fs=13, sfs=11, z=4)
    _node(ax,.759, Y_ETH,.178, NH,"mock","Mock I/O",     "Nginx · Cores 4, 12", fs=13, sfs=11, z=4)
    _connect(ax,.063+.178,.415+NH/2, NX,.415+NH/2,    C["load_edge"], "Petición HTTP")
    _connect(ax,NX+NW,.615+NH/2, .759,.615+NH/2,      C["mock_edge"], "fetch / httpx")

    caption_bar(fig,["Contenedor intercepta tráfico con tc/netem en eth0 (egress) e ifb0 (ingress)",
                     "k6 inyecta carga  ·  Nginx actúa como mock de I/O"])
    save(fig, os.path.join(out, "1_topologia_infraestructura.png"))

# ── Sequence diagram engine ───────────────────────────────────────────────────

def seq_diagram(filename, actors, messages, captions, out, *,
                fig_w=13, box_h=0.84, row_h=1.15, note_h=0.66, note_gap=0.22,
                pad_top=0.55, pad_bot=0.75,
                fs_actor=15, fs_sub=12, fs_lbl=13, fs_note=12, fs_step=12, fs_cap=12):

    n = len(actors)

    # ── Box sizing: fixed width, then derive column step ──────────────────────
    # We want: EDGE_PAD + bw/2  to be the x of first/last actor center.
    # So: xs[0] = EDGE_PAD + bw/2, xs[n-1] = fig_w - EDGE_PAD - bw/2
    # This guarantees actor boxes never clip canvas edges.
    EDGE_PAD = fig_w * 0.025          # hard margin from canvas edge to box edge
    bw       = min((fig_w - 2*EDGE_PAD) / (n + 0.6), 2.20)   # box width
    nw       = bw * 1.10                                       # note width

    first_x  = EDGE_PAD + bw / 2     # center of first actor
    last_x   = fig_w - EDGE_PAD - bw / 2
    col_step = (last_x - first_x) / (n - 1) if n > 1 else 0
    xs       = [first_x + i * col_step for i in range(n)]

    # left margin for step numbers (just inside the leftmost box left edge)
    step_x = EDGE_PAD * 0.55

    # ── Figure height ─────────────────────────────────────────────────────────
    content_h = sum(row_h + (note_h + note_gap if "note" in m else 0) for m in messages)
    fig_h = pad_top + box_h + content_h + pad_bot

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.patch.set_facecolor(C["bg"]); ax.set_facecolor(C["bg"])
    ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h); ax.axis("off")

    actor_top = fig_h - pad_top
    actor_bot = actor_top - box_h
    ll_bot    = pad_bot * 0.30

    # ── Lifelines ─────────────────────────────────────────────────────────────
    for x in xs:
        ax.plot([x, x], [actor_bot, ll_bot], color=C["lifeline"],
                lw=1.2, linestyle=(0,(5,4)), zorder=1)

    # ── Actor boxes  (anchored by left edge = x - bw/2) ──────────────────────
    for i, (name, bg, ec) in enumerate(actors):
        x = xs[i];  bx = x - bw/2;  by = actor_bot
        rbox(ax, bx, by, bw, box_h, bg, ec, lw=2.0, rs=0.10, z=5)
        lines = name.split("\n")
        if len(lines) == 1:
            ax.text(x, by + box_h/2, lines[0], ha="center", va="center",
                    fontsize=fs_actor, fontweight="bold", color=C["txt"], fontfamily=FONT, zorder=6)
        else:
            ax.text(x, by + box_h*.65, lines[0], ha="center", va="center",
                    fontsize=fs_actor, fontweight="bold", color=C["txt"], fontfamily=FONT, zorder=6)
            ax.text(x, by + box_h*.28, lines[1], ha="center", va="center",
                    fontsize=fs_sub, color=C["muted"], fontfamily=FONT, zorder=6)

    # ── Messages ──────────────────────────────────────────────────────────────
    cy = actor_bot - row_h * 0.52

    for idx, msg in enumerate(messages):
        x0, x1   = xs[msg["from"]], xs[msg["to"]]
        col      = actors[msg["from"]][2]
        has_note = "note" in msg

        # step number
        ax.text(step_x, cy + 0.10, str(idx+1),
                fontsize=fs_step, color=C["step"], fontfamily=FONT,
                ha="center", va="center", fontweight="bold", zorder=6)

        # arrow
        arrow(ax, x0, x1, cy, col)

        # label above arrow
        ax.text((x0+x1)/2, cy + 0.14, msg["label"],
                ha="center", va="bottom", fontsize=fs_lbl,
                color=C["txt"], fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.20", fc="white", ec="none", alpha=0.93),
                zorder=5)

        # note box below this row
        if has_note:
            na  = msg.get("note_actor", msg["from"])
            nx  = xs[na];  nbx = nx - nw/2
            nby = cy - note_gap - note_h
            rbox(ax, nbx, nby, nw, note_h, C["note_fill"], C["note_edge"], lw=1.3, rs=0.10, z=4)
            nlines = msg["note"].split("\n")
            for li, ln in enumerate(nlines):
                yt = nby + note_h * (1 - (li+.5)/len(nlines))
                ax.text(nx, yt, ln, ha="center", va="center",
                        fontsize=fs_note, color=C["note_txt"], fontfamily=FONT, zorder=5)

        cy -= row_h + (note_h + note_gap if has_note else 0)

    caption_bar(fig, captions, fs=fs_cap)
    save(fig, os.path.join(out, f"{filename}.png"))

# ── Diagram 2: CPU ────────────────────────────────────────────────────────────

def diagrama_cpu(out):
    actors = [
        ("Inyector k6",                C["load_fill"],  C["load_edge"]),
        ("ifb0\n(Ingress)",            C["netem_fill"], C["netem_edge"]),
        ("eth0\n(Egress)",             C["netem_fill"], C["netem_edge"]),
        ("Framework\nExpress/FastAPI", C["app_fill"],   C["app_edge"]),
    ]
    messages = [
        {"from":0,"to":1,"label":"HTTP GET /cpu",
         "note":"Aplica retardo / pérdida\n(tráfico ingress)","note_actor":1},
        {"from":1,"to":3,"label":"Petición recibida",
         "note":"Bucle sincrónico\n8 000 iter. SHA-256","note_actor":3},
        {"from":3,"to":2,"label":"HTTP 200 OK",
         "note":"Aplica retardo / pérdida\n(tráfico egress)","note_actor":2},
        {"from":2,"to":0,"label":"Transacción finalizada"},
    ]
    seq_diagram("2_flujo_secuencia_cpu", actors, messages,
        ["k6 envía GET /cpu  ·  ifb0 degrada ingreso  ·  8 000 iter. SHA-256",
         "respuesta vía eth0 (egress degradado)"],
        out, fig_w=13, box_h=0.84, row_h=1.15, note_h=0.66, note_gap=0.22,
        pad_top=0.58, pad_bot=0.75,
        fs_actor=15, fs_sub=12, fs_lbl=13, fs_note=12, fs_step=12, fs_cap=12)

# ── Diagram 3: I/O ────────────────────────────────────────────────────────────

def diagrama_io(out):
    actors = [
        ("Inyector k6",                C["load_fill"],  C["load_edge"]),
        ("ifb0\n(Ingress)",            C["netem_fill"], C["netem_edge"]),
        ("eth0\n(Egress)",             C["netem_fill"], C["netem_edge"]),
        ("Framework\nExpress/FastAPI", C["app_fill"],   C["app_edge"]),
        ("Mock I/O\nNginx",            C["mock_fill"],  C["mock_edge"]),
    ]
    messages = [
        {"from":0,"to":1,"label":"HTTP GET /io",
         "note":"① Degr. Ingress\n(petición de k6)","note_actor":1},
        {"from":1,"to":3,"label":"Petición recibida"},
        {"from":3,"to":2,"label":"GET http://mock_io:80/",
         "note":"② Degr. Egress\n(salida al mock)","note_actor":2},
        {"from":2,"to":4,"label":"Petición de red real"},
        {"from":4,"to":1,"label":"HTTP 200 OK  (Mock)",
         "note":"③ Degr. Ingress\n(respuesta del mock)","note_actor":1},
        {"from":1,"to":3,"label":"Resolución asíncrona",
         "note":"Liberación socket TCP\ny destrucción de vars.","note_actor":3},
        {"from":3,"to":2,"label":"HTTP 200 OK  (Final)",
         "note":"④ Degr. Egress\n(salida a k6)","note_actor":2},
        {"from":2,"to":0,"label":"Transacción finalizada"},
    ]
    seq_diagram("3_flujo_secuencia_io", actors, messages,
        ["4 puntos de degradación: ① ingress k6→fw  ② egress fw→mock  ③ ingress mock→fw  ④ egress fw→k6",
         "Framework resuelve la llamada al mock de forma asíncrona (fetch / httpx)"],
        out, fig_w=16, box_h=0.92, row_h=1.28, note_h=0.74, note_gap=0.25,
        pad_top=0.62, pad_bot=0.85,
        fs_actor=17, fs_sub=14, fs_lbl=15, fs_note=14, fs_step=14, fs_cap=14)

# ── Entry point ───────────────────────────────────────────────────────────────

def generate_diagrams(graph_dir="./graphs"):
    os.makedirs(graph_dir, exist_ok=True)
    diagrama_topologia(graph_dir)
    diagrama_cpu(graph_dir)
    diagrama_io(graph_dir)

if __name__ == "__main__":
    generate_diagrams(sys.argv[1] if len(sys.argv) > 1 else "./graphs")