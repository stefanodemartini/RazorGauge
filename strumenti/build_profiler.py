# Unisce piastra modificata + colonna RazorGauge (manifold via trimesh) -> STL pezzo unico
import trimesh, numpy as np, sys
from trimesh.creation import box
src, col, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = trimesh.load(src); C = trimesh.load(col)
ENC_C = (35.0, 49.55)            # asse dell'encoder / ruota (Y, Z)
ENC_R = 26.5                     # sede del corpo encoder Ø53 (corpo Ø38): comprende le 4 finestre ad arco (r 20-26), niente pareti sottili
ENC_WALL = 3.0                   # fondo della sede = spessore della piastra originale: l'albero sporge come prima
DZ = -16.0                       # rullo inferiore + braccio spostati: centro Z -6.45 = 28.00 mm dal laser (simmetrico alla ruota)
ZE = 3.6 + DZ - 2.2              # bordo della piastra lato rullo: Z -14.6 (copre tutto il blocco guida dello spintore)
ZT = 57.7                        # bordo della piastra lato ruota: Z 57.7 (era 55.6; copre il blocco guida lato ruota)
ZS = 0.55                        # punto di misura spostato da Z 21.00 a 21.55 (interasse ruota-laser 28.00 mm)
XB = 22.22
Z_FORK = (9.55 + DZ, 49.55)              # rulli spintori (sopra il rullo inferiore spostato e sopra la ruota encoder)
SX, SZ = 16.6, 12.6              # guida della forcella ORIGINALE (ingombro 16 x 12, gioco 0.3 per lato: MJF + forcella stampata)
GW, GZ = 2.0, 8.15               # parete laterale (X) e mezza larghezza del blocco lungo il cavo
GY0, GY1, CAP = 85.0, 117.8, 6.0 # guida rettangolare CHIUSA da Y 85 (sopra rullo e bullone anche a cavo 3 + 1.5 mm); cappello come l'originale
def B(x0,x1,y0,y1,z0,z1):
    b = box([x1-x0, y1-y0, z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
U = trimesh.boolean.union; D = trimesh.boolean.difference; I = trimesh.boolean.intersection
arm    = B(3.01, 30.51, 40, 65.5, 3.0, 16.0)
holder = B(3.01, 30.51, 104, 118.5, 3.0, 16.0)
central= B(3.01, 30.31, 63.0, 70.5, 15.0, 39.0)
holder2= B(3.01, 31.0, 104, 118.5, 43.0, 56.5)          # supporto a cuneo dello spintore superiore: sostituito
rest = D([P, U([arm, holder, holder2, central])])
moved = [I([P, B(2.9, 30.51, 40, 65.5, 3.0, 16.0)])]   # solo il braccio del rullo inferiore (il supporto a cuneo e' sostituito)
for mm in moved: mm.apply_translation([0, 0, DZ])
# allargamento piastra lato rullo: Z da 3.6 a -8.9, angoli raggiati R2.5
ext = trimesh.creation.box([3, 177.9-41, 6-ZE])
ext.apply_translation([1.5, (41+177.9)/2, (6+ZE)/2])
r = 2.5
corner_cut = []
for y in (41, 177.9):
    sy = 1 if y == 41 else -1
    sq = B(-0.1, 3.1, y - (0 if sy > 0 else r), y + (r if sy > 0 else 0), ZE, ZE + r)
    cyl = trimesh.creation.cylinder(radius=r, height=3.2, sections=48)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
    cyl.apply_translation([1.5, y + sy*r, ZE + r])
    corner_cut.append(D([sq, cyl]))
ext = D([ext, U(corner_cut)])
ext_t = B(0, 3, 69.0, 177.9 - r, 55.0, ZT)                 # allargamento lato ruota fino a ZT (angolo superiore raccordato sotto)
ext = U([ext, ext_t])
# piastra prolungata in alto fino alla cima della torre (bordo superiore allineato alla torre)
Y_TOP_NEW = 177.9   # altezza originale della piastra (la torre sporge sopra)
top = B(0, 3, 170, Y_TOP_NEW - r, ZE, ZT)
top_round = []
for z in (ZE + r, ZT - r):
    cyl = trimesh.creation.cylinder(radius=r, height=3, sections=48)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
    cyl.apply_translation([1.5, Y_TOP_NEW - r, z]); top_round.append(cyl)
top_round.append(B(0, 3, Y_TOP_NEW - r - 0.01, Y_TOP_NEW, ZE + r, ZT - r))
top = U([top] + top_round)
res = U([rest] + moved + [ext, top, C])
# piastra ispessita fino al retro della colonna (X 7.22) in tutta la zona della torre (Y 76.41 - cima)
X_BACKCOL = 22.22 - 15.0
Y0 = C.bounds[0][1] if False else 76.41
thick = B(0, X_BACKCOL, Y0, Y_TOP_NEW - r, ZE, ZT)
tr = []
for z in (ZE + r, ZT - r):
    cyl = trimesh.creation.cylinder(radius=r, height=X_BACKCOL, sections=48)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
    cyl.apply_translation([X_BACKCOL/2, Y_TOP_NEW - r, z]); tr.append(cyl)
tr.append(B(0, X_BACKCOL, Y_TOP_NEW - r - 0.01, Y_TOP_NEW, ZE + r, ZT - r))
thick = U([thick] + tr)
# finestra originale: riempita (angoli R4, come l'originale)
wr = 4.0; wins = []
for (yy, zz) in [(74.9 + wr, 11.6 + wr), (74.9 + wr, 47.6 - wr), (104.8 - wr, 11.6 + wr), (104.8 - wr, 47.6 - wr)]:
    cyl = trimesh.creation.cylinder(radius=wr, height=X_BACKCOL, sections=48)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); cyl.apply_translation([X_BACKCOL/2, yy, zz]); wins.append(cyl)
window = trimesh.convex.convex_hull(trimesh.util.concatenate(wins))
res = U([res, thick, window])            # finestra originale chiusa (riempita a tutto spessore)
# fori di fissaggio alla piastra di supporto (viti M3 da davanti, lato cavo): rettangolo 48 x 36.5 simmetrico sulla
# piastra (8.5 mm da entrambi i bordi laterali Z -14.6 / 57.7, 8.4 mm dal bordo superiore), sopra gli spintori
MOUNT = [(y, z, 1.7) for y in (133.0, 169.5) for z in (ZE + 8.5, ZT - 8.5)]
holes = []
for (y, z, rr) in MOUNT:
    h = trimesh.creation.cylinder(radius=rr, height=7.6, sections=48)
    h.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); h.apply_translation([3.6, y, z]); holes.append(h)
res = D([res, U(holes)])
# --- passaggio cavi del connettore sotto la scheda: tacca aperta dal bordo inferiore della piastra (tutto lo spessore)
notch = B(-0.2, X_BACKCOL + 0.4, 40.0, 46.0, 10.5, 15.5)
nr = trimesh.creation.cylinder(radius=2.5, height=X_BACKCOL + 0.6, sections=48); nr.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); nr.apply_translation([X_BACKCOL/2, 46.0, 13.0])
res = D([res, U([notch, nr])])
# --- PIASTRA A SPESSORE UNICO: la sagoma della piastra (sezione a X 1.5, con tutti i fori e le asole) estrusa da X 0 a X 7.22
import shapely.geometry as sg, shapely.ops as so
M2 = np.array([[0,1,0,0],[0,0,1,0],[1,0,0,-1.5],[0,0,0,1]], dtype=float)
sec2d, _ = res.section(plane_origin=[1.5,0,0], plane_normal=[1,0,0]).to_2D(to_2D=M2)
PLATE2D = so.unary_union(list(sec2d.polygons_full)).buffer(0).simplify(0.02, preserve_topology=True)
def extrude_yz(poly, x0, x1):
    ms = []
    for g in (poly.geoms if hasattr(poly, "geoms") else [poly]):
        if g.area < 1: continue
        m = trimesh.creation.extrude_polygon(g, x1 - x0)
        m.apply_transform(np.array([[0,0,1,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]], dtype=float)); ms.append(m)
    return U(ms) if len(ms) > 1 else ms[0]
res = U([res, extrude_yz(PLATE2D, 0.0, X_BACKCOL)])
# sede della linguetta posteriore della slitta: si rifa nello spessore aggiunto (fondo a X 4.82 come prima)
res = D([res, B(4.82, 9.5, 58.81, 61.16, 10.25 + ZS, 24.75 + ZS)])   # gioco 0.1 sotto, 0.25 sopra e ai lati
# --- fori Ø3 originali della zona encoder e di fissaggio (Ø2.99) portati a Ø3.3: nel PA12 MJF i fori escono ~0.1 mm piu piccoli
HOLES33 = [(3.0, 18.7), (3.0, 80.4), (57.97, 80.44), (49.01, 49.53), (47.98, 42.03), (35.0, 64.53), (28.02, 61.69), (28.02, 37.42), (22.03, 42.06)]
hc = []
for (y, z) in HOLES33:
    h = trimesh.creation.cylinder(radius=1.65, height=X_BACKCOL + 1, sections=48); h.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); h.apply_translation([X_BACKCOL/2, y, z]); hc.append(h)
res = D([res, U(hc)])
# --- alleggerimento: tasche aperte sul retro della zona ispessita (pelle anteriore 2 mm, nervature 3 mm)
SKIN = 1.6; RIB = 2.2; RIM = 3.0          # alleggerimento (8/10/2026): pelle 1.6, nervature 2.2, bordo 3.0
pk_x1 = X_BACKCOL - SKIN
# tasche costruite in 2D (sezione Y-Z) e "aperte" morfologicamente: nessuna fessura o lamella sotto 1.6 mm
def rect(y0, y1, z0, z1): return sg.box(y0, z0, y1, z1)
keep2 = []
for z in (7.5 + ZS, 21.0 + ZS, 34.5 + ZS, 48.0):                       # nervature lungo Y
    keep2.append(rect(-1, Y_TOP_NEW + 1, z - RIB/2, z + RIB/2))
for y in (20.0, 50.0, 76.4, 101.0, 126.8, 150.0):                      # nervature lungo Z
    keep2.append(rect(y - RIB/2, y + RIB/2, ZE - 1, ZT + 1))
for (y, z, _) in MOUNT: keep2.append(sg.Point(y, z).buffer(4.5, 48))    # bossoli fori di fissaggio
for c in Z_FORK: keep2.append(rect(GY0 - 1, GY1 + 1, c - GZ - 1, c + GZ + 1))   # pieno sotto i blocchi guida
keep2.append(sg.Point(*ENC_C).buffer(ENC_R + 4.0, 96))                 # pieno attorno alla sede encoder
keep2.append(rect(39.0, 66.5, -11.0 + DZ + 13, 4.0 + DZ + 13))         # braccio del rullo inferiore
keep2.append(rect(47.5, 64.0, 4.0 + ZS, 27.0 + ZS))                    # sede slitta, trave, colonnina
for (y, z) in ((3.0, 18.7), (3.0, 80.4), (57.97, 80.44), (52.0, 18.67)): keep2.append(sg.Point(y, z).buffer(4.5, 48))   # fori zona encoder
KEEP2 = so.unary_union(keep2)
def opened(poly, w=0.8): return poly.buffer(-w, 32).buffer(w, 32)       # apertura con raccordi tondi: nessuna tasca piu stretta di 1.6 mm
POCK = opened(PLATE2D.buffer(-RIM, join_style=2).difference(KEEP2))
DEEP = opened(rect(Y0 + RIM, Y_TOP_NEW - RIM, 9.55 + ZS, 33.55 + ZS).intersection(PLATE2D.buffer(-RIM, join_style=2)).difference(KEEP2))
def big(poly, amin=6.0):
    gs = [g for g in (poly.geoms if hasattr(poly, "geoms") else [poly]) if g.area > amin]
    return so.unary_union(gs)
POCK, DEEP = big(POCK), big(DEEP)
pockets = U([extrude_yz(POCK, -0.1, pk_x1), extrude_yz(DEEP, -0.1, X_BACKCOL)])
res = D([res, pockets])
# --- sede del corpo dell'encoder sul retro: il fondo resta spesso come la piastra originale (3 mm)
encs = trimesh.creation.cylinder(radius=ENC_R, height=X_BACKCOL - ENC_WALL + 0.2, sections=128)
encs.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
encs.apply_translation([(X_BACKCOL - ENC_WALL - 0.2)/2, ENC_C[0], ENC_C[1]])
res = D([res, encs])
# --- blocchi guida per le forcelle ORIGINALI, inserite DAL BASSO (senza rullo): sede rettangolare chiusa 16.3 x 12.3,
#     piu stretta del rullo; il bordo inferiore resta sopra rullo e bullone; in alto il cappello del supporto originale
blocks, cuts = [], []
GTOP = GY1 - CAP                       # 111.8: il blocco finisce qui, sopra c'e il TAPPO SEPARATO (stesso spessore e foro del cappello)
TAP_X = (10.6, 33.4)                   # viti M3 del tappo (dietro: nel pieno verso la piastra; davanti: nella spalla anteriore)
LUG_Y0 = GTOP - 10.5                   # spalle per le viti del tappo, alte 10.5 mm (fondo pieno 1.9 mm sotto il foro)
for c in Z_FORK:
    blocks.append(B(XB - SX/2 - GW, XB + SX/2 + GW, GY0, GTOP, c - GZ, c + GZ))     # scatola
    blocks.append(B(X_BACKCOL - 0.3, XB - SX/2 - GW + 0.1, GY0, GTOP, c - 2.0, c + 2.0))   # anima centrale
    for sz in (-1, 1):                                                               # anime laterali
        z0, z1 = sorted((c + sz*SZ/2, c + sz*GZ))
        blocks.append(B(X_BACKCOL - 0.3, XB - SX/2 - GW + 0.1, GY0, GTOP, z0, z1))
    blocks.append(B(X_BACKCOL - 0.3, XB - SX/2 + 0.01, LUG_Y0, GTOP, c - GZ, c + GZ))     # spalla posteriore piena (vite)
    blocks.append(B(XB + SX/2 - 0.01, TAP_X[1] + 2.75, LUG_Y0, GTOP, c - GZ, c + GZ))     # spalla anteriore (vite)
    cuts.append(B(XB - SX/2, XB + SX/2, GY0 - 0.1, GTOP + 0.1, c - SZ/2, c + SZ/2)) # sede passante: la forcella entra DALL'ALTO
    for tx in TAP_X:                                                                 # fori M3 autofilettanti Ø2.5, 8.5 mm
        h = trimesh.creation.cylinder(radius=1.25, height=8.6, sections=32)
        h.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1,0,0])); h.apply_translation([tx, GTOP - 4.25, c]); cuts.append(h)
    ch = trimesh.creation.box([SX + 1.6, 1.6, SZ + 1.6]); ch.apply_translation([XB, GY0, c]); cuts.append(ch)   # invito 0.8 mm
res = D([U([res] + blocks), U(cuts)])
# --- due guide a J tra i rulli, lunghe il massimo possibile: Z 4.8-12.5 (tra rullo spintore e fascio) e Z 29.5-37.8 (tra fascio e ruota).
#     Gola larga come la guida originale lato ruota (3.0 mm, fondo tondo R1.5); fondo 0.3 mm sotto la linea
#     (la linea appoggia sempre su ruota e rullo); parete alta verso la piastra, labbro davanti, invito svasato alle due facce.
import shapely.affinity as sa
J_SPANS = ((4.8 + DZ + 13.3, 12.5 + ZS), (29.5 + ZS, 37.0))   # allungate al massimo: rullo spintore (anche senza cavo) / fascio L2 Ø14 (Z 14-28) / ruota
J_W = 3.0; J_BOT = 66.91 - 0.3; J_FLOOR0 = 65.1
def j_guide(za, zb):
    zc = (za + zb)/2; J_T = zb - za
    xb = 22.22
    outline = so.unary_union([sg.box(6.0, J_FLOOR0, xb - J_W/2 - 2.0, 69.5),                  # braccio dalla piastra
                              sg.box(xb - J_W/2 - 2.0, J_FLOOR0, xb - J_W/2, 72.0),            # parete posteriore (alta)
                              sg.box(xb - J_W/2 - 2.0, J_FLOOR0, xb + J_W/2 + 2.0, J_BOT),     # fondo sotto la gola
                              sg.box(xb + J_W/2, J_FLOOR0, xb + J_W/2 + 2.0, 69.9)])           # labbro anteriore
    groove = so.unary_union([sg.box(xb - J_W/2, J_BOT + J_W/2, xb + J_W/2, 80), sg.Point(xb, J_BOT + J_W/2).buffer(J_W/2, 64)])
    prof = outline.difference(groove).buffer(-0.5, 32).buffer(0.5, 32)                         # spigoli arrotondati R0.5
    def ext(poly, z0, z1):
        m = trimesh.creation.extrude_polygon(poly, z1 - z0); m.apply_translation([0, 0, z0]); return m
    body = ext(prof, zc - J_T/2, zc + J_T/2)
    flare = trimesh.convex.convex_hull(trimesh.util.concatenate([ext(groove, zc - 0.6, zc + 0.6),
                ext(groove.buffer(0.7, 32), zc - J_T/2 - 0.05, zc - J_T/2 + 0.05), ext(groove.buffer(0.7, 32), zc + J_T/2 - 0.05, zc + J_T/2 + 0.05)]))
    return D([body, flare])
res = U([res] + [j_guide(a, b) for (a, b) in J_SPANS])
# --- foro di fissaggio originale (Y 57.97, Z 18.67) coperto davanti dalla sede della slitta: chiuso e spostato a Y 52.0
#     (stessa Z; passante, raggiungibile dal davanti accanto alla ruota encoder e dal retro)
HOLE_OLD, HOLE_NEW = (57.97, 18.67), (52.0, 18.67)
plug = trimesh.creation.cylinder(radius=1.8, height=7.22, sections=48); plug.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); plug.apply_translation([3.61, *HOLE_OLD])
# r 1.8 > foro Ø3.3: nessun anello residuo. Tratto X 0-3.2 pieno; davanti (X 3.2-7.22) riempio solo sotto Y 58.2 per non toccare la sede della linguetta della slitta (Y 58.87-60.95)
plug = trimesh.boolean.intersection([plug, U([B(-0.1, 3.2, 50, 70, 0, 40), B(3.0, 7.22, 50, 58.2, 0, 40)])])
res = U([res, plug])
hn = trimesh.creation.cylinder(radius=1.65, height=X_BACKCOL + 1, sections=48); hn.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); hn.apply_translation([X_BACKCOL/2, *HOLE_NEW])
res = D([res, hn])
# pulizia: alette da 0.1 mm lasciate dallo spostamento del braccio del rullo inferiore (estratto da X 2.9) fuori dal contorno piastra
res = D([res, U([B(-1, 3.06, 30.0, 41.15, ZE - 3, 17.0), B(-1, 3.06, 40.0, 70.0, ZE - 3, ZE - 0.01)])])
# --- SMUSSI DI STAMPA (spigoli esterni liberi; nessun accoppiamento toccato) -----------------------------------
#  (1) angoli convessi del contorno piastra raccordati R3 (come l'originale), (2) smusso 0.6 sul perimetro esterno della faccia
#  posteriore (appoggio sulla piastra di supporto: resta piana) e della faccia anteriore dove non c'e' nulla attaccato,
#  (3) invito 0.5 sulla bocca della sede encoder, (4) smusso 0.7 sugli spigoli verticali anteriori liberi dei blocchi guida (uguale a quello dei tappi).
#  Esclusi: fori, sedi, guide, facce di battuta, tutto cio' che si accoppia.
def _sec2d(m, x):
    s, _ = m.section(plane_origin=[x,0,0], plane_normal=[1,0,0]).to_2D(to_2D=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,-x],[0,0,0,1]], dtype=float))
    return so.unary_union(list(s.polygons_full)).buffer(0)
_S = _sec2d(res, 1.5)
_E = sg.Polygon(max(getattr(_S, "geoms", [_S]), key=lambda g: g.area).exterior)
_F = _sec2d(res, X_BACKCOL + 0.4).buffer(1.0, 16)            # impronta di tutto cio' che sta sulla faccia anteriore (+1 mm)
def _ext2(poly, x0, x1):
    gs = [g for g in getattr(poly, "geoms", [poly]) if g.geom_type == "Polygon" and g.area > 1e-3]
    ms = []
    for g in gs:
        m = trimesh.creation.extrude_polygon(g, x1 - x0)
        m.apply_transform(np.array([[0,0,1,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]], dtype=float)); ms.append(m)
    return (U(ms) if len(ms) > 1 else ms[0]) if ms else None
cut = []
_Er = _E.buffer(-3.0, 64).buffer(3.0, 64)                                      # contorno con gli angoli convessi raccordati R3
_OUT = _E.buffer(0.6, 16)                                                       # le fasce partono FUORI dal pezzo: niente lamelle sul bordo
_CH, _H = 0.6, 0.1                                                              # smussi 0.6 a gradini da 0.1 (risoluzione MJF ~0.08)
_NS = int(round(_CH / _H))
m = _ext2(_OUT.difference(_Er).difference(_F), _CH - 0.013, X_BACKCOL - _CH + 0.013); cut += [m] if m is not None else []   # (1) raccordi
for i in range(_NS):
    d = _CH - (i + 0.5) * _H
    m = _ext2(_OUT.difference(_Er.buffer(-d, 32)), (-0.2 if i == 0 else i * _H - 0.013), (i + 1) * _H); cut += [m] if m is not None else []          # (2) retro
    m = _ext2(_OUT.difference(_Er.buffer(-d, 32)).difference(_F), X_BACKCOL - (i + 1) * _H, (X_BACKCOL + 0.2 if i == 0 else X_BACKCOL - i * _H + 0.013)); cut += [m] if m is not None else []   # fronte
_n = 5                                                                          # (3) invito 0.5 x 45 sulla sede del corpo encoder
for i in range(_n):
    rr = ENC_R + 0.5 - (i + 0.5) * 0.1
    c = trimesh.creation.cylinder(radius=rr, height=0.126 + (0.2 if i == 0 else 0), sections=128)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); c.apply_translation([i * 0.1 + 0.05 - (0.1 if i == 0 else 0), ENC_C[0], ENC_C[1]]); cut.append(c)
def _wedge(xc, zc, sx, sz, y0, y1, L=1.0):                                     # prisma triangolare lungo Y sullo spigolo (xc, zc)
    tri = sg.Polygon([(xc + 0.3*sx, zc + 0.3*sz), (xc - L*sx, zc + 0.3*sz), (xc + 0.3*sx, zc - L*sz)])
    w = trimesh.creation.extrude_polygon(tri, y1 - y0)                        # piano (X, Z), estrusione lungo +Y
    w.apply_transform(np.array([[1,0,0,0],[0,0,1,y0],[0,1,0,0],[0,0,0,1]], dtype=float))
    if w.volume < 0: w.invert()
    return w
for c in Z_FORK:                                                                # (4) spigoli verticali anteriori dei blocchi guida
    for sz in (-1, 1):
        cut.append(_wedge(XB + SX/2 + GW, c + sz*GZ, 1, sz, GY0 - 0.2, LUG_Y0 + 0.01))
        cut.append(_wedge(TAP_X[1] + 2.75, c + sz*GZ, 1, sz, LUG_Y0 - 0.01, GTOP + 0.2))
res = D([res, U(cut)])
parts = res.split(only_watertight=False)
res = max(parts, key=lambda p: p.volume)   # scarta eventuali schegge a volume nullo
import io
def _reloaded(m):
    buf = io.BytesIO(); m.export(buf, file_type="stl"); buf.seek(0); return trimesh.load(buf, file_type="stl")
for dig in (5, 4, 6, 3):                                     # scelgo la tolleranza di fusione che da' un STL chiuso dopo l'export
    t = res.copy(); t.merge_vertices(digits_vertex=dig); t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()
    r2 = _reloaded(t)
    if r2.is_watertight and r2.is_volume and len(r2.split(only_watertight=False)) == 1:
        res = t; break
res.export(out)
print("watertight", res.is_watertight, "volume cm3 %.1f" % (res.volume/1000), "bounds", res.bounds.round(2).tolist(), "corpi", len(res.split(only_watertight=False)))
