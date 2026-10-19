# Vista 3D della RazorBoard: texture reale dei layer + modelli semplificati dei componenti (pyvista, offscreen)
import math, numpy as np, pcbnew, pyvista as pv
from PIL import Image, ImageDraw
from pcbnew import ToMM

W, H, T = 175.0, 125.0, 1.6
board = pcbnew.LoadBoard("/home/claude/board/RazorBoard/RazorBoard.kicad_pcb")

# ------------------------------------------------------------- texture
def texture(side):
    cu, mk, sk = [np.array(Image.open(f"{side}.{l}.png").convert("L")) < 128 for l in ("Cu", "Mask", "SilkS")]
    h, w = cu.shape
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (18, 82, 38)                       # solder mask su FR4
    img[cu] = (38, 128, 58)                     # mask sopra il rame
    img[mk] = (205, 205, 198)                   # pad stagnati (HASL)
    img[sk & ~mk] = (238, 238, 232)             # serigrafia
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    sx, sy = w / W, h / H
    for fp in board.GetFootprints():
        for p in fp.Pads():
            r = ToMM(p.GetDrillSize().x) / 2
            if r <= 0: continue
            x, y = ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)
            if side == "B": x = W - x
            d.ellipse([(x - r) * sx, (y - r) * sy, (x + r) * sx, (y + r) * sy], fill=(25, 25, 25))
    for tr in board.GetTracks():
        if tr.GetClass() == "PCB_VIA":
            r = ToMM(tr.GetDrillValue()) / 2; x, y = ToMM(tr.GetPosition().x), ToMM(tr.GetPosition().y)
            if side == "B": x = W - x
            d.ellipse([(x - r) * sx, (y - r) * sy, (x + r) * sx, (y + r) * sy], fill=(25, 25, 25))
    return pv.numpy_to_texture(np.array(im).copy())

pl = pv.Plotter(off_screen=True, window_size=(2200, 1500))
pl.set_background("#e9ecef", top="#ffffff")
# coordinate 3D: X = x scheda, Y = -y scheda (y verso l'alto), Z verso l'alto
top = pv.Plane(center=(W / 2, -H / 2, T), direction=(0, 0, 1), i_size=W, j_size=H)
top.texture_map_to_plane(inplace=True)
bot = pv.Plane(center=(W / 2, -H / 2, 0), direction=(0, 0, -1), i_size=W, j_size=H)
bot.texture_map_to_plane(inplace=True)
pl.add_mesh(top, texture=texture("F"))
pl.add_mesh(bot, texture=texture("B"))
pl.add_mesh(pv.Box(bounds=(0, W, -H, 0, 0.001, T - 0.001)), color="#c8b98a")   # bordo FR4

# ------------------------------------------------------------- primitive
def P(x, y): return (x, -y)
def add(mesh, color, **kw): pl.add_mesh(mesh, color=color, smooth_shading=True, **kw)
def box_local(cx, cy, ang, lx, ly, z0, hz, color, ox=0.0, oy=0.0):
    """box centrato in (cx,cy)+offset locale ruotato di ang (gradi, convenzione KiCad: antiorario a schermo)"""
    a = math.radians(ang)
    dx = ox * math.cos(a) + oy * math.sin(a); dy = -ox * math.sin(a) + oy * math.cos(a)
    b = pv.Box(bounds=(-lx / 2, lx / 2, -ly / 2, ly / 2, z0, z0 + hz))
    b.rotate_z(ang, inplace=True)
    b.translate((cx + dx, -(cy + dy), 0), inplace=True)
    add(b, color)
def cyl(p1, p2, r, color, z):
    c = ((p1[0] + p2[0]) / 2, -(p1[1] + p2[1]) / 2, z)
    d = (p2[0] - p1[0], -(p2[1] - p1[1]), 0)
    L = math.hypot(*d[:2])
    add(pv.Cylinder(center=c, direction=d, radius=r, height=L, resolution=40), color)
def vcyl(x, y, r, z0, h, color, res=48):
    add(pv.Cylinder(center=(x, -y, z0 + h / 2), direction=(0, 0, 1), radius=r, height=h, resolution=res), color)

def pads(fp):
    return {p.GetNumber(): (ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)) for p in fp.Pads()}
def padlist(fp):
    return [(p.GetNumber(), ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)) for p in fp.Pads()]

Z = T
for fp in board.GetFootprints():
    ref = fp.GetReference(); name = fp.GetFPID().GetLibItemName().wx_str()
    ang = fp.GetOrientationDegrees()
    x0, y0 = ToMM(fp.GetPosition().x), ToMM(fp.GetPosition().y)
    pd = pads(fp)
    if name.startswith("ESP32_DevKitV1"):
        # zoccoli femmina 1x15 (h 8.5) + modulo DevKit sopra
        for col in (0.0, 25.4):
            box_local(x0 + col, y0 + 14 * 2.54 / 2, 0, 2.54, 15 * 2.54, Z, 8.5, "#1b1b1b")
        mz = Z + 8.5 + 2.5
        bx = x0 + 12.7; by = y0 - 6.6 + 52.0 / 2
        box_local(bx, by, 0, 28.3, 52.0, mz, 1.6, "#202326")                    # PCB modulo
        box_local(bx, y0 - 6.6 + 52 - 3.0 - 9, 0, 18.0, 25.5, mz + 1.6, 3.1, "#b8bcc2")   # schermo WROOM
        box_local(bx, y0 - 6.6 + 52 - 3.0, 0, 18.0, 6.0, mz + 1.6, 0.8, "#2a2a2a")       # antenna
        box_local(bx, y0 - 6.6 + 2.5, 0, 7.5, 5.5, mz + 1.6, 2.8, "#c9c9c9")              # micro-USB
        for dx in (-9.5, 9.5): box_local(bx + dx, y0 - 6.6 + 7, 0, 3.5, 3.5, mz + 1.6, 1.5, "#d9d9d9")  # pulsanti
        box_local(bx, y0 + 18, 0, 7.0, 7.0, mz + 1.6, 1.0, "#111111")                    # CH340/CP2102
    elif name.startswith("TerminalBlock"):
        n = len(pd); L = n * 5.08
        # corpo: in locale x da -2.54 a L-2.54, y da -5.2 (retro) a +4.6 (fronte, ingresso fili)
        box_local(x0, y0, ang, L, 9.8, Z, 10.0, "#2f8f46", ox=L / 2 - 2.54, oy=-0.3)
        for i in range(n):
            a = math.radians(ang); lx = i * 5.08
            px = x0 + lx * math.cos(a); py = y0 - lx * math.sin(a)
            vcyl(px, py, 1.6, Z + 10.0, 0.6, "#c0c0c0")                                    # vite
            box_local(px, py, ang, 3.4, 1.2, Z + 3.0, 3.2, "#0b2e15", oy=4.3)               # foro ingresso filo
    elif name.startswith("DIP-"):
        n = len(pd); rows = n // 2
        box_local(x0 + 3.81, y0 + (rows - 1) * 2.54 / 2, 0, 6.4, rows * 2.54 + 0.5, Z + 0.6, 3.3, "#1a1a1a")
        vcyl(x0 + 3.81, y0 + 0.2, 0.6, Z + 3.9, 0.05, "#555555")
    elif name.startswith("R_Axial"):
        p1, p2 = pd["1"], pd["2"]
        cyl(p1, p2, 0.35, "#b0b0b0", Z + 1.25)
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        dirv = ((p2[0] - p1[0]) / 10.16, (p2[1] - p1[1]) / 10.16)
        a = (mid[0] - dirv[0] * 3.15, mid[1] - dirv[1] * 3.15); b = (mid[0] + dirv[0] * 3.15, mid[1] + dirv[1] * 3.15)
        cyl(a, b, 1.25, "#d8c08f", Z + 1.25)
        for k, col in ((-1.8, "#7a3b10"), (-0.9, "#111111"), (0.0, "#d02020"), (1.9, "#c9a227")):
            c1 = (mid[0] + dirv[0] * (k - 0.25), mid[1] + dirv[1] * (k - 0.25)); c2 = (mid[0] + dirv[0] * (k + 0.25), mid[1] + dirv[1] * (k + 0.25))
            cyl(c1, c2, 1.28, col, Z + 1.25)
    elif name.startswith("C_Disc"):
        p1, p2 = pd["1"], pd["2"]
        c = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        add(pv.Cylinder(center=(c[0], -c[1], Z + 4.5), direction=(0, 1, 0), radius=2.5, height=2.5, resolution=40), "#d9822b")
    elif name.startswith("CP_Radial"):
        D = float(name.split("_D")[1].split("mm")[0]); p1, p2 = pd["1"], pd["2"]
        c = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        hgt = 11.5 if D >= 6 else 11.0
        vcyl(c[0], c[1], D / 2, Z, hgt, "#1d3c8a")
        vcyl(c[0], c[1], D / 2 * 0.98, Z + hgt, 0.05, "#c8c8c8")
    elif name.startswith("D_DO"):
        p1, p2 = pd["1"], pd["2"]
        dims = {"DO-201AD": (2.7, 9.5, "#151515"), "DO-15": (1.8, 7.6, "#151515"), "DO-41": (1.35, 5.2, "#151515"), "DO-35": (0.95, 4.0, "#d98c2b")}
        r, L, col = next(v for k, v in dims.items() if k in name)
        cyl(p1, p2, 0.4, "#b0b0b0", Z + r)
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2); ln = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        u = ((p2[0] - p1[0]) / ln, (p2[1] - p1[1]) / ln)
        a = (mid[0] - u[0] * L / 2, mid[1] - u[1] * L / 2); b = (mid[0] + u[0] * L / 2, mid[1] + u[1] * L / 2)
        cyl(a, b, r, col, Z + r)
        k1 = (a[0] + u[0] * 0.6, a[1] + u[1] * 0.6); k2 = (a[0] + u[0] * 1.3, a[1] + u[1] * 1.3)   # banda catodo (pin 1)
        cyl(k1, k2, r * 1.02, "#dddddd", Z + r)
    elif name.startswith("LED_D3"):
        p1, p2 = pd["1"], pd["2"]; c = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        val = fp.GetValue().lower()
        col = "#3ccf4e" if "verde" in val else ("#ffd21f" if "giallo" in val else "#e02424")
        vcyl(c[0], c[1], 1.5, Z + 1.0, 3.8, col)
        add(pv.Sphere(radius=1.5, center=(c[0], -c[1], Z + 4.8)), col)
    elif name.startswith("TO-92"):
        c = pd["2"]
        add(pv.Cylinder(center=(c[0], -c[1], Z + 2.5 + 2.25), direction=(0, 0, 1), radius=2.4, height=4.5, resolution=40), "#151515")
    elif name.startswith("Converter_DCDC"):
        box_local(x0 + 2.54, y0 - 1.7, 0, 11.6, 7.6, Z, 10.2, "#141414")
    elif name.startswith("Fuseholder"):
        for k in ("1", "2"):
            pts = [p for p in padlist(fp) if p[0] == k]
            cx = sum(p[1] for p in pts) / len(pts); cy = sum(p[2] for p in pts) / len(pts)
            box_local(cx, cy, 0, 6.0, 6.0, Z, 8.0, "#c0c0c0")
        allx = [p[1] for p in padlist(fp)]
        cyl((min(allx) + 1, y0), (max(allx) - 1, y0), 2.5, "#e6eef0", Z + 7.0)
        cyl((min(allx) + 1, y0), (min(allx) + 5, y0), 2.55, "#b0b0b0", Z + 7.0)
        cyl((max(allx) - 5, y0), (max(allx) - 1, y0), 2.55, "#b0b0b0", Z + 7.0)
    elif name.startswith("PinHeader"):
        n = len(pd)
        box_local(x0, y0 + (n - 1) * 2.54 / 2, 0, 2.54, n * 2.54, Z, 2.5, "#1a1a1a")
        for k, (px, py) in pd.items(): box_local(px, py, 0, 0.64, 0.64, Z + 2.5, 6.0, "#d4af37")
        box_local(x0, y0 + 2.54 / 2, 0, 2.6, 5.1, Z + 2.5, 6.0, "#c41e1e")            # jumper 1-2
    elif name.startswith("SW_PUSH"):
        box_local(x0 + 3.25, y0 + 2.25, 0, 6.0, 6.0, Z, 3.5, "#2b2b2b")
        vcyl(x0 + 3.25, y0 + 2.25, 1.75, Z + 3.5, 1.5, "#111111")
    elif name.startswith("MountingHole"):
        add(pv.Cylinder(center=(x0, -y0, Z + 0.3), direction=(0, 0, 1), radius=2.8, height=0.6), "#b0b0b0")

def _dbg():
    print("bounds", pl.bounds)
    for k,a in pl.actors.items():
        b=a.GetBounds()
        if max(abs(v) for v in b)>400: print("BIG",k,b)
def snap(fname, pos, focal, up=(0, 0, 1), zoom=1.0, parallel=False):
    cam = pl.camera
    cam.focal_point = focal; cam.position = pos; cam.up = up
    if parallel:
        pl.enable_parallel_projection(); cam.parallel_scale = 66 / zoom
    else:
        pl.disable_parallel_projection(); cam.view_angle = 30.0 / zoom
    pl.camera_set = True
    pl.reset_camera_clipping_range(); pl.render()
    print(fname, cam.position)
    pl.screenshot(fname)
cx, cy = W / 2, -H / 2
pl.add_light(pv.Light(position=(cx - 120, cy - 160, 220), focal_point=(cx, cy, 0), intensity=0.6))
snap("RazorBoard_3D_iso.png", (cx - 50, cy - 300, 230), (cx, cy, 0), zoom=1.3)
snap("RazorBoard_3D_top.png", (cx, cy, 400), (cx, cy, 0), up=(0, 1, 0), zoom=1.0, parallel=True)
snap("RazorBoard_3D_morsetti.png", (95, -270, 70), (95, -100, 0), zoom=1.25)
snap("RazorBoard_3D_retro.png", (cx + 60, cy + 290, 220), (cx, cy, 0), zoom=1.3)
print("ok")
