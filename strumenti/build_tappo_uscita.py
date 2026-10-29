# Tappino removibile della gola di uscita lato ruota (31/10/2026). Va nel vano tolto dal pezzo unico (build_profiler.py, TU_*):
# X 16 - 28.37 (fronte del braccio), Y 67.4 - 69.9, Z 77.9 - 83.43. A U rovesciata: rifa' il soffitto della gola a Y 69.0
# (foro di uscita 3.6 x 3.7 con spigoli R0.6, come nel pezzo), sopra e' alto 1.5 mm in piu' (soffitto spesso 2.4).
# Fissaggio senza attrezzi: 2 perni Ø2.4 nei fori Ø2.6 delle pareti + clip elastica sul fronte con dente sotto il braccio (Y 63.9).
# Si toglie tirando in avanti la clip e sollevando. Uscita: tappo_uscita.stl (coordinate piastra) e tappo_uscita_stampa.stl.
import trimesh, numpy as np, shapely.geometry as sg
T = trimesh.transformations
def B(x0, x1, y0, y1, z0, z1): return trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])
U = lambda m: trimesh.boolean.union(m, engine="manifold"); D = lambda a, b: trimesh.boolean.difference([a, b], engine="manifold")
XB = 22.22; XF = 28.37; ZE = 83.43                     # asse gola, fronte del braccio, fine del pezzo
TU_X0, TU_Y0, TU_Z0 = 16.0, 67.4, 77.9
TU_PINS = ((18.2, 80.85), (26.2, 80.85))
G = 0.1                                                # gioco sulle facce di contatto
YT = 69.9 + 1.5                                        # cima del tappino
def ex_rect(hw, y0, y1, z):
    pr = sg.box(XB - hw, y0, XB + hw, y1).buffer(-0.6, 16).buffer(0.6, 16)
    return np.array([[x, y, z] for x, y in pr.exterior.coords])
body = [B(TU_X0 + G, XF, TU_Y0 + G, YT, TU_Z0 + G, ZE),            # corpo nel vano
        B(XF - 0.01, XF + G + 1.0, 69.9 - 1.0, YT, TU_Z0 + 0.4, ZE - 0.3)]   # sbalzo sopra il fronte da cui pende la clip
# clip: gamba 1.0 mm davanti al fronte del braccio (gioco 0.1) fino a sotto il braccio; dente 0.6 sotto (Y 63.9) con rampa
CL_Z = (TU_Z0 + 0.4, ZE - 0.3)
body.append(B(XF + G, XF + G + 1.0, 62.4, YT, *CL_Z))
dente = trimesh.convex.convex_hull(np.array([[x, y, z] for z in CL_Z for x, y in
          ((XF + G + 0.01, 62.4), (XF + G + 0.01, 63.8), (XF - 0.6, 63.8), (XF - 0.6, 63.6))]))
body.append(dente)
for px, pz in TU_PINS:                                             # perni Ø2.4 lunghi 2.3 (foro Ø2.6 profondo 2.5)
    c = trimesh.creation.cylinder(radius=1.2, height=2.4, sections=32); c.apply_transform(T.rotation_matrix(np.pi/2, [1, 0, 0]))
    c.apply_translation([px, TU_Y0 + G - 1.15, pz]); body.append(c)
m = U(body)
cuts = [trimesh.convex.convex_hull(np.vstack([ex_rect(1.8, 65.3, 69.0, 77.0), ex_rect(1.8, 65.3, 69.0, 83.0)])),     # gola (come nel pezzo)
        trimesh.convex.convex_hull(np.vstack([ex_rect(1.8, 65.3, 69.0, 82.9), ex_rect(2.2, 64.9, 69.3, 83.7)]))]     # smusso d'uscita
m = D(m, U(cuts))
# smusso 0.5 sullo spigolo superiore anteriore (presa e niente spigolo vivo)
m = D(m, trimesh.convex.convex_hull(np.array([[x, y, z] for z in (70, 90) for x, y in ((XF + G + 1.01, YT - 0.6), (XF + G + 1.01, YT + 0.01), (XF + G + 0.4, YT + 0.01))])))
m.export("tappo_uscita.stl")
p = m.copy(); p.apply_transform(T.rotation_matrix(np.pi/2, [0, 0, 1])); p.apply_translation(-p.bounds[0]); p.export("tappo_uscita_stampa.stl")
print("tappo uscita: chiuso %s, %.2f cm3, %s, corpi %d" % (m.is_watertight, m.volume/1000, m.extents.round(2), len(m.split())))
