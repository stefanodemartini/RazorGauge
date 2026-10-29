# Logo RazorBlade (PDF vettoriale di Stefano) -> contorni 2D in mm per il rilievo sullo sportellino.
# Rasterizza il PDF a 1200 dpi (pdftoppm), estrae i contorni con OpenCV (con i fori interni delle lettere), li scala alla
# larghezza voluta e salva logo_razorblade.json: lista di poligoni [esterno, [fori...]] in mm, origine al centro, x a destra, y in alto.
import sys, subprocess, json, numpy as np, cv2, shapely.geometry as sg, shapely.ops as so, tempfile, os
pdf, out, width_mm = sys.argv[1], sys.argv[2], float(sys.argv[3])
DPI = 1200
tmp = tempfile.mkdtemp(); subprocess.run(["pdftoppm", "-r", str(DPI), "-gray", "-png", pdf, os.path.join(tmp, "p")], check=True)
img = cv2.imread(os.path.join(tmp, sorted(os.listdir(tmp))[0]), cv2.IMREAD_GRAYSCALE)
b = (img < 128).astype(np.uint8)
cnts, hier = cv2.findContours(b, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
polys = []
for i, c in enumerate(cnts):
    if hier[0][i][3] != -1 or len(c) < 8: continue               # solo contorni esterni; i fori sono i figli
    ext = c[:, 0, :].astype(float)
    holes = []; j = hier[0][i][2]
    while j != -1:
        if len(cnts[j]) >= 8: holes.append(cnts[j][:, 0, :].astype(float))
        j = hier[0][j][0]
    p = sg.Polygon(ext, holes).buffer(0)
    if p.area > 50: polys.append(p)
U = so.unary_union(polys); x0, y0, x1, y1 = U.bounds
s = width_mm / (x1 - x0); cx, cy = (x0 + x1)/2, (y0 + y1)/2
def tr(xy): return [((x - cx)*s, -(y - cy)*s) for x, y in xy]
res = []
for g in (U.geoms if hasattr(U, "geoms") else [U]):
    g = sg.Polygon(tr(g.exterior.coords), [tr(r.coords) for r in g.interiors]).simplify(0.01, preserve_topology=True)
    res.append([list(g.exterior.coords), [list(r.coords) for r in g.interiors]])
json.dump({"width_mm": width_mm, "height_mm": (y1 - y0)*s, "polys": res}, open(out, "w"))
print("logo: %d parti, %.2f x %.2f mm, fori %d" % (len(res), width_mm, (y1 - y0)*s, sum(len(r[1]) for r in res)))
