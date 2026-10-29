# Sportellino frontale scorrevole (30/10/2026): chiude la fessura frontale di carico della coda di topo, da cui il chip
# vedeva la luce ambiente (11% dell'emisfero). Scorre in verticale sulle due guide a T del pezzo unico (build_profiler.py,
# SH_*): chiuso = in basso sul piede delle guide; aperto = +13 mm (fondo a Y 76.5, sopra i labbri delle guide J: si carica
# la coda di topo); sfilandolo verso l'alto si toglie. Due nottolini elastici (linguette 1.0 mm nella lastra) scattano negli
# incavi delle guide nelle due posizioni. Incavo in basso per la spina e il cavo del sensore.
# Uscita (cartella corrente): sportello.stl (coordinate piastra, chiuso) e sportello_stampa.stl (lastra in piano).
import trimesh, numpy as np
T = trimesh.transformations
def B(x0, x1, y0, y1, z0, z1): return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])
U = lambda m: trimesh.boolean.union(m, engine="manifold"); D = lambda a, b: trimesh.boolean.difference([a, b], engine="manifold")
SH_Z = (-6.45 - 6.0, 49.55 + 6.0)                # guide (uguali a build_profiler.py)
PX = (39.75, 41.75)                              # lastra: 0.25 davanti alla testa delle guide (X 39.5), spessa 2.0
PY = (63.5, 101.0)                               # chiuso: dal sotto del raggio piu' basso visto dal chip (Y 64.42) alla cima
PZ = (SH_Z[0] - 6.05, SH_Z[1] + 6.05)            # da guida a guida (Z -18.5 ... 61.6), con due fianchi
CY = (87.6, 100.5)                               # graffe sulle guide (appoggiano sul piede a Y 87.5)
FIN_Y = (88.6, 96.6); FIN_W, FIN_T, FIN_SLOT, BUMP = 4.0, 1.0, 0.6, 0.45   # nottolino: linguetta nella lastra, dente verso la guida
body = [B(PX[0], PX[1], PY[0], PY[1], PZ[0], PZ[1])]
# fianchi alle due estremita' lungo la coda di topo: fermano i raggi radenti lungo il canale (fuori dal piede delle guide
# Z -16.85 / 59.95, anche da aperto). Lato ruota solo da X 30.5 (la ruota arriva a X 29.84).
body.append(B(25.3, PX[0] + 0.5, PY[0], 86.0, PZ[0], PZ[0] + 1.5))
body.append(B(30.5, PX[0] + 0.5, PY[0], 86.0, PZ[1] - 1.5, PZ[1]))
cuts = [B(PX[0] - 0.2, PX[1] + 0.2, PY[0] - 0.1, 67.7, 10.5, 19.6)]          # incavo per spina (Z 11.05-19.05, Y <= 67.1) e cavo
cuts.append(B(PX[0] - 0.2, PX[1] + 0.2, PY[0] - 0.1, 65.0, 3.9, 10.6))          # incavo sopra la testa della vite M3 della slitta (Z 7.25 ±2.75, X <= 40.97, Y <= 64.6)
for z in SH_Z:
    body.append(B(36.5, PX[0] + 0.5, CY[0], CY[1], z - 4.5, z + 4.5))        # graffa (fusa nella lastra)
    cuts.append(B(37.75, PX[0], CY[0] - 0.1, CY[1] + 0.1, z - 3.25, z + 3.25))   # tasca della testa (gioco 0.25)
    cuts.append(B(36.4, 37.8, CY[0] - 0.1, CY[1] + 0.1, z - 1.75, z + 1.75))  # passaggio dell'anima (gioco 0.25)
    # nottolino: due tagli verticali + taglio in basso (linguetta attaccata in alto), assottigliata dal davanti a FIN_T
    for s in (-1, 1): cuts.append(B(PX[0] - 0.1, PX[1] + 0.1, FIN_Y[0] - FIN_SLOT, FIN_Y[1], z + s*FIN_W/2 + (0 if s > 0 else -FIN_SLOT), z + s*FIN_W/2 + (FIN_SLOT if s > 0 else 0)))
    cuts.append(B(PX[0] - 0.1, PX[1] + 0.1, FIN_Y[0] - FIN_SLOT, FIN_Y[0], z - FIN_W/2 - FIN_SLOT, z + FIN_W/2 + FIN_SLOT))
    cuts.append(B(PX[0] + FIN_T, PX[1] + 0.1, FIN_Y[0] - 0.1, FIN_Y[1], z - FIN_W/2, z + FIN_W/2))
m = D(U(body), U(cuts))
dents = []
for z in SH_Z:                                                               # dente a rampa sul retro del nottolino (Y 89.6)
    pts = [[PX[0] + 0.3, y, zz] for y in (88.7, 90.5) for zz in (z - 1.5, z + 1.5)] + [[PX[0] - BUMP, y, zz] for y in (89.3, 89.9) for zz in (z - 1.5, z + 1.5)]
    dents.append(trimesh.convex.convex_hull(np.array(pts)))
m = U([m] + dents)
# presa per le dita: due nervature orizzontali sul davanti, in alto
m = U([m] + [B(PX[1] - 0.01, PX[1] + 1.2, y, y + 1.2, 6.0, 37.0) for y in (95.5, 98.5)])
# logo RazorBlade INCISO 0.6 mm sul fronte, come la scritta RazorGauge del coperchio (30/10/2026, richiesta di Stefano): dal PDF vettoriale (strumenti/logo_da_pdf.py),
# largo 76 mm, centrato lungo la lastra (Z 21.55 = asse di misura), Y 72.8-87.4: sotto i nottolini (Y >= 88) e sopra gli incavi.
# Solchi alla larghezza vera del logo (31/10: tolto l'allargamento 0.05, assottigliava le creste tra le lettere). Lastra 2.0 -> sotto il logo 1.4 mm.
import json, os, shapely.geometry as sg, shapely.ops as so
LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo", "logo_razorblade_76mm.json")
if os.path.exists(LOGO):
    _d = json.load(open(LOGO)); _P = so.unary_union([sg.Polygon(e, h) for e, h in _d["polys"]]).buffer(0.0, join_style=1)
    LOGO_YC, LOGO_D = 80.1, 0.6
    _parts = []
    for g in (_P.geoms if hasattr(_P, "geoms") else [_P]):
        e = trimesh.creation.extrude_polygon(g, LOGO_D + 0.2)
        e.apply_transform(np.array([[0, 0, 1, PX[1] - LOGO_D], [0, 1, 0, LOGO_YC], [-1, 0, 0, 21.55], [0, 0, 0, 1]], float))   # vista dal fronte: destra = -Z
        _parts.append(e)
    m = D(m, U(_parts))
m.export("sportello.stl")
p = m.copy(); p.apply_transform(T.rotation_matrix(-np.pi/2, [0, 1, 0])); p.apply_translation(-p.bounds[0]); p.export("sportello_stampa.stl")
print("sportello: chiuso %s, %.2f cm3, %s, corpi %d" % (m.is_watertight, m.volume/1000, m.extents.round(2), len(m.split())))
