# Unisce piastra modificata + colonna RazorGauge (manifold via trimesh) -> STL pezzo unico
import trimesh, numpy as np, sys
from trimesh.creation import box
src, col, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = trimesh.load(src); C = trimesh.load(col)
ENC_C = (35.0, 49.55)            # asse dell'encoder / ruota (Y, Z)
ENC_R = 26.5                     # sede del corpo encoder Ø53 (corpo Ø38): comprende le 4 finestre ad arco (r 20-26), niente pareti sottili
ENC_WALL = 3.0                   # fondo della sede = spessore della piastra originale: l'albero sporge come prima
ENC_FR = 19.0                    # tasca anteriore Ø38 (30/10/2026): teste viti encoder (r 14-15 + 2.75, margine 1.25) e mozzo Ø29 della ruota originale.
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
res = D([res, B(4.72, 9.0, TR_Y0 - 0.3, TR_Y0 + 2.25, 11.4, 23.7)])   # 31/10/2026: gioco laterale della linguetta 0.15 (era 0.25): slitta ripetibile
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
res = D([res, extrude_yz(so.unary_union(_win), -0.1, X_BACKCOL)])
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
        _x0, _x1 = SH_HEAD_X[1] - 0.35, SH_HEAD_X[1] + 0.1                     #  servivano ~1.6 N per nottolino e lo spigolo poteva puntare)
        rcut.append(trimesh.convex.convex_hull(np.array([[_x0, yd + dy, zz] for dy in (-0.4, 0.4) for zz in (z - 2.2, z + 2.2)] +
                                                          [[_x1, yd + dy, zz] for dy in (-1.26, 1.26) for zz in (z - 2.2, z + 2.2)])))
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
plug = trimesh.boolean.intersection([plug, U([B(-0.1, 3.2, 50, 70, 0, 40), B(3.0, 7.22, 50, 58.0, 0, 40)])])   # 58.0: sotto la sede della linguetta v2 (fondo 58.11)
res = U([res, plug])
hn = trimesh.creation.cylinder(radius=1.65, height=X_BACKCOL + 1, sections=48); hn.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); hn.apply_translation([X_BACKCOL/2, *HOLE_NEW])
res = D([res, hn])
# 28/10/2026: la mensola della slitta copre il foro: canale Ø6.5 per la vite e il cacciavite, da X 7.22 al fronte della mensola
bore = trimesh.creation.cylinder(radius=3.25, height=35, sections=48); bore.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0])); bore.apply_translation([7.22 + 17.5, *HOLE_NEW])
bore_open = B(7.22, 42.5, HOLE_NEW[0] - 3.25, HOLE_NEW[0] + 3.25, HOLE_NEW[1], 34.0)   # canale aperto verso la ruota: niente lamelle tra canale e scarico ruota
bore_open = U([bore_open, B(12.0, 42.5, 46.9, HOLE_NEW[0] - 3.25 + 0.01, HOLE_NEW[1], 34.0)])   # 30/10/2026: sotto il canale, lato ruota, restava un cuneo 0.15-0.4 mm tra canale e scarico ruota
res = D([res, U([bore, bore_open])])
# 31/10/2026: FORO DI USCITA della coda di topo dopo la ruota (blocco ORIGINALE, Z 78.5-83.4): era 3.0 x 2.8 (Y 65.6-68.4) ->
#     la Ø3 passava schiacciata e strisciando, la Ø2 toccava il soffitto se dritta. Allargato a 3.6 x 3.7 (Y 65.3-69.0, pareti
#     0.9 sopra / 1.4 sotto), spigoli lungo Z R0.6, fondo a rampa dall'interno, smusso all'uscita (niente invito sul soffitto: con 0.9 di parete lascerebbe un filo).
def _ex_rect(hw, y0, y1, z):
    pr = sg.box(XB - hw, y0, XB + hw, y1).buffer(-0.6, 16).buffer(0.6, 16)
    return np.array([[x, y, z] for x, y in pr.exterior.coords])
_ex = [trimesh.convex.convex_hull(np.vstack([_ex_rect(1.8, 65.3, 69.0, 77.0), _ex_rect(1.8, 65.3, 69.0, 83.0)])),
       trimesh.convex.convex_hull(np.vstack([_ex_rect(1.8, 66.3, 69.0, 69.0), _ex_rect(1.8, 65.3, 69.0, 77.05)])),   # fondo a rampa (niente gradino)
       trimesh.convex.convex_hull(np.vstack([_ex_rect(1.8, 65.3, 69.0, 82.9), _ex_rect(2.2, 64.9, 69.3, 83.7)]))]
res = D([res, U(_ex)])
# 31/10/2026 (Stefano: la copertura della gola d'ingresso a sinistra trattiene la coda di topo durante la scansione ma spesso
#     e' un problema): COPERTURA RIMOVIBILE. Tolto dal pezzo il tratto sopra la gola (X 16 - fronte, Y 67.4 - 70, Z 77.9 - fine: comprende l invito originale del soffitto);
#     al suo posto il tappino strumenti/build_tappo_uscita.py: a U rovesciata, rifa' il soffitto a Y 69.0, 2 perni Ø2.4 nei fori
#     Ø2.6 delle due pareti, clip elastica che aggancia il sotto del braccio sul fronte. Senza tappino la gola e' aperta in alto.
TU_X0, TU_Y0, TU_Z0 = 16.0, 67.4, 77.9
TU_PINS = ((18.2, 80.85), (26.2, 80.85))                                   # (X, Z) dei perni
res = D([res, U([B(TU_X0, 28.6, TU_Y0, 70.1, TU_Z0, 83.8)] +
               [trimesh.creation.cylinder(radius=1.3, height=2.6, sections=32).apply_transform(
                    trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0])).apply_translation([px, TU_Y0 - 1.25, pz]) for px, pz in TU_PINS])])
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
