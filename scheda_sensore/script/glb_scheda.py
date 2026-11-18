# GLB 3D della scheda sensore RazorSensor (dal kicad_pcb reale): FR4, rame top/bottom sotto maschera, piazzole scoperte,
# serigrafia, fori, componenti (corpi indicativi dalle dimensioni dei package), cavo saldato con calza isolata.
# Frame three.js: X = x KiCad, Y = alto (lato componenti), Z = y KiCad.  Uso: HOME=/tmp/kh python3 glb_scheda.py out.glb
import sys, pcbnew, numpy as np, trimesh, shapely.geometry as sg, shapely.ops as so
T = trimesh.transformations
TH = 1.6; CU = 0.035; MK = 0.02; SK = 0.015
b = pcbnew.LoadBoard("RazorSensor/RazorSensor.kicad_pcb")
mm = pcbnew.ToMM; ERR = pcbnew.FromMM(0.01)

def ps2shp(ps):
    ps.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST); out = []
    for i in range(ps.OutlineCount()):
        o = ps.COutline(i); ext = [(mm(o.CPoint(j).x), mm(o.CPoint(j).y)) for j in range(o.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hh = ps.CHole(i, h); holes.append([(mm(hh.CPoint(j).x), mm(hh.CPoint(j).y)) for j in range(hh.PointCount())])
        if len(ext) >= 3: out.append(sg.Polygon(ext, holes).buffer(0))
    return so.unary_union(out) if out else sg.Polygon()

def layer_poly(layer, pads=True, tracks=True, zones=True, drawings=True, texts=True):
    ps = pcbnew.SHAPE_POLY_SET()
    if tracks:
        for t in b.GetTracks():
            if t.IsOnLayer(layer): t.TransformShapeToPolygon(ps, layer, 0, ERR, 1)
    if zones:
        for z in b.Zones():
            if z.IsOnLayer(layer) and not z.GetIsRuleArea():
                f = z.GetFilledPolysList(layer)
                for i in range(f.OutlineCount()): ps.AddOutline(f.COutline(i))
                for i in range(f.OutlineCount()):
                    for h in range(f.HoleCount(i)): ps.AddHole(f.CHole(i, h), ps.OutlineCount() - f.OutlineCount() + i)
    for fp in b.GetFootprints():
        if pads:
            for p in fp.Pads():
                if p.IsOnLayer(layer): p.TransformShapeToPolygon(ps, layer, 0, ERR, 1)
        if drawings:
            for g in fp.GraphicalItems():
                if g.IsOnLayer(layer):
                    g.TransformShapeToPolygon(ps, layer, 0, ERR, 1)
    if drawings or texts:
        for d in b.GetDrawings():
            if d.IsOnLayer(layer): d.TransformShapeToPolygon(ps, layer, 0, ERR, 1)
    return ps2shp(ps)

# contorno e fori
edge = sg.box(0, 0, 24, 18)
bb = b.GetBoardEdgesBoundingBox()
holes = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        d = p.GetDrillSize().x
        if d > 0: x, y = mm(p.GetPosition()); holes.append(sg.Point(x, y).buffer(mm(d) / 2, 48))
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA": x, y = mm(t.GetPosition()); holes.append(sg.Point(x, y).buffer(mm(t.GetDrillValue()) / 2, 16))
HOLES = so.unary_union(holes)

def ext(poly, y0, y1):                              # poligono (x, y KiCad) estruso in altezza fra y0 e y1 (frame three)
    poly = poly.difference(HOLES).simplify(0.004) if not poly.is_empty else poly
    ms = []
    for g in (poly.geoms if hasattr(poly, "geoms") else [poly]):
        if g.is_empty or g.area < 1e-4: continue
        m = trimesh.creation.extrude_polygon(g, y1 - y0)
        m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
        m.invert() if m.volume < 0 else None
        ms.append(m)
    return trimesh.util.concatenate(ms) if ms else None

parts = {}
parts["scheda_FR4"] = ext(edge, -TH, 0)
import svg2shp, subprocess, os
SV = "/tmp/claude-0/svg"; os.makedirs(SV, exist_ok=True)
def L(n):
    subprocess.run(["kicad-cli", "pcb", "export", "svg", "--exclude-drawing-sheet", "--drill-shape-opt", "0", "--black-and-white", "-l", n, "-o", f"{SV}/{n}.svg", "RazorSensor/RazorSensor.kicad_pcb"], capture_output=True)
    return svg2shp.layer(f"{SV}/{n}.svg")
cuF, cuB, mkF, mkB = L("F.Cu"), L("B.Cu"), L("F.Mask"), L("B.Mask")
parts["maschera_top"] = ext(edge.difference(mkF), 0, MK)
parts["maschera_bottom"] = ext(edge.difference(mkB), -TH - MK, -TH)
parts["rame_top"] = ext(cuF.difference(mkF), MK, MK + CU)                       # rame sotto maschera (rilievo)
parts["rame_bottom"] = ext(cuB.difference(mkB), -TH - MK - CU, -TH - MK)
parts["piazzole_top"] = ext(cuF.intersection(mkF), 0, CU)
parts["piazzole_bottom"] = ext(cuB.intersection(mkB), -TH - CU, -TH)
skF = L("F.Silkscreen").difference(mkF); skB = L("B.Silkscreen").difference(mkB)
parts["serigrafia_top"] = ext(skF, MK + CU, MK + CU + SK)
parts["serigrafia_bottom"] = ext(skB, -TH - MK - CU - SK, -TH - MK - CU)
# metallizzazione dei fori passanti (piazzole del cavo)
pth = []
for p in b.FindFootprintByReference("J1").Pads():
    x, y = mm(p.GetPosition()); r = mm(p.GetDrillSize().x) / 2
    c = sg.Point(x, y).buffer(r + 0.03, 32).difference(sg.Point(x, y).buffer(r, 32))
    m = trimesh.creation.extrude_polygon(c, TH); m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, -TH], [0, 1, 0, 0], [0, 0, 0, 1]], float))
    if m.volume < 0: m.invert()
    pth.append(m)
parts["piazzole_top"] = trimesh.util.concatenate([parts["piazzole_top"]] + pth)

def box(cx, cz, sx, sz, y0, y1):
    return trimesh.creation.box(bounds=[[cx - sx / 2, y0, cz - sz / 2], [cx + sx / 2, y1, cz + sz / 2]])
Y0 = CU
for fp in b.GetFootprints():
    ref = fp.GetReference(); pads = list(fp.Pads())
    if ref[0] in "RC":
        (x1, y1), (x2, y2) = [mm(p.GetPosition()) for p in pads]
        big = abs(y1 - y2) > 1.75                      # 0805
        L, W, H = (2.0, 1.25, 0.85) if big else (1.6, 0.8, 0.45 if ref[0] == "R" else 0.8)
        cx, cz = (x1 + x2) / 2, (y1 + y2) / 2; vert = abs(y1 - y2) > abs(x1 - x2)
        sx, sz = (W, L) if vert else (L, W)
        cap = 0.3 if not big else 0.45
        body = box(cx, cz, sx, sz, Y0, Y0 + H)
        e1 = box(cx, cz - (L / 2 - cap / 2), W + 0.02, cap, Y0, Y0 + H + 0.01) if vert else box(cx - (L / 2 - cap / 2), cz, cap, W + 0.02, Y0, Y0 + H + 0.01)
        e2 = box(cx, cz + (L / 2 - cap / 2), W + 0.02, cap, Y0, Y0 + H + 0.01) if vert else box(cx + (L / 2 - cap / 2), cz, cap, W + 0.02, Y0, Y0 + H + 0.01)
        mid = box(cx, cz, sx - (0 if not vert else 0.0), sz - 2 * cap, Y0, Y0 + H) if vert else box(cx, cz, sx - 2 * cap, sz, Y0, Y0 + H)
        parts[f"{ref}_corpo"] = mid
        parts[f"{ref}_terminali"] = trimesh.util.concatenate([e1, e2])
    elif ref == "U2":                                   # SOT-23-5 (2.9 x 1.6 x 1.1), reofori a gabbiano
        x, y = mm(fp.GetPosition())
        parts["U2_corpo"] = box(x, y, 2.9, 1.6, Y0 + 0.1, Y0 + 1.1)
        leads = []
        for p in pads:
            px, py = mm(p.GetPosition()); s = 1 if py > y else -1
            leads.append(box(px, y + s * 0.95, 0.4, 0.5, Y0 + 0.35, Y0 + 0.5)); leads.append(box(px, py + s * 0.05, 0.4, 0.6, Y0, Y0 + 0.15))
        parts["U2_reofori"] = trimesh.util.concatenate(leads)
    elif ref == "U1":                                   # TSL1401CL package CL: 9.4 x 3.0 x 1.2, plastica trasparente
        x, y = mm(fp.GetPosition())                     # 08/11/2026: l'origine del footprint e' il CENTRO DEI PIXEL (asse laser);
        cx = x; cy = float(np.mean([mm(p.GetPosition())[1] for p in pads]))   # centro del package: X = origine, Y = centro delle file di piazzole
        parts["U1_corpo_trasparente"] = box(cx, cy, 9.4, 3.0, Y0 + 0.02, Y0 + 1.2)
        # substrato e matrice di fotodiodi (8.064 x 0.064) a 0.305 dal centro del package verso i pin 5-8 = sull'origine del footprint
        parts["U1_substrato"] = box(cx, cy, 9.3, 2.9, Y0 + 0.02, Y0 + 0.25)
        parts["U1_die"] = box(cx, (cy + y) / 2, 8.6, 0.9, Y0 + 0.25, Y0 + 0.5)
        parts["U1_fotodiodi"] = box(x, y, 8.064, 0.064, Y0 + 0.5, Y0 + 0.52)
        parts["U1_contatti"] = trimesh.util.concatenate([box(*mm(p.GetPosition()), mm(p.GetSize().x) * 0.85, mm(p.GetSize().y) * 0.85, Y0, Y0 + 0.03) for p in pads])

# cavo: 5 fili saldati dal lato componenti (stagno sotto, nello scarico 0.8 della slitta), escono verso +X; calza isolata
COLS = {"1": "3V3", "2": "GND", "3": "SI", "4": "CLK", "5": "AO"}
def tube(pts, r, sec=14):
    pts = np.array(pts, float); ms = []
    for a, c in zip(pts[:-1], pts[1:]):
        v = c - a; L = np.linalg.norm(v)
        cy = trimesh.creation.cylinder(radius=r, height=L, sections=sec)
        cy.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], v / L)); cy.apply_translation((a + c) / 2); ms.append(cy)
        sp = trimesh.creation.icosphere(subdivisions=1, radius=r); sp.apply_translation(c); ms.append(sp)
    return trimesh.util.concatenate(ms)
J1 = {p.GetNumber(): mm(p.GetPosition()) for p in b.FindFootprintByReference("J1").Pads()}
solder = []
for n, (x, y) in J1.items():
    w = tube([[x, -TH - 0.6, y], [x, 0.9, y], [x + 1.4, 1.5, y], [30.0, 1.5, y], [34.0, 1.5, 5.6 + (y - 5.6) * 0.35]], 0.30)
    ins = tube([[x + 1.0, 1.4, y], [30.0, 1.5, y], [34.0, 1.5, 5.6 + (y - 5.6) * 0.35]], 0.48)
    parts[f"filo_{n}_{COLS[n]}_rame"] = w
    parts[f"filo_{n}_{COLS[n]}"] = ins
    cone = trimesh.creation.cone(radius=0.62, height=0.45, sections=24); cone.apply_translation([x, CU, y]); solder.append(cone)
    cone = trimesh.creation.cone(radius=0.62, height=0.45, sections=24); cone.apply_transform(T.rotation_matrix(np.pi, [1, 0, 0])); cone.apply_translation([x, -TH - CU, y]); solder.append(cone)
parts["stagno"] = trimesh.util.concatenate(solder)
parts["calza_schermo"] = tube([[33.2, 1.5, 5.6], [37.0, 1.5, 5.6]], 1.75, 24)                  # calza tagliata e ripiegata
parts["guaina_termo"] = tube([[32.6, 1.5, 5.6], [36.0, 1.5, 5.6]], 1.95, 24)                   # termorestringente: calza isolata
parts["guaina_cavo"] = tube([[35.5, 1.5, 5.6], [48.0, 1.5, 5.6]], 1.6, 24)

sc = trimesh.Scene()
for k, m in parts.items():
    if m is not None and len(m.faces): sc.add_geometry(m, node_name=k, geom_name=k)
sc.export(sys.argv[1] if len(sys.argv) > 1 else "scheda.glb")
print(len(parts), {k: (len(m.faces) if m is not None else 0) for k, m in parts.items()})
