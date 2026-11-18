# Piastrina girevole che copre la gola d'ingresso lato ruota (31/10/2026, sostituisce il tappino a incastro).
# Appoggia sul braccio (Y 69.9), gira attorno al perno PU_PIV (05/11/2026: perno stampato Ø4 nel braccio + vite M2 x 5 e rondella Ø6: foro Ø4.3).
# Chiusa (0 gradi): si allunga verso il fronte e copre la gola X 20.42-24.02 (soffitto a Y 69.9). Aperta: ruotata di 90 gradi
# verso -Z, sta sopra il braccio pieno e la gola resta libera. Dente sotto (r 0.6, alto 0.35) negli incavi del braccio.
# Uscita: piastrina_ingresso.stl (chiusa, coordinate piastra), piastrina_ingresso_aperta.stl, piastrina_ingresso_stampa.stl.
import trimesh, numpy as np, shapely.geometry as sg
T = trimesh.transformations
U = lambda m: trimesh.boolean.union(m, engine="manifold"); D = lambda a, b: trimesh.boolean.difference([a, b], engine="manifold")
PIV = (13.5, 80.0); Y0 = 69.9; TH = 1.8
DET = (18.5, 80.0)                                          # dente (chiusa)
shape = sg.Point(PIV[0], PIV[1]).buffer(3.5, 64).union(sg.Point(25.0, PIV[1]).buffer(2.6, 64)).convex_hull   # da perno a oltre la gola
shape = shape.difference(sg.Point(PIV[0], PIV[1]).buffer(2.15, 64))                                          # 05/11/2026: foro Ø4.3 sul perno stampato Ø4.0
def ext_xz(poly, y0, y1):                                   # poligono nel piano (X, Z) estruso lungo Y
    m = trimesh.creation.extrude_polygon(poly, y1 - y0)
    m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
    if m.volume < 0: m.invert()
    return m
m = ext_xz(shape, Y0 + 0.02, Y0 + TH)
# presa: nervatura in cima vicino all'estremita' (si spinge con un dito)
m = U([m, ext_xz(sg.box(23.6, PIV[1] - 2.0, 24.8, PIV[1] + 2.0), Y0 + TH - 0.01, Y0 + TH + 1.0)])
# dente di scatto sotto
d = trimesh.creation.icosphere(subdivisions=3, radius=0.6); d.apply_translation([DET[0], Y0 + 0.02 + 0.6 - 0.35, DET[1]])
d = trimesh.boolean.intersection([d, trimesh.creation.box(bounds=[[DET[0] - 1, Y0 - 0.5, DET[1] - 1], [DET[0] + 1, Y0 + 0.05, DET[1] + 1]])], engine="manifold")
m = U([m, d])
# 05/11/2026: smusso 0.4 sotto il foro (spazio per il raccordo alla base del perno stampato)
_c = trimesh.creation.cylinder(radius=1.0, height=1.0, sections=64); _v = _c.vertices.copy(); _t = _v[:, 2] > 0
_v[:, :2] *= np.where(_t, 2.15, 2.6)[:, None]; _v[:, 2] = np.where(_t, Y0 + 0.47, Y0 - 0.1); _c = trimesh.Trimesh(_v, _c.faces); _c.fix_normals()
_c.apply_transform(T.rotation_matrix(-np.pi/2, [1, 0, 0])); _c.apply_translation([PIV[0], 0, PIV[1]]); m = D(m, _c)
m.export("piastrina_ingresso.stl")
o = m.copy(); o.apply_transform(T.rotation_matrix(np.radians(90), [0, 1, 0], point=[PIV[0], 0, PIV[1]])); o.export("piastrina_ingresso_aperta.stl")
p = m.copy(); p.apply_translation(-p.bounds[0]); p.export("piastrina_ingresso_stampa.stl")
print("piastrina: chiusa %s, %.2f cm3, %s, corpi %d; aperta Z %.1f-%.1f X %.1f-%.1f" % (m.is_watertight, m.volume/1000, m.extents.round(2), len(m.split()), o.bounds[0][2], o.bounds[1][2], o.bounds[0][0], o.bounds[1][0]))
