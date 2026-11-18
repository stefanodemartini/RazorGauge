# Unisce piastra modificata + colonna RazorGauge (manifold via trimesh) -> STL pezzo unico
import trimesh, numpy as np, sys
from trimesh.creation import box
src, col, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = trimesh.load(src); C = trimesh.load(col)
ENC_C = (35.0, 49.55)            # asse dell'encoder / ruota (Y, Z)
ENC_R = 26.5                     # sede del corpo encoder Ø53 (corpo Ø38): comprende le 4 finestre ad arco (r 20-26), niente pareti sottili
ENC_WALL = 3.0                   # fondo della sede = spessore della piastra originale: l'albero sporge come prima
ENC_FR = 18.8                    # 02/11/2026 da 19.0: anello verso le finestre ad arco da 0.93 a 1.13 mm (PolyD: pareti >= 1 mm).
                                 # tasca anteriore Ø38 (30/10/2026): teste viti encoder (r 14-15 + 2.75, margine 1.25) e mozzo Ø29 della ruota originale.
                                 # NON r 20 (raggio interno delle 4 finestre ad arco r 20-26: superfici coincidenti = lamelle nell'STL) e non 21-23
                                 # (il cerchio taglia gli spigoli delle finestre di sbieco: cunei 0.05-0.4 mm). Con 19: anello pieno 1.0 mm verso le finestre.
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
# sede della linguetta posteriore della slitta v2 (28/10/2026): fondo a filo della mensola (Y 58.11 = riferimento),
# linguetta 2.0 x 12 (Z 11.55-23.55) -> sede 2.25 x 12.5, profonda fino a X 4.72 (0.1 oltre la punta)
TR_Y0 = 58.11
res = D([res, B(4.72, 9.0, TR_Y0 - 0.3, TR_Y0 + 2.25, 11.35, 23.75)])   # gioco laterale della linguetta 0.2 (02/11/2026, linee guida PolyD; 31/10 era 0.15, prima 0.25)
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
keep2.append(rect(44.0, 64.0, 1.0, 31.0))                              # mensola della slitta v2 (28/10/2026)
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
# --- zona encoder (30/10/2026, ristampa): fondo riportato a X 0-3 COME NEL FLYLINEPROFILER ORIGINALE, encoder appoggiato
#     al retro del pezzo (X 0, corpo nel foro Ø42 della piastra in alluminio). Cosi' vanno bene ENTRAMBE le ruote:
#     - ruota originale (Decoder+Ruota.stl): mozzo Ø29 a 1.6 mm dal codolo come nell'originale -> cerchio X 17.84-27.84
#     - ruota CNC RG_ruota_encoder: cerchio X 17.22-27.22 = 10.0 mm dalla faccia anteriore del pezzo (X 7.22), come da disegno
#     Davanti: tasca Ø40 da X 7.22 a X 3.0 per le teste delle 3 viti M3 dell'encoder e il mozzo Ø29 della ruota originale.
#     (prima: sede Ø53 sul retro profonda 4.22 -> encoder e albero 4.22 mm piu' avanti, ruota originale fuori centro di ~5 mm)
encs = trimesh.creation.cylinder(radius=ENC_FR, height=X_BACKCOL - ENC_WALL + 0.2, sections=128)
encs.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
encs.apply_translation([(X_BACKCOL + ENC_WALL + 0.2)/2, ENC_C[0], ENC_C[1]])
res = D([res, encs])
# finestre ad arco (r 20-26) passanti su tutto lo spessore: la mensola (da X 2.82) ne riempiva un angolo -> gradino a X 2.82
_win = [sg.Polygon(r) for g in (PLATE2D.geoms if hasattr(PLATE2D, "geoms") else [PLATE2D]) for r in g.interiors
        if 19.5 < sg.Polygon(r).centroid.distance(sg.Point(*ENC_C)) < 24.5 and sg.Polygon(r).area > 50]
print("finestre encoder:", len(_win))
# 03/11/2026 (Stefano: confronto col foro Ø42 della piastra CNC): le finestre originali r 20-26 cadevano dentro il foro Ø42 solo per
#     1 mm -> da dietro 4 fessure a mezzaluna e il resto chiuso dall'alluminio. Servono solo a risparmiare materiale: richiuse e rifatte
#     FUORI dal foro (r 21.5-27.3, stessi settori angolari, angoli raccordati R1): niente fessure, risparmio uguale (4.2 cm3 contro 4.1),
#     davanti aperte, il fondo e' la piastra in alluminio. Lontane dalla base della mensola (Y 44-64, Z 1-31) di almeno 1 mm.
res = U([res, extrude_yz(so.unary_union(_win).buffer(0.05, 16), 0.0, X_BACKCOL)])          # finestre originali richiuse
_cy, _cz = ENC_C
_ring = sg.Point(_cy, _cz).buffer(27.3, 256).difference(sg.Point(_cy, _cz).buffer(21.5, 256))
_nw = []
for _w in _win:
    _p = np.array(_w.exterior.coords); _a = np.arctan2(_p[:, 1] - _cz, _p[:, 0] - _cy)
    if _a.max() - _a.min() > np.pi: _a = np.where(_a < 0, _a + 2*np.pi, _a)
    _A = np.linspace(_a.min(), _a.max(), 90)
    _sec = sg.Polygon([(_cy, _cz)] + [(_cy + 40*np.cos(t), _cz + 40*np.sin(t)) for t in _A])
    _nw.append(_sec.intersection(_ring))
_NW = so.unary_union(_nw).difference(sg.box(44.0 - 1.0, 1.0 - 1.0, 64.0 + 1.0, 31.0 + 1.0)).buffer(-1.0, 32).buffer(1.0, 32)
print("finestre encoder rifatte: area %.0f mm2" % _NW.area)
res = D([res, extrude_yz(_NW, -0.1, X_BACKCOL)])
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
    # (invito 0.8 sul bordo inferiore della sede tolto il 30/10/2026: la forcella entra dall'alto e lasciava 0.2 mm alle linguette anti-gioco)
res = D([U([res] + blocks), U(cuts)])
# --- 30/10/2026 (Stefano: forcelle troppo lasche, vibrano al passaggio della coda di topo): LINGUETTE ELASTICHE ANTI-GIOCO.
#     La forcella e' guidata solo nel tratto basso della sede (prisma 16 x 12 in sede per 4-6 mm) con 0.3 mm per lato.
#     In ogni blocco due linguette ricavate nelle pareti (anteriore X+ e laterale esterna Z) con un dente che entra di
#     FLX_BUMP nella sede: la forcella e' spinta contro la parete posteriore e quella interna -> gioco zero anche con le
#     tolleranze MJF. Linguetta spessa FLX_T, libera in basso (Y 85), lunga FLX_L, larga FLX_W; dente a rampa (invito dall'alto).
FLX_T, FLX_L, FLX_GAP, FLX_BUMP, FLX_BUMP_Z = 1.0, 14.0, 0.6, 0.7, 0.6   # interferenza 0.4 (X) e 0.3 (Z) col gioco nominale 0.3
FLX_Y0, FLX_Y1 = GY0, GY0 + FLX_L
FLX_BY = (GY0 + 0.2, GY0 + 0.8, GY0 + 1.6, GY0 + 3.6)          # dente vicino all estremita libera: rampa bassa / piano / piano / rampa alta (invito)
# (il prisma della forcella entra nella sede da 1.75 mm senza cavo a 6 mm con cavo 3 + 2)
FLX_ZSIDE = {Z_FORK[0]: -1, Z_FORK[1]: +1}                       # parete Z esterna (lontana dalla torre)
def _bump(pts_in, pts_out):                                       # prisma a rampa: profilo (u=Y, v=sporgenza) estruso
    return trimesh.convex.convex_hull(np.array(pts_in + pts_out))
flx_cut, flx_add = [], []
for c in Z_FORK:
    # parete anteriore (X+): linguetta larga 7 lungo Z, spinge la forcella verso la piastra
    w = 7.0; xi = XB + SX/2                                       # faccia interna della parete anteriore
    for s in (-1, 1): flx_cut.append(B(xi - 0.05, xi + GW + 0.05, FLX_Y0 - 1.0, FLX_Y1, c + s*w/2 + (0 if s > 0 else -FLX_GAP), c + s*w/2 + (FLX_GAP if s > 0 else 0)))
    flx_cut.append(B(xi + FLX_T, xi + GW + 0.05, FLX_Y0 - 1.0, FLX_Y1, c - w/2, c + w/2))          # assottiglia a FLX_T
    y0, y1, y2, y3 = FLX_BY; zz = (c - w/2 + 0.3, c + w/2 - 0.3)
    flx_add.append(_bump([[xi + 0.3, y, z] for y in (y0, y3) for z in zz], [[xi - FLX_BUMP, y, z] for y in (y1, y2) for z in zz]))
    # parete Z esterna: linguetta larga 9 lungo X, spinge la forcella verso la parete interna
    w = SX - 2*FLX_GAP; s0 = FLX_ZSIDE[c]; zi = c + s0*SZ/2; zo = c + s0*GZ     # larga quanto la sede: il dente deve toccare i BRACCI della forcella
    for s in (-1, 1): flx_cut.append(B(XB + s*w/2 + (0 if s > 0 else -FLX_GAP), XB + s*w/2 + (FLX_GAP if s > 0 else 0), FLX_Y0 - 1.0, FLX_Y1, min(zi, zo) - 0.05, max(zi, zo) + 0.05))
    zt = zi + s0*FLX_T
    flx_cut.append(B(XB - w/2, XB + w/2, FLX_Y0 - 1.0, FLX_Y1, min(zt, zo) - (0.05 if s0 < 0 else 0), max(zt, zo) + (0.05 if s0 > 0 else 0)))
    for xx in ((XB - w/2 + 0.3, XB - 4.7), (XB + 4.7, XB + w/2 - 0.3)):          # due denti, sui due bracci (X 14.2-16.2 e 28.2-30.2)
        flx_add.append(_bump([[x, y, zi + s0*0.3] for y in (y0, y3) for x in xx], [[x, y, zi - s0*FLX_BUMP_Z] for y in (y1, y2) for x in xx]))
res = U([D([res, U(flx_cut)])] + flx_add)
# --- 30/10/2026 (Stefano: il chip vede la luce ambiente dalla fessura frontale di carico della coda di topo):
#     GUIDE A T per lo SPORTELLINO FRONTALE scorrevole (strumenti/build_sportello.py), sul fronte dei due blocchi guida,
#     verticali da Y 86 a 111.8, a Z = blocco -/+ 6.0 (lontano dalle viti dei tappi e dalla linguetta anti-gioco).
#     Testa con 2 incavi di scatto (chiuso / aperto +13 mm) sulla faccia anteriore; piede in basso = fermo dello sportellino.
SH_Z = (Z_FORK[0] - 6.0, Z_FORK[1] + 6.0)
SH_Y0, SH_Y1 = 86.0, GTOP
SH_HEAD_X, SH_STEM_X = (38.0, 39.5), 38.0
SH_DET_Y = (89.6, 89.6 + 13.0)
rails, rcut = [], []
for z in SH_Z:
    rails.append(B(XB + SX/2 + GW - 0.1, SH_STEM_X + 0.01, SH_Y0, SH_Y1, z - 1.5, z + 1.5))      # anima
    rails.append(B(SH_HEAD_X[0], SH_HEAD_X[1], SH_Y0, SH_Y1, z - 3.0, z + 3.0))                  # testa
    rails.append(B(36.6, SH_HEAD_X[1], SH_Y0, SH_Y0 + 1.5, z - 4.4, z + 4.4))                    # piede (fermo in basso)
    for yd in SH_DET_Y:                                                       # incavi di scatto a fianchi inclinati 30 gradi (31/10/2026: a spigolo vivo
        _x0, _x1 = SH_HEAD_X[1] - 0.35, SH_HEAD_X[1] + 0.1                     #  servivano ~1.6 N per nottolino e lo spigolo poteva puntare). 02/11: passanti su tutta la testa (prima +/-2.2: ai lati restavano pareti da 0.8)
        rcut.append(trimesh.convex.convex_hull(np.array([[_x0, yd + dy, zz] for dy in (-0.4, 0.4) for zz in (z - 3.1, z + 3.1)] +
                                                          [[_x1, yd + dy, zz] for dy in (-1.26, 1.26) for zz in (z - 3.1, z + 3.1)])))
    rcut.append(_bump([[SH_HEAD_X[1] + 0.1, SH_Y1 + 0.1, zz] for zz in (z - 3.1, z + 3.1)] + [[SH_HEAD_X[1] - 0.6, SH_Y1 + 0.1, zz] for zz in (z - 3.1, z + 3.1)],
                      [[SH_HEAD_X[1] + 0.1, SH_Y1 - 1.5, zz] for zz in (z - 3.1, z + 3.1)]))     # smusso in cima alla testa (invito del nottolino)
res = D([U([res] + rails), U(rcut)])
# --- due guide a J tra i rulli, lunghe il massimo possibile: Z 4.8-12.5 (tra rullo spintore e fascio) e Z 29.5-37.8 (tra fascio e ruota).
#     Gola larga come la guida originale lato ruota (3.0 mm, fondo tondo R1.5); fondo 0.3 mm sotto la linea
#     (la linea appoggia sempre su ruota e rullo); parete alta verso la piastra, labbro davanti, invito svasato alle due facce.
import shapely.affinity as sa
J_SPANS = ((4.8 + DZ + 13.3, 12.5 + ZS), (29.5 + ZS, 37.0))   # allungate al massimo: rullo spintore (anche senza cavo) / fascio L2 Ø14 (Z 14-28) / ruota
J_W = 3.0; J_BOT = 66.91 - 0.3; J_FLOOR0 = 65.1
J_FLOOR_LOW = 63.5; J_BOARD_Z0 = 21.55 - 12.0   # fondo rialzato (0.3 sopra la scheda, Y 63.21); bordo scheda lato rullo Z 9.55
def j_guide(za, zb):
    zc = (za + zb)/2; J_T = zb - za
    xb = 22.22
    outline = so.unary_union([sg.box(6.0, J_FLOOR0, xb - J_W/2 - 2.0, 69.5),                  # braccio dalla piastra
                              sg.box(xb - J_W/2 - 2.0, J_FLOOR0, xb - J_W/2, 72.0),            # parete posteriore (alta)
                              sg.box(xb - J_W/2 - 2.0, J_FLOOR0, xb + J_W/2 + 2.0, J_BOT + J_W/2),   # fondo sotto la gola (fino al centro del raggio: fondo davvero tondo R1.5)
                              sg.box(xb + J_W/2, J_FLOOR0, xb + J_W/2 + 2.0, 69.9)])           # labbro anteriore
    groove = so.unary_union([sg.box(xb - J_W/2, J_BOT + J_W/2, xb + J_W/2, 80), sg.Point(xb, J_BOT + J_W/2).buffer(J_W/2, 64)])
    prof = outline.difference(groove).buffer(-0.5, 32).buffer(0.5, 32)                         # spigoli arrotondati R0.5
    def ext(poly, z0, z1):
        m = trimesh.creation.extrude_polygon(poly, z1 - z0); m.apply_translation([0, 0, z0]); return m
    body = ext(prof, zc - J_T/2, zc + J_T/2)
    # 30/10/2026: l'invito era UN solo inviluppo convesso tra le due facce -> la gola era allargata di 0.7 mm su TUTTA la
    # lunghezza e il fondo era sceso a 0.81 mm (segnalato dall'utente). Ora: invito solo negli ultimi 1.5 mm di ogni faccia,
    # e solo di lato e verso l'alto (il fondo della gola non scende mai sotto J_BOT).
    fl = groove.buffer(0.7, 32).intersection(sg.box(0, J_BOT, 60, 90))
    flares = [trimesh.convex.convex_hull(trimesh.util.concatenate([ext(groove, zf - s*1.5 - 0.05, zf - s*1.5 + 0.05),
                ext(fl, zf - 0.05, zf + 0.05)])) for zf, s in ((zc - J_T/2, -1), (zc + J_T/2, 1))]
    # fondo ispessito dove sotto non c'e' niente: rialzo da J_FLOOR0 a J_FLOOR_LOW (dalla piastra X 6 fino al labbro)
    under = []
    zl0, zl1 = za, zb
    if zb < 20:                                    # guida lato rullo: solo fuori dalla scheda e dalla sua corsa di estrazione (Z >= 9.55)
        zl1 = min(zb, J_BOARD_Z0 - 0.55)
        if zl1 > za + 1: under.append(B(6.0, xb + J_W/2 + 2.0, J_FLOOR_LOW, J_FLOOR0 + 0.5, za, zl1))
    else:                                          # guida lato ruota: segue la ruota con 1.5 mm di gioco radiale
        blk = B(6.0, xb + J_W/2 + 2.0, J_FLOOR_LOW, J_FLOOR0 + 0.5, za, zb)
        wc = trimesh.creation.cylinder(radius=200/(2*np.pi) + 1.5, height=40, sections=256)
        wc.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0])); wc.apply_translation([20, 35.0, 49.55])
        under.append(D([blk, wc]))
    return D([U([body] + under), U(flares)])
res = U([res] + [j_guide(a, b) for (a, b) in J_SPANS])
# --- foro di fissaggio originale (Y 57.97, Z 18.67) coperto davanti dalla sede della slitta: chiuso e spostato a Y 52.0
#     (stessa Z; passante, raggiungibile dal davanti accanto alla ruota encoder e dal retro)
HOLE_OLD, HOLE_NEW = (57.97, 18.67), (52.0, 18.67)
plug = trimesh.creation.cylinder(radius=1.8, height=7.22, sections=48); plug.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); plug.apply_translation([3.61, *HOLE_OLD])
# r 1.8 > foro Ø3.3: nessun anello residuo. Tratto X 0-3.2 pieno; davanti (X 3.2-7.22) riempio solo sotto Y 58.2 per non toccare la sede della linguetta della slitta (Y 58.87-60.95)
plug = trimesh.boolean.intersection([plug, B(-0.1, 7.22, 50, 70, 0, 40)])   # 04/11/2026: foro richiuso tutto (prima restava una tasca 1.5 mm dietro la sede
res = U([res, plug])                                                          #   della linguetta e un rialzo 0.19 sul suo fondo) e sede della linguetta ritagliata:
res = D([res, B(4.72, 9.0, TR_Y0 - 0.3, TR_Y0 + 2.25, 11.35, 23.75)])         #   stessa sede di riga 104 (gioco 0.2)
hn = trimesh.creation.cylinder(radius=1.65, height=X_BACKCOL + 1, sections=48); hn.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); hn.apply_translation([X_BACKCOL/2, *HOLE_NEW])
res = D([res, hn])
# 05/11/2026 (Stefano, stampa anche presso JLC3DP: tolleranza +/-0.4% oltre 100 mm): gli 8 fori delle viti M3 x 12 pezzo -> piastra
#     in alluminio portati a Ø3.6 (prima 3.3-3.4): +/-0.15 di recupero per lato sull'interasse (fino a 166 mm tra i fori estremi).
FIX8 = [(y, z) for (y, z, _) in MOUNT] + [(3.0, 18.7), (3.0, 80.4), (57.97, 80.44), HOLE_NEW]
_f8 = []
for (y, z) in FIX8:
    h = trimesh.creation.cylinder(radius=1.8, height=X_BACKCOL + 0.4, sections=64); h.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); h.apply_translation([X_BACKCOL/2, y, z]); _f8.append(h)
res = D([res, U(_f8)])
# 28/10/2026: la mensola della slitta copre il foro: canale Ø6.5 per la vite e il cacciavite, da X 7.22 al fronte della mensola
bore = trimesh.creation.cylinder(radius=3.25, height=35, sections=48); bore.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); bore.apply_translation([7.22 + 17.5, *HOLE_NEW])
bore_open = B(7.22, 42.5, HOLE_NEW[0] - 3.25, HOLE_NEW[0] + 3.25, HOLE_NEW[1], 34.0)   # canale aperto verso la ruota: niente lamelle tra canale e scarico ruota
bore_open = U([bore_open, B(12.0, 42.5, 46.9, HOLE_NEW[0] - 3.25 + 0.01, HOLE_NEW[1], 34.0)])   # 30/10/2026: sotto il canale, lato ruota, restava un cuneo 0.15-0.4 mm tra canale e scarico ruota
res = D([res, U([bore, bore_open])])
# 31/10/2026: FORO D'INGRESSO della coda di topo prima della ruota (03/11: era chiamato 'di uscita'; la coda di topo ENTRA da qui, lato ruota Z+) (blocco ORIGINALE, Z 78.5-83.4): era 3.0 x 2.8 (Y 65.6-68.4) ->
#     la Ø3 passava schiacciata e strisciando, la Ø2 toccava il soffitto se dritta. Allargato a 3.6 x 3.7 (Y 65.3-69.0, pareti
#     0.9 sopra / 1.4 sotto), spigoli lungo Z R0.6, fondo a rampa dall'interno, smusso all'imbocco (niente invito sul soffitto: con 0.9 di parete lascerebbe un filo).
# 03/11/2026 (Stefano: la gola della mensola d'ingresso non era uniforme): prima c'erano la gola originale larga 3.0 (Z 60.5-78.5),
#     il foro allargato a 3.6 solo sotto Y 69.0 (Z 69-83: sotto le pareti restava uno sbalzo), il fondo con due pendenze e un gradino
#     di 0.05 dove era stato tolto il soffitto. Ora: riempita e rifatta come UNA gola sola, aperta in alto per tutta la lunghezza,
#     larga 3.6 (X 20.42-24.02), spigoli del fondo R0.6, fondo con una pendenza unica dall'inizio del fondo (Y 66.78 a Z 62.6, come l'originale) alla fine del
#     braccio (Y 65.30 a Z 83.43), invito all'imbocco (0.4 per lato e sotto negli ultimi 0.8 mm).
GW2 = 1.8
def _gfloor(z): return 66.78 + (65.30 - 66.78) * (z - 62.6) / (83.43 - 62.6)   # a Z 62.6 come l'originale (sotto il fondo resta >= 1 mm)
def _gring(hw, y0, z, r=0.6):
    pr = sg.box(XB - hw, y0, XB + hw, 72.5).buffer(-r, 16).buffer(r, 16)
    return np.array([[x, y, z] for x, y in pr.exterior.coords])
res = U([res, B(XB - 2.05, XB + 2.05, 65.2, 69.91, 66.5, 83.43)])                  # riempimento (sopra il fondo pieno: Z >= 66.5)
_ch = [trimesh.convex.convex_hull(np.vstack([_gring(GW2, _gfloor(59.5), 59.5), _gring(GW2, _gfloor(84.5), 84.5)])),   # gola unica
       trimesh.convex.convex_hull(np.vstack([_gring(GW2, _gfloor(82.93), 82.93), _gring(GW2 + 0.4, _gfloor(83.73) - 0.4, 83.73, 1.0)]))]   # invito
res = D([res, U(_ch)])
# 31/10/2026 (Stefano: la copertura della gola d'ingresso a sinistra trattiene la coda di topo durante la scansione ma spesso
#     e' un problema; il tappino a incastro era troppo complicato): PIASTRINA GIREVOLE. Tolto il soffitto della gola (Z 77.8 - fine):
#     gola aperta in alto per tutta la lunghezza. Sopra il braccio una piastrina (strumenti/build_piastrina_ingresso.py) gira su una
#     perno (05/11: stampato Ø4 + vite M2, prima vite a spalla M3 in un inserto): chiusa copre la gola (soffitto a Y 69.9), ruotata di
#     90 gradi verso l'interno lascia la gola libera. Due scatti (dente sotto la piastrina, due incavi nel braccio).
PU_PIV = (13.5, 80.0)                                                       # perno (X, Z) sul braccio pieno, accanto alla gola
PU_DET = ((18.5, 80.0), (13.5, 75.0))                                       # incavi di scatto: chiusa / aperta
# 31/10/2026: borchia cilindrica attorno all inserto del perno (r 4.6, Y 63.8-69.9, come il foro passante): verso la fine del pezzo (Z 83.43) la parete
#     era 1.4 mm, ora 2.6 (sporge fino a Z 84.6, sotto la piastrina, dentro il contorno della piastra in alluminio Z <= 92).
# 01/11/2026 (Stefano): la faccia di testa del braccio d'ingresso (Z 83.43) aveva gli spigoli vivi, mentre gli spigoli lungo Z del braccio
#     sono raccordati R0.5: smusso 0.5 (03/11: ora raccordo tondo R0.5, vedi sotto) sul perimetro della faccia di testa del braccio, gola compresa, tranne lo
#     spigolo sulla faccia posteriore (X 0, appoggio sulla piastra: vivo); anche la borchia del perno ha gli spigoli smussati 0.5.
_ZA = 83.43
_s = res.section(plane_origin=[0, 0, _ZA - 1.0], plane_normal=[0, 0, 1]); _pl, _ = _s.to_2D(to_2D=np.eye(4))
_arm = so.unary_union(list(_pl.polygons_full)).buffer(0).intersection(sg.box(-1.0, 63.0, 30.0, 70.5))
_armx = so.unary_union([_arm, sg.box(-5.0, 55.0, 0.3, 75.0),          # faccia posteriore (X 0, in appoggio sulla piastra): spigolo VIVO
                        sg.box(-5.0, 55.0, 8.0, 64.0),                # blocco sotto il braccio (contorno della piastra): invariato
                        sg.box(20.40, 63.0, 24.04, 71.0)])            # gola (anche sotto: il fondo all'imbocco resta >= 1.0 mm): ha gia' il suo smusso d'imbita (sotto il fondo resterebbero 0.45 mm)
# 03/11/2026 (Stefano: gli smussi del braccio non erano tutti uguali, preferisce quello dell'STL originale): al posto dello smusso
#     a gradini 0.5 la testata (Z 83.43) ha un RACCORDO TONDO R0.5 come gli spigoli lungo Z del braccio originale (sfera R0.5 fatta
#     scorrere sul profilo: minkowski). Stesse esclusioni di prima (faccia posteriore X 0-1, blocco sotto, gola con il suo invito).
import manifold3d as _mf
def _to_mf(t): return _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def _to_tm(m):
    mm = m.to_mesh(); t = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False); return t
_RA = 0.5
_core = []
for _q in getattr(_armx.buffer(-_RA + 0.02, 32), "geoms", [_armx.buffer(-_RA + 0.02, 32)]):
    if _q.geom_type == "Polygon" and _q.area > 1e-3:
        _m = trimesh.creation.extrude_polygon(_q, 3.0 - _RA + 0.003); _m.apply_translation([0, 0, _ZA - 3.0]); _core.append(_m)
_rnd = _to_mf(_core[0])
for _m in _core[1:]: _rnd = _rnd + _to_mf(_m)
_rnd = _to_tm(_rnd.minkowski_sum(_mf.Manifold.sphere(_RA, 48)))      # +0.02 di lato: il raccordo non intacca le facce laterali
_reg = trimesh.creation.extrude_polygon(sg.box(1.0, 63.0, 30.0, 70.5), _RA + 0.6); _reg.apply_translation([0, 0, _ZA - _RA - 0.05])
res = D([res, D([_reg, _rnd])])
# spigoli alti della gola (aperta per tutta la lunghezza): raccordo R0.5 come gli altri spigoli lungo Z del braccio
_gq = []
for _xc, _sx in ((XB - GW2, 1), (XB + GW2, -1)):          # _sx: verso la gola (03/11: il segno era invertito, il raccordo non tagliava)
    _sq = sg.box(min(_xc, _xc - _sx*_RA), 69.91 - _RA, max(_xc, _xc - _sx*_RA), 69.91 + 0.1)
    _sq = so.unary_union([_sq, sg.box(min(_xc, _xc + _sx*0.05), 69.91 - _RA, max(_xc, _xc + _sx*0.05), 69.91 + 0.1)])
    _q = _sq.difference(sg.Point(_xc - _sx*_RA, 69.91 - _RA).buffer(_RA, 64))
    _m = trimesh.creation.extrude_polygon(_q, _ZA + 0.5 - 60.0); _m.apply_translation([0, 0, 60.0]); _gq.append(_m)   # 03/11: per tutta la gola
res = D([res, U(_gq)])
# borchia del perno: spigoli sopra e sotto con raccordo R0.5 (prima smusso dritto 0.5)
_boss = _to_tm(_mf.Manifold.cylinder(6.1 - 2*_RA, 4.6 - _RA, 4.6 - _RA, 96, True).minkowski_sum(_mf.Manifold.sphere(_RA, 48)))
_boss.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
_boss.apply_translation([PU_PIV[0], 69.9 - 3.05, PU_PIV[1]]); res = U([res, _boss])
# 02/11/2026 (PolyD: parti sotto 1 mm): alla fine del braccio d'ingresso, verso la ruota (Z 60.6-62.6) il fondo della gola, tra la gola e lo scarico
#     della ruota, era spesso 0.5-1.0 mm. Tolto: li' la coda di topo appoggia ancora sulla ruota; il fondo comincia a Z 62.6 (1.0 mm)
#     con un invito sullo spigolo d'ingresso.
_gf = trimesh.convex.convex_hull(np.array([[x, y, z] for x in (XB - GW2, XB + GW2) for (y, z) in ((60.0, 58.0), (67.6, 58.0), (67.6, 63.2), (66.3, 62.6), (60.0, 62.6))]))
res = D([res, _gf])
_pu = []                                                                     # 03/11: soffitto gia' tolto dalla gola unica
# 05/11/2026: niente piu' inserto nel braccio (borchia piena): perno stampato, vedi sotto
for dx, dz in PU_DET:
    s_ = trimesh.creation.icosphere(subdivisions=3, radius=0.75); s_.apply_translation([dx, 69.9 + 0.25, dz]); _pu.append(s_)   # incavo 0.5 profondo
res = D([res, U(_pu)])
# 05/11/2026 (Stefano: niente vite a spalla): PERNO STAMPATO della piastrina, tutt'uno con la borchia: Ø4.0 alto 2.0 sopra il
#     braccio (Y 69.9-71.9), raccordo ~0.3 alla base, smusso 0.2 in cima; foro Ø1.7 profondo 6 per una vite M2 x 5 autofilettante
#     che con una rondella M2 larga (Ø6, DIN 9021) si stringe sulla testa del perno e trattiene la piastrina (foro Ø4.3) con 0.2 di gioco.
def _cylY(r0, r1, y0, y1, sec=64):
    a = trimesh.creation.cylinder(radius=1.0, height=1.0, sections=sec); v = a.vertices.copy(); top = v[:, 2] > 0
    v[:, :2] *= np.where(top, r1, r0)[:, None]; v[:, 2] = np.where(top, y1, y0); a = trimesh.Trimesh(v, a.faces); a.fix_normals()
    a.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0])); a.apply_translation([PU_PIV[0], 0, PU_PIV[1]]); return a
_pin = U([_cylY(2.0, 2.0, 69.8, 71.7), _cylY(2.0, 1.8, 71.7, 71.9), _cylY(2.32, 2.0, 69.85, 70.22)])
res = U([res, _pin])
res = D([res, _cylY(0.85, 0.85, 65.9, 72.5, 32)])
# 31/10/2026: PASSAGGIO PER UNA FASCETTA sotto la mensola (fermacavo del cavo del sensore, che passa sotto a Y ~43.5, Z 13):
#     due asole dal basso (Z 4.5-6.1 e 12.9-14.5; oltre Z 16.2 c'e' lo scarico della ruota) unite da un tunnel lungo Z sopra un ponticello di 1.5 mm. Fascetta fino a 2.5 x 1.1.
# 02/11/2026: tasca di alleggerimento chiusa dal basso nella mensola (sotto la slitta c'era un pieno da 11.9 mm; PolyD sconsiglia
#     pareti oltre 10 mm: cavita' in superficie). Aperta in basso (Y 47), 5 mm di profondita': sopra restano 6.1 mm fino al piano della slitta.
res = D([res, B(9.0, 20.5, 46.5, 52.0, 5.5, 11.5)])
FC_X = (24.0, 27.0)
res = D([res, U([B(FC_X[0], FC_X[1], 48.5, 50.1, 4.5, 14.5),
                 B(FC_X[0], FC_X[1], 46.8, 48.6, 4.5, 6.1), B(FC_X[0], FC_X[1], 46.8, 48.6, 12.9, 14.5)])])
# pulizia: alette da 0.1 mm lasciate dallo spostamento del braccio del rullo inferiore (estratto da X 2.9) fuori dal contorno piastra
res = D([res, U([B(-1, 3.7, 30.0, 41.15, ZE - 3, 17.0), B(-1, 3.06, 40.0, 70.0, ZE - 3, ZE - 0.01)])])   # 02/11: fino a X 3.7 (alette 0.18 sulle orecchie)
# --- SMUSSI DI STAMPA (spigoli esterni liberi; nessun accoppiamento toccato) -----------------------------------
#  (1) angoli convessi del contorno piastra raccordati R3 (come l'originale, a tutto spessore), (2) smusso 0.6 sul perimetro esterno della
#  faccia anteriore dove non c'e' nulla attaccato (01/11/2026: NIENTE smusso sulla faccia posteriore, in appoggio sulla piastra in alluminio),
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
# 03/11/2026 (Stefano): niente piu' smussi a gradini: il perimetro della faccia anteriore ha un RACCORDO TONDO R0.5 come gli spigoli
#     dell'STL originale (prima smusso 0.6 a gradini da 0.1). Sfera R0.5 fatta scorrere sul contorno (minkowski, manifold3d).
#     (2) retro: TOLTO il 01/11/2026 (Stefano): gli spigoli della faccia posteriore, in appoggio sulla piastra in alluminio, restano vivi
_RP = 0.5
_NOCH = so.unary_union([sg.Point(3.0, 18.70).buffer(3.6, 32), sg.Point(3.0, 80.40).buffer(3.6, 32)])   # 02/11: niente raccordo anteriore vicino ai fori M3 a Y 3 (restavano 0.8 mm sotto il foro)
m = _ext2(_OUT.difference(_Er).difference(_F), -0.2, X_BACKCOL + 0.2); cut += [m] if m is not None else []   # (1) angoli R3 a tutto spessore
_cp = _ext2(_Er.buffer(-_RP + 0.02, 32), X_BACKCOL - 3.0, X_BACKCOL - _RP + 0.003)
_rp = _to_tm(_to_mf(_cp).minkowski_sum(_mf.Manifold.sphere(_RP, 48)))
m = _ext2(_OUT.difference(_F), X_BACKCOL - _RP - 0.05, X_BACKCOL + 0.2)   # col raccordo R0.5 sotto i fori M3 a Y 3 restano >= 1 mm: niente esclusione
if m is not None: cut.append(D([m, _rp]))                                        # (2) fronte: raccordo R0.5
# (3) invito 0.5 x 45 sul bordo della tasca anteriore dell'encoder: cono vero (non a gradini: si vedevano anelli)
_c = trimesh.creation.cylinder(radius=1.0, height=1.0, sections=192)          # tronco di cono da r ENC_FR (X 7.22-0.5) a r ENC_FR+0.5 (X 7.22) e oltre
_v = _c.vertices.copy(); top = _v[:, 2] > 0
_v[:, :2] *= np.where(top, ENC_FR + 0.7, ENC_FR - 0.01)[:, None]; _v[:, 2] = np.where(top, 0.21, -0.5)
_c = trimesh.Trimesh(_v, _c.faces); _c.fix_normals()
_c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0])); _c.apply_translation([X_BACKCOL, ENC_C[0], ENC_C[1]])
cut.append(_c)
def _wedge(xc, zc, sx, sz, y0, y1, L=1.0):                                     # prisma triangolare lungo Y sullo spigolo (xc, zc)
    tri = sg.Polygon([(xc + 0.3*sx, zc + 0.3*sz), (xc - L*sx, zc + 0.3*sz), (xc + 0.3*sx, zc - L*sz)])
    w = trimesh.creation.extrude_polygon(tri, y1 - y0)                        # piano (X, Z), estrusione lungo +Y
    w.apply_transform(np.array([[1,0,0,0],[0,0,1,y0],[0,1,0,0],[0,0,0,1]], dtype=float))
    if w.volume < 0: w.invert()
    return w
for c in Z_FORK:                                                                # (4) spigoli verticali anteriori dei blocchi guida
    for sz in (-1, 1):
        if (c, sz) in ((Z_FORK[0], -1), (Z_FORK[1], 1)):                        # 04/11/2026: spigolo accanto alla guida dello sportellino
            _xc, _zc = XB + SX/2 + GW, c + sz*GZ                                   # (anima a Z -13.95 / 57.05): smusso 0.65 che finisce a filo
            _t = sg.Polygon([(_xc, _zc + 0.3*sz), (_xc - 0.95, _zc + 0.3*sz), (_xc, _zc - 0.65*sz)])   # sotto l'anima, senza tagliarla
            _w = trimesh.creation.extrude_polygon(_t, LUG_Y0 + 0.01 - (GY0 - 0.2))     # (prima: tacca 0.35 sotto la radice della guida)
            _w.apply_transform(np.array([[1,0,0,0],[0,0,1,GY0 - 0.2],[0,1,0,0],[0,0,0,1]], dtype=float))
            if _w.volume < 0: _w.invert()
            cut.append(_w)
        else:
            cut.append(_wedge(XB + SX/2 + GW, c + sz*GZ, 1, sz, GY0 - 0.2, LUG_Y0 + 0.01))
        if (c, sz) in ((Z_FORK[0], -1), (Z_FORK[1], 1)):                        # 04/11/2026: idem sulla spalla anteriore (tratto alto)
            _xc, _zc = TAP_X[1] + 2.75, c + sz*GZ
            _t = sg.Polygon([(_xc, _zc + 0.3*sz), (_xc - 0.95, _zc + 0.3*sz), (_xc, _zc - 0.65*sz)])
            _w = trimesh.creation.extrude_polygon(_t, GTOP + 0.2 - (LUG_Y0 - 0.01))
            _w.apply_transform(np.array([[1,0,0,0],[0,0,1,LUG_Y0 - 0.01],[0,1,0,0],[0,0,0,1]], dtype=float))
            if _w.volume < 0: _w.invert()
            cut.append(_w)
        else:
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
