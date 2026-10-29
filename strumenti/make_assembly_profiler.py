import trimesh, numpy as np, math, sys
from trimesh.creation import cylinder
T=trimesh.transformations
O="/mnt/user-data/outputs/RazorGauge/integrazione_profiler/"
pull = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0     # slitta estratta di "pull" mm (solo per le immagini)
def col(m, rgba): m=m.copy(); m.visual.face_colors=rgba; return m
def cylX(x0,x1,y,z,r,sec=96):
    c=cylinder(radius=r,height=x1-x0,sections=sec); c.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
ZM=21.55                                                   # punto di misura (interasse ruota-laser 28.00)
Mt=T.translation_matrix([22.22,64.41,ZM]) @ T.rotation_matrix(-np.pi/2,[1,0,0])
def tp(m): m=m.copy(); m.apply_transform(Mt); return m
parts={}
parts["pezzo_unico"]=col(trimesh.load("profiler.stl"),[190,190,195,255])
C=trimesh.load("carriage.stl"); C.apply_translation([0,0,24.5]); parts["carrello"]=col(tp(C),[90,100,115,255])
vs=[cylX(30.22,36.22,64.41+24.5+3.8,ZM-6.5,1.5,24), cylX(36.22,39.22,64.41+24.5+3.8,ZM-6.5,2.75,24)]   # vite M3x6 di blocco del carrello, dal davanti
parts["vite_M3_carrello"]=col(trimesh.util.concatenate(vs),[60,60,60,255])
L=trimesh.load("lid.stl"); Ml=T.rotation_matrix(math.radians(-90),[0,1,0]) @ T.translation_matrix([-14,0,0]); L.apply_transform(np.linalg.inv(Ml)); parts["coperchio"]=col(tp(L),[120,120,125,140])
las=cylinder(radius=4.5,height=20,sections=64); las.apply_translation([0,0,114.2+10]); parts["laser"]=col(tp(las),[200,30,30,255])   # Picotronic Ø9 x 20 (29/10/2026)
parts["tappo_laser"]=col(tp(trimesh.load("laser_cap.stl")),[150,150,160,255])
vg=[]                                                       # 2 grani M3 x 8 (frontale +X, laterale +Y) a Z_LF + 14
for d in ((1,0),(0,1)):
    g_=cylinder(radius=1.5,height=8,sections=20); g_.apply_transform(T.rotation_matrix(np.pi/2,[-d[1],d[0],0])); g_.apply_translation([d[0]*(4.6+4),d[1]*(4.6+4),114.2+14]); vg.append(g_)
parts["grani_laser"]=col(tp(trimesh.util.concatenate(vg)),[60,60,60,255])
l1=cylinder(radius=12.47/2,height=3.11,sections=64); l1.apply_translation([0,0,105.2]); parts["lente_L1"]=col(tp(l1),[150,200,255,200])
l2=cylinder(radius=19.95/2,height=2.8,sections=64); l2.apply_translation([0,0,24.5]); parts["lente_L2"]=col(tp(l2),[150,200,255,200])
_sp=trimesh.load("/home/claude/pu/run_sportello/sportello.stl"); _sp.apply_translation([0,13.0 if pull>0 else 0.0,0])   # sportellino (aperto quando la slitta e' estratta)
parts["sportello_luce"]=col(_sp,[45,45,50,255])
parts["tappo_uscita"]=col(trimesh.load("/home/claude/pu/run_tappo_uscita/tappo_uscita.stl"),[45,45,50,255])   # copertura removibile della gola di uscita (31/10/2026)
tray=tp(trimesh.load("tray.stl")); tray.apply_translation([pull,0,0]); parts["slitta_sensore"]=col(tray,[230,160,40,255])
# scheda sensore v2 (TSL1401CL, 28/10/2026): ingombro da cad/FlylineProfiler_RazorGauge.scad VIEW="pcb"
S=tp(trimesh.load("pcb.stl")); S.apply_translation([pull,0,0]); parts["scheda_sensore"]=col(S,[20,130,40,255])
vv=[]                                                       # 2 viti M3 x 12 verticali: slitta 3.5 + 8.5 nella mensola
for (sx,sy) in ((15.9,9.0),(16.0,14.3)):
    sh=cylinder(radius=1.5,height=12,sections=24); sh.apply_translation([sx,sy,-6.3+3.5-6]); vv.append(sh)
    if sy < 12:                                              # svasata ISO 10642 a filo della slitta (sotto la spina del connettore)
        hd=trimesh.creation.cone(radius=3.0,height=3.0,sections=32); hd.apply_transform(T.rotation_matrix(np.pi,[1,0,0])); hd.apply_translation([sx,sy,-6.3+3.5])
        hd=trimesh.boolean.intersection([hd,trimesh.creation.box(bounds=[[sx-4,sy-4,-6.3+3.5-1.6],[sx+4,sy+4,-6.3+3.5-0.02]])],engine="manifold"); vv.append(hd)
    else:
        hd=cylinder(radius=2.75,height=3,sections=24); hd.apply_translation([sx,sy,-6.3+3.5+1.5]); vv.append(hd)
scr=tp(trimesh.util.concatenate(vv)); scr.apply_translation([pull,0,0]); parts["viti_M3_slitta"]=col(scr,[60,60,60,255])
# cavo schermato Ø4 dalla spina (bordo anteriore della scheda) giu' davanti alla mensola, sotto di essa fino alla tacca della piastra
pts=np.array([[43.2,63.5,15.05],[46.0,63.5,15.05],[46.0,44.5,15.05],[43.5,44.0,13.0],[3.5,43.5,13.0],[-25,43.5,13.0]])
segs=[]
for a_,b_ in zip(pts[:-1],pts[1:]):
    L_=np.linalg.norm(b_-a_); c=cylinder(radius=2.0,height=L_,sections=16)
    c.apply_transform(trimesh.geometry.align_vectors([0,0,1],(b_-a_)/L_)); c.apply_translation((a_+b_)/2); segs.append(c)
    sp=trimesh.creation.icosphere(subdivisions=1,radius=2.0); sp.apply_translation(b_); segs.append(sp)
if pull == 0: parts["cavo_sensore"]=col(trimesh.boolean.union(segs,engine="manifold"),[30,30,30,255])
R=200/(2*math.pi)
# ruota CNC reale (STEP RG_ruota_encoder, 30/10/2026): mozzo Ø18 verso la parete, faccia posteriore del mozzo a X 10.44,
# cerchio X 17.22-27.22 (10.0 mm dalla faccia anteriore del pezzo, mezzeria sulla linea X 22.22)
_W=trimesh.load("/home/claude/cnc/RG_ruota_encoder.step"); _W=_W.to_geometry() if hasattr(_W,"to_geometry") else _W
_W.apply_scale(1000.0); _W.merge_vertices(); _W.apply_transform(np.array([[0,0,1,10.44],[0,1,0,35.0],[1,0,0,49.55],[0,0,0,1]],float))
parts["ruota_encoder_200mm"]=col(_W,[60,170,90,255])
# encoder LPD3806 col fondo della sede riportato a X 0-3 (30/10/2026): faccia di montaggio a X 0 (retro del pezzo),
# corpo Ø38.2 x 34.3 nel foro Ø42 della piastra in alluminio, codolo Ø20 x 5.22, albero Ø6 x 13 (punta a X 18.22)
parts["albero_encoder"]=col(cylX(5.22,18.22,35,49.55,2.98),[160,160,160,255])
parts["encoder_LPD3806"]=col(trimesh.boolean.union([cylX(-34.3,0.0,35,49.55,19.1),cylX(-0.01,5.22,35,49.55,10.0)],engine="manifold"),[40,40,40,255])
for nm,(y,z) in {"rullo_inferiore_spostato":(58.91,-6.45),"rullo_spintore_lato_misura":(76.91,-6.45),"rullo_superiore_su_ruota":(76.91,49.55)}.items():
    parts[nm]=col(cylX(17.22,27.22,y,z,8),[40,70,200,255])
    if nm=="rullo_inferiore_spostato": parts["perno_"+nm]=col(cylX(14.2,30.2,y,z,2.4),[170,170,170,255])
import sys as _s; _s.path.insert(0,"/home/claude/fp/v3"); from forks import place
for z,nm in ((-6.45,"forcella_spintore_lato_misura"),(49.55,"forcella_spintore_sulla_ruota")):
    parts[nm]=col(place(z,2.0),[150,120,200,255])
    yr=66.91+2+8                                           # centro rullo con cavo Ø2
    # perno dei cuscinetti = bullone M5 x 25 (testa esagonale 8 x 3.5) + dado M5 (8 x 4)
    hx=trimesh.creation.cylinder(radius=4.62,height=3.5,sections=6); hx.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); hx.apply_translation([22.22-8-1.75,yr,z])
    nt=trimesh.creation.cylinder(radius=4.62,height=4.0,sections=6); nt.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); nt.apply_translation([22.22+8+2.0,yr,z])
    sh=cylX(14.22,22.22+8+4+1.5,yr,z,2.5,24)
    parts["bullone_dado_perno_"+nm]=col(trimesh.util.concatenate([hx,nt,sh]),[110,110,115,255])
    bu=cylinder(radius=3.1,height=9.87,sections=24); bu.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); bu.apply_translation([22.22,yr+15.93,z])
    parts["boccola_filettata_"+nm]=col(bu,[200,170,60,255])   # boccola nella sede Ø6.27 della forcella originale
    y_top=yr-76.91+122.8                                   # stelo M5 avvitato nella boccola, esce 5 mm sopra il cappello (a cavo Ø2)
    st=cylinder(radius=2.5,height=y_top-(yr+12),sections=24); st.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); st.apply_translation([22.22,(y_top+yr+12)/2,z])
    parts["stelo_M5_"+nm]=col(st,[90,90,90,255])
    y0=yr+13; y1=111.8                                     # molla attorno al cilindro Ø8 della forcella e allo stelo, fino al cappello
    sp=trimesh.boolean.difference([cylinder(radius=5.0,height=y1-y0,sections=32), cylinder(radius=4.2,height=y1-y0+1,sections=32)]); sp.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); sp.apply_translation([22.22,(y0+y1)/2,z]); parts["molla_"+nm]=col(sp,[220,220,60,255])
TP=trimesh.load("/home/claude/fp/v3/tappo_blocco_guida.stl")
for z,nm in ((-6.45,"lato_misura"),(49.55,"sulla_ruota")):
    t=TP.copy(); t.apply_translation([0,0,z+6.45]); parts["tappo_"+nm]=col(t,[150,150,160,255])
    vv=[]
    for x in (10.6,33.4):
        b=cylinder(radius=1.5,height=12,sections=20); b.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); b.apply_translation([x,117.8-6+6-6,z]); b.apply_translation([0,0,0])
        b=cylinder(radius=1.5,height=12,sections=20); b.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); b.apply_translation([x,117.8-6,z])
        hd=cylinder(radius=2.75,height=3,sections=20); hd.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); hd.apply_translation([x,117.8+1.5,z])
        vv+= [b,hd]
    parts["viti_tappo_"+nm]=col(trimesh.util.concatenate(vv),[60,60,60,255])
line=cylinder(radius=1,height=150,sections=32); line.apply_translation([22.22,67.91,37]); parts["cavo_2mm"]=col(line,[255,150,0,255])
sc=trimesh.Scene()
for k,m in parts.items(): sc.add_geometry(m, node_name=k, geom_name=k)
if pull == 0:
    sc.export(O+"FlylineProfiler_RazorGauge_assieme.glb")          # GLB: Y in alto (convenzione glTF) -> piastra verticale
    # STL e 3MF: Z in alto (Windows 3D Viewer, slicer) -> ruoto come in realta: piastra verticale, torre in alto,
    # fronte (lato cavo) verso l'osservatore della vista frontale, coda di topo orizzontale
    R = T.rotation_matrix(-np.pi/2, [0,0,1]) @ T.rotation_matrix(np.pi/2, [1,0,0])
    sc_r = trimesh.Scene()
    for k,m in parts.items(): mm = m.copy(); mm.apply_transform(R); sc_r.add_geometry(mm, node_name=k, geom_name=k)
    sc_r.export(O+"FlylineProfiler_RazorGauge_assieme.3mf")
    trimesh.util.concatenate(list(sc_r.geometry.values())).export(O+"FlylineProfiler_RazorGauge_assieme.stl")
sc.export("assieme_%d.glb" % int(pull))
print("ok", pull)
