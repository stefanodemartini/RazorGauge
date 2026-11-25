import re, math, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from matplotlib.transforms import Affine2D

pcb, out = sys.argv[1], sys.argv[2]
s = open(pcb, encoding="utf-8").read()

def block(i):
    d = 0; k = i
    while True:
        c = s[k]
        if c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return s[i:k + 1]
        k += 1

# footprints
fps = []
for m in re.finditer(r"\(footprint ", s):
    b = block(m.start())
    at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", b)
    x, y, r = float(at[1]), float(at[2]), float(at[3] or 0)
    ref = re.search(r'\(fp_text reference "([^"]+)"', b) or re.search(r'\(property "Reference" "([^"]+)"', b)
    pads = []
    for pm in re.finditer(r'\(pad "(\d*)" (\w+) (\w+) \(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\) \(size ([-\d.]+) ([-\d.]+)\)', b):
        px, py = float(pm[4]), float(pm[5]); pr = float(pm[6] or r)
        a = math.radians(r)
        gx = x + px * math.cos(a) + py * math.sin(a)
        gy = y - px * math.sin(a) + py * math.cos(a)
        net = re.search(r'\(net \d+ "([^"]*)"\)', b[pm.start():pm.start() + 600])
        pads.append(dict(n=pm[1], kind=pm[2], shape=pm[3], x=gx, y=gy, rot=pr,
                         w=float(pm[7]), h=float(pm[8]), net=net[1] if net else ""))
    fps.append(dict(ref=ref[1] if ref else "?", x=x, y=y, r=r, pads=pads))
byref = {f["ref"]: f for f in fps}
segs = [(float(a), float(b), float(c), float(d), float(w), l) for a, b, c, d, w, l in
        re.findall(r'\(segment \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\) \(width ([-\d.]+)\) \(layer "([^"]+)"\)', s)]

def pad_of(ref, n):
    return next(p for p in byref[ref]["pads"] if p["n"] == n)

def draw_board(ax, title, variant, pinlab=False):
    ax.set_facecolor("white")
    ax.add_patch(Rectangle((0, 0), 24, 18, fc="#1b1b1b", ec="#888", lw=1.5, zorder=0))
    for x1, y1, x2, y2, w, l in segs:
        if l == "F.Cu":
            ax.plot([x1, x2], [y1, y2], color="#5a4a1a", lw=w * 9, solid_capstyle="round", zorder=1)
    for f in fps:
        for p in f["pads"]:
            col = "#d4af37"
            if f["ref"] == "U2":
                if variant == "bypass": col = "#d4af37"
            if p["kind"] == "np_thru_hole":
                ax.add_patch(Circle((p["x"], p["y"]), p["w"] / 2, fc="white", ec="#999", zorder=2)); continue
            if p["kind"] == "thru_hole":
                ax.add_patch(Circle((p["x"], p["y"]), p["w"] / 2, fc=col, ec="none", zorder=2))
                ax.add_patch(Circle((p["x"], p["y"]), 0.4, fc="#1b1b1b", zorder=3)); continue
            rect = Rectangle((p["x"] - p["w"] / 2, p["y"] - p["h"] / 2), p["w"], p["h"], fc=col, ec="none", zorder=2)
            rect.set_transform(Affine2D().rotate_deg_around(p["x"], p["y"], -p["rot"]) + ax.transData)
            ax.add_patch(rect)
        # corpo componente (contorno tratteggiato) + riferimento
        if f["ref"] in ("U1",):
            ax.add_patch(Rectangle((f["x"] - 4.7, f["y"] - 1.5 + 0.305 * (1 if f["r"] == 180 else -1)), 9.4, 3.0,
                                   fc="none", ec="#cfcfcf", lw=1, ls="--", zorder=4))
        if f["ref"] != "J1" and f["ref"] != "?":
            xs = [p["x"] for p in f["pads"]] or [f["x"]]; ys = [p["y"] for p in f["pads"]] or [f["y"]]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            if f["ref"] == "U1": cy += 1.05
            if f["ref"].startswith("H"): continue
            ax.text(cx, cy, f["ref"], color="white", fontsize=7.5, ha="center", va="center", zorder=6,
                    fontweight="bold", alpha=0.9, clip_on=True)
    # etichette piazzole J1
    for p in byref["J1"]["pads"]:
        lab = {"1": "3V3", "2": "GND", "3": "SI", "4": "CLK", "5": "AO"}[p["n"]]
        ax.text(p["x"] - 1.2, p["y"], lab, color="#ddd", fontsize=6.5, ha="right", va="center", zorder=6, clip_on=True)

    u2 = byref["U2"]
    if variant == "bypass":
        # U2 tolto: croce rossa sul corpo
        x0 = min(p["x"] for p in u2["pads"]) - 0.6; x1 = max(p["x"] for p in u2["pads"]) + 0.6
        y0 = min(p["y"] for p in u2["pads"]) - 0.7; y1 = max(p["y"] for p in u2["pads"]) + 0.7
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="#ff3b30", lw=2.2, zorder=7))
        ax.plot([x0, x1], [y0, y1], color="#ff3b30", lw=2.2, zorder=7)
        ax.plot([x0, x1], [y1, y0], color="#ff3b30", lw=2.2, zorder=7)
        a = pad_of("R4", "1"); b = pad_of("U2", "1")
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color="#00e5ff", lw=4.5, solid_capstyle="round", zorder=8)
        for p in (a, b):
            ax.add_patch(Circle((p["x"], p["y"]), 0.42, fc="#00e5ff", ec="white", lw=1, zorder=9))
    else:
        # nuovo chip: corpo + pallino del pin 1
        p1 = pad_of("U2", "1")
        xs = [p["x"] for p in u2["pads"]]; ys = [p["y"] for p in u2["pads"]]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        ax.add_patch(Rectangle((cx - 1.45, cy - 0.8), 2.9, 1.6, fc="#2a2a2a", ec="#34c759", lw=2.2, zorder=7))
        ax.add_patch(Circle((p1["x"] + 0.15, cy + 0.42), 0.2, fc="white", zorder=8))
        if pinlab: ax.text(cx, cy - 0.25, "MCP6001", color="#34c759", fontsize=6.5, ha="center", va="center", zorder=8, fontweight="bold")
        names = {"1": "OUT", "2": "V−", "3": "IN+", "4": "IN−", "5": "V+"}
        for p in (u2["pads"] if pinlab else []):
            dy = 0.95 if p["y"] > cy else -0.95
            ax.text(p["x"], p["y"] + dy, f'{p["n"]} {names[p["n"]]}', color="#34c759", fontsize=8, clip_on=True,
                    ha="center", va="center", zorder=8, fontweight="bold",
                    bbox=dict(fc="#1b1b1b", ec="none", pad=0.4, alpha=0.85))
    ax.set_xlim(-0.6, 24.6); ax.set_ylim(18.6, -0.6); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")


fig = plt.figure(figsize=(16, 11), dpi=160)
gs = fig.add_gridspec(2, 3, width_ratios=[1.25, 1.0, 1.05], hspace=0.22, wspace=0.05)
def zoom(ax, variant, color, title):
    draw_board(ax, title, variant, pinlab=True)
    ax.set_xlim(8.6, 16.4); ax.set_ylim(7.6, 1.6)
    for sp in ax.spines.values(): sp.set_edgecolor(color); sp.set_linewidth(2)
def frame(ax, color):
    ax.add_patch(Rectangle((8.6, 1.6), 7.8, 6.0, fc="none", ec=color, lw=1.6, ls="--", zorder=10))
a1 = fig.add_subplot(gs[0, 0]); draw_board(a1, "A · Prova subito, senza ricambi", "bypass"); frame(a1, "#00b8d4")
z1 = fig.add_subplot(gs[0, 1]); zoom(z1, "bypass", "#00b8d4", "Ingrandimento")
a = pad_of("R4", "1"); b = pad_of("U2", "1")
z1.annotate("R4, piazzola\nverso il sensore", (a["x"], a["y"]), (a["x"] - 0.3, a["y"] + 1.55), color="#00e5ff",
            fontsize=9, ha="center", va="center", zorder=12, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color="#00e5ff", lw=1))
z1.annotate("U2 piazzola 1", (b["x"], b["y"]), (b["x"] + 1.6, b["y"] + 1.5), color="#00e5ff",
            fontsize=9, ha="center", va="center", zorder=12, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color="#00e5ff", lw=1))
z1.text(13.6, 2.05, "U2 tolto", color="#ff3b30", fontsize=9, ha="center", fontweight="bold", zorder=12)
t1 = fig.add_subplot(gs[0, 2]); t1.axis("off")
t1.text(0.02, 0.95,
 "1. Togli U2 (LMV321): aria calda, due\n    saldatori, o taglia i piedini.\n\n"
 "2. Ponticello di ~2 mm (filo sottile o\n    reoforo) tra:\n"
 "    • R4, piazzola verso il sensore (AO_RAW)\n"
 "    • U2 piazzola 1 (AO_BUF): delle tre\n      verso il sensore, quella vicina a R4\n\n"
 "3. Il segnale va all'ADC tramite R10 (100 Ω),\n    senza offset +0.15 V (come il vecchio\n    modulo Hiwonder). Firmware invariato.\n\n"
 "4. gauge_dark + gauge_ref.\n    Picco ancora basso -> laser:\n    JP2 su 2-3 (5 V).",
 va="top", fontsize=10.5, linespacing=1.25)
a2 = fig.add_subplot(gs[1, 0]); draw_board(a2, "B · Correzione definitiva: U2 -> MCP6001T-I/OT", "swap"); frame(a2, "#34c759")
z2 = fig.add_subplot(gs[1, 1]); zoom(z2, "swap", "#34c759", "Ingrandimento")
t2 = fig.add_subplot(gs[1, 2]); t2.axis("off")
t2.text(0.02, 0.95,
 "1. Togli il ponticello e monta MCP6001T-I/OT\n    (SOT-23-5) al posto di U2.\n\n"
 "2. Piedinatura 1 OUT / 2 V− / 3 IN+ /\n    4 IN− / 5 V+ = quella del PCB:\n    nient'altro da cambiare.\n\n"
 "3. Pallino del pin 1 dalla parte di R4\n    (stessa posizione dell'LMV321 tolto).\n\n"
 "4. ATTENZIONE: NON MCP6001R né MCP6001U\n    (piedinature diverse). Controlla il\n    datasheet del pezzo comprato.\n\n"
 "Perché: l'LMV321 ha 1 IN+ / 3 IN− / 4 OUT;\nsu questo PCB fa da comparatore bloccato\n(uscita fissa a 0 V o 3.2 V).",
 va="top", fontsize=10.5, linespacing=1.25)
fig.suptitle("RazorSensor rev 1.1 — rilavorazione di U2  (lato componenti, geometria dal .kicad_pcb)",
             fontsize=15, fontweight="bold", y=0.955)
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("ok", out)
