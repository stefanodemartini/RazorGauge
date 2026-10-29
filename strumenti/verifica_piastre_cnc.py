# Verifica pezzi stampati (pezzo unico MJF + assieme) contro le lastre CNC GIA' ORDINATE (STEP in piastra_alluminio/cnc).
# Dipendenze: trimesh, shapely, manifold3d, cascadio (pip install cascadio) per leggere gli STEP.
# Esempio (dalla cartella del repo): python3 strumenti/verifica_piastre_cnc.py piastra_alluminio/cnc integrazione_profiler/FlylineProfiler_RazorGauge_pezzo_unico.stl integrazione_profiler/FlylineProfiler_RazorGauge_assieme.glb
# Da rilanciare dopo OGNI modifica degli STL. Uso: python3 verifica_piastre_cnc.py <cartella_cnc> <pezzo_unico.stl> <assieme.glb>
import sys, numpy as np, trimesh, shapely.geometry as sg, shapely.ops as so
CNC, PU, GLB = sys.argv[1], sys.argv[2], sys.argv[3]
def load_step(n):
    m = trimesh.load(CNC + '/' + n + '.step'); m = m.to_geometry() if hasattr(m, 'to_geometry') else m
    m.apply_scale(1000.0); return m
def step_poly(m, z=3.0):                                   # sezione a meta spessore -> poligono 2D nelle coordinate dello STEP
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]); p, M = s.to_2D(to_2D=np.eye(4))
    return so.unary_union(p.polygons_full)
res = []
def rep(ok, txt): res.append(("OK " if ok else "!! ") + txt); print(res[-1])
# ---- piastra verticale nelle coordinate dell'assieme: Z = 92 - x_step, Y = y_step - 26, X = z_step - 6 (fronte X 0, retro X -6)
Pst = step_poly(load_step('RG_piastra_verticale'))
Ppl = so.unary_union([sg.Polygon([(92 - x, y - 26) for x, y in g.exterior.coords], [[(92 - x, y - 26) for x, y in r.coords] for r in g.interiors]) for g in getattr(Pst, 'geoms', [Pst])])   # (Z, Y)
outer = so.unary_union([sg.Polygon(g.exterior) for g in getattr(Ppl, 'geoms', [Ppl])])
holes = [sg.Polygon(r) for g in getattr(Ppl, 'geoms', [Ppl]) for r in g.interiors]
def ext_ZY(poly, x0, x1):
    m = trimesh.creation.extrude_polygon(poly, x1 - x0)       # (Z,Y,w) -> (X=w+x0, Y, Z)
    m.apply_transform(np.array([[0, 0, 1, x0], [0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float))
    if m.volume < 0: m.invert()
    return m
plate = ext_ZY(Ppl, -6.0, 0.0)
rep(abs(plate.volume - 378789) < 2000, "Piastra verticale dallo STEP: %.0f mm3, %d fori/aperture, contorno Z %.1f..%.1f Y %.1f..%.1f"
    % (plate.volume, len(holes), *np.array(outer.bounds)[[0, 2, 1, 3]]))
# ---- pezzo unico
P = trimesh.load(PU)
cut = P.slice_plane([0.05, 0, 0], [-1, 0, 0])                  # strato posteriore X 0..0.05
foot = so.unary_union([sg.Polygon([(q[2], q[1]) for q in f]).buffer(0) for f in P.vertices[P.faces[(P.triangles_center[:, 0] < 0.02) & (P.face_normals[:, 0] < -0.99)]]])
foot = foot.buffer(0.01).buffer(-0.01)
rep(foot.area > 100, "Impronta posteriore del pezzo unico (faccia X 0): %.0f mm2" % foot.area)
rep(foot.difference(outer).area < 0.5, "Impronta dentro il contorno della piastra (fuori: %.2f mm2)" % foot.difference(outer).area)
rep(P.bounds[0][0] > -0.01, "Pezzo unico non sporge dietro la faccia della piastra (X min %.3f)" % P.bounds[0][0])
# ---- fori della piastra sotto l'impronta: devono essere i fori delle viti del pezzo (allineati) o aperture previste
def ray_free(x0, x1, y, z):                                    # True se il segmento lungo X non attraversa materiale del pezzo
    loc, _, _ = P.ray.intersects_location(np.array([[x0, y, z]]), np.array([[1.0, 0, 0]]))
    return not any(x0 < l[0] < x1 for l in loc)
foot_fill = so.unary_union([sg.Polygon(g.exterior) for g in getattr(foot, 'geoms', [foot])])
RB = [(-2.0, 61.0), (85.0, 61.0), (-2.0, 203.0), (85.0, 203.0)]   # fori distanziali RazorBoard (Z, Y), da layout.py: filetto maschio max 6 -> a filo
def bore_free(y, z, r=1.6, x1=59.0):
    return all(ray_free(-0.1, x1, y + r * np.sin(a), z + r * np.cos(a)) for a in np.linspace(0, 2 * np.pi, 12, endpoint=False))
def seat_x(y, z, r=2.9):
    seat = []
    for a in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        l2, _, _ = P.ray.intersects_location(np.array([[60.0, y + r * np.sin(a), z + r * np.cos(a)]]), np.array([[-1.0, 0, 0]]))
        seat.append(max([q[0] for q in l2 if q[0] < 60], default=0.0))
    return float(np.median(seat))
n_as = 0
for h in holes:
    c = h.centroid; z, y = c.x, c.y; bz = h.bounds; w, hh = bz[2] - bz[0], bz[3] - bz[1]
    inside = h.intersection(foot_fill).area / h.area
    if inside < 0.001 and not h.buffer(1.0).intersects(foot_fill): continue
    small = w < 3.5 and hh < 3.5
    isRB = any(np.hypot(z - a, y - b) < 0.3 for a, b in RB)
    if small and isRB:
        cov = not bore_free(y, z, 1.0, 2.0)
        rep(True, "Foro distanziale RazorBoard Z %.2f Y %.2f: %s" % (z, y, "coperto dal pezzo (filetto maschio max 6 mm, a filo)" if cov else "libero"))
    elif small:
        n_as += 1; fb = bore_free(y, z); s = seat_x(y, z)
        rep(fb and 5.5 <= s <= 9.5 and inside > 0.99, "Vite M3x12 Z %.2f Y %.2f: foro Ø3.2 libero nel pezzo %s, appoggio testa X %.2f -> filetto in piastra %.1f mm"
            % (z, y, "si" if fb else "NO (non allineato/coperto)", s, 12 - s))
    else:
        rep(True, "Apertura piastra Z %.1f Y %.1f (%.1f x %.1f): coperta dal pezzo per il %.0f%%" % (z, y, w, hh, 100 * inside))
rep(n_as == 8, "Fori viti pezzo unico -> piastra trovati: %d (attesi 8)" % n_as)
# fori passanti del pezzo (Ø3-3.6) sulla faccia posteriore che cadono sul pieno della piastra
pieces = [g for g in getattr(foot, 'geoms', [foot])]
orph = []; blind = []
for g in pieces:
    for r in g.interiors:
        q = sg.Polygon(r); bb = q.bounds
        if 2.8 < bb[2] - bb[0] < 4.0 and 2.8 < bb[3] - bb[1] < 4.0:
            if not any(q.centroid.distance(hh.centroid) < 0.5 or hh.contains(q) for hh in holes):   # allineato a un foro o dentro un'apertura (es. Ø42 encoder)
                cz, cy = q.centroid.x, q.centroid.y
                if ray_free(-0.1, 59.0, cy, cz): orph.append("Z %.2f Y %.2f" % (cz, cy))      # passante: una vite finirebbe sul pieno
                else: blind.append("Z %.2f Y %.2f" % (cz, cy))
rep(not orph, "Fori passanti Ø3-4 del pezzo senza foro corrispondente nella piastra: %s" % (orph if orph else "nessuno"))
if blind: print("   (tasche cieche dal retro, non interessano la piastra: %s)" % ", ".join(blind))
# ---- fori del pezzo che finiscono sul pieno della piastra (vite senza filetto sotto)
# ---- interferenze tra la piastra e tutte le parti dell'assieme
G = trimesh.load(GLB); bad = []
for k, g in G.geometry.items():
    if k == 'cavo_2mm': continue
    try: v = trimesh.boolean.intersection([plate, g], engine='manifold').volume
    except Exception: v = -1
    if v > 1e-3 or v < 0: bad.append("%s %.3f" % (k, v))
rep(not bad, "Piastra verticale: nessuna compenetrazione con le parti dell'assieme %s" % (bad if bad else ""))
# ---- encoder nel foro Ø42 (A1)
if 'encoder_LPD3806' in G.geometry:
    e = G.geometry['encoder_LPD3806']; v = e.vertices[e.vertices[:, 0] < 0.5]
    if len(v):
        r = np.hypot(v[:, 1] - 35.0, v[:, 2] - 49.55).max(); rep(r < 21.0 - 0.5, "Corpo encoder nel foro Ø42 della piastra: raggio max %.2f (gioco %.2f)" % (r, 21.0 - r))
# ---- ruota encoder CNC (STEP): asse = asse encoder (Y 35, Z 49.55), mozzo verso la parete, faccia posteriore del mozzo a X 10.44
#      (cerchio X 17.22..27.22 = mezzeria sulla linea X 22.22; parete del pezzo a X 7.22: 10.0 mm fino al cerchio)
W = load_step('RG_ruota_encoder'); W.merge_vertices()
rep(abs(W.extents[0] - 63.66) < 0.05 and abs(W.extents[2] - 16.78) < 0.05, "Ruota CNC dallo STEP: Ø%.2f x %.2f" % (W.extents[0], W.extents[2]))
W.apply_transform(np.array([[0, 0, 1, 10.44], [0, 1, 0, 35.0], [1, 0, 0, 49.55], [0, 0, 0, 1]], float))   # (x,y,z)->(X=z+10.44, Y=y+35, Z=x+49.55)
cl = []
S = W.sample(6000); bb = W.bounds
def crop(g):
    c = g
    for o, n in (([bb[0][0] - 2, 0, 0], [1, 0, 0]), ([bb[1][0] + 2, 0, 0], [-1, 0, 0]), ([0, bb[0][1] - 2, 0], [0, 1, 0]),
                 ([0, bb[1][1] + 2, 0], [0, -1, 0]), ([0, 0, bb[0][2] - 2], [0, 0, 1]), ([0, 0, bb[1][2] + 2], [0, 0, -1])):
        if len(c.faces) == 0: return c
        c = c.slice_plane(o, n)
    return c
for k, g in [('pezzo_unico', P)] + [(k, g) for k, g in G.geometry.items() if k not in ('ruota_encoder_200mm', 'albero_encoder', 'cavo_2mm', 'pezzo_unico')]:
    c = crop(g)
    if len(c.faces) == 0: continue
    q, d, _ = trimesh.proximity.closest_point(c, S); i = int(np.argmin(d))
    if d[i] < 1.0: cl.append("%s %.2f mm a X %.1f Y %.1f Z %.1f" % (k, d[i], *q[i]))
bad = [c for c in cl if float(c.split()[1]) < 0.5]
rep(not bad, "Ruota CNC (mozzo Ø18 + battistrada, tolleranza Ø ±0.10, eccentricità 0.05): gioco minimo >= 0.5 mm%s"
    % ((" | sotto 1 mm: " + "; ".join(cl)) if cl else ", tutto oltre 1 mm"))
# ---- tacca cavo laser (A4, bordo superiore) rispetto alla torre
top = P.vertices[:, 1].max(); rep(top < outer.bounds[3], "Pezzo unico sotto il bordo superiore della piastra (Y %.2f < %.2f)" % (top, outer.bounds[3]))
print("\nRISULTATO:", "TUTTO OK" if all(r.startswith("OK") for r in res) else "CONTROLLARE LE RIGHE !!")
