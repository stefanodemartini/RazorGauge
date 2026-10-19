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
las=cylinder(radius=2,height=14,sections=48); las.apply_translation([0,0,127.2]); parts["laser"]=col(tp(las),[200,30,30,255])
l1=cylinder(radius=12.47/2,height=3.11,sections=64); l1.apply_translation([0,0,105.2]); parts["lente_L1"]=col(tp(l1),[150,200,255,200])
l2=cylinder(radius=19.95/2,height=2.8,sections=64); l2.apply_translation([0,0,24.5]); parts["lente_L2"]=col(tp(l2),[150,200,255,200])
tray=tp(trimesh.load("tray.stl")); tray.apply_translation([pull,0,0]); parts["slitta_sensore"]=col(tray,[230,160,40,255])
S=trimesh.load("/mnt/user-data/outputs/RazorGauge/cad/sensor.stl"); S=trimesh.intersections.slice_mesh_plane(S,[0,0,-1],[0,0,4.2],cap=True); S.apply_transform(T.translation_matrix([-12.6,15.5,0.2]) @ T.rotation_matrix(np.pi,[1,0,0])); S=tp(S); S.apply_translation([pull,0,0]); parts["scheda_sensore"]=col(S,[20,130,40,255])
scr=cylinder(radius=1.5,height=10,sections=24); scr.apply_translation([17.0,16.65,-5.5-3]); scr=tp(scr); scr.apply_translation([pull,0,0]); parts["vite_M3_slitta"]=col(scr,[60,60,60,255])
# spina XH 5 poli sotto la scheda + 5 fili che passano dalla tacca della piastra verso il retro
def boxp(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box([x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
# fili saldati direttamente nei 5 fori (fila a ty 9.7 -> Z 11.3, misurata), uscita verso il basso; fascetta sull'aletta della slitta
tie=[boxp(14.92,29.52,54.6,57.1,11.9,12.9),boxp(14.92,29.52,54.6,57.1,7.6,8.6),boxp(14.92,15.92,54.6,57.1,7.6,12.9),boxp(28.52,29.52,54.6,57.1,7.6,12.9),boxp(29.52,33.5,54.3,57.4,11.7,15.7)]
for t_ in tie: t_.apply_translation([0,0,ZM-21.0])
tie=trimesh.util.concatenate(tie); tie.apply_translation([pull,0,0]); parts["fascetta_2_5mm"]=col(tie,[250,250,250,255])
wcols=[[30,30,30,255],[200,30,30,255],[230,200,40,255],[40,90,210,255],[40,160,60,255]]   # GND VCC AO CLK SI
for i,x in enumerate([17.22,19.72,22.22,24.72,27.22]):
    ya=42.0+1.3*(i%3); za=11.8+1.4*(i//3)+0.7*(i%2)
    pts=np.array([[x+pull,61.0,ZM-9.7],[x+pull,46.5,ZM-9.7],[x+pull-1.5,ya,za],[3.5,ya,za],[-25,ya,za]])
    segs=[]
    for a_,b_ in zip(pts[:-1],pts[1:]):
        L=np.linalg.norm(b_-a_); c=cylinder(radius=0.6,height=L,sections=12)
        c.apply_transform(trimesh.geometry.align_vectors([0,0,1],(b_-a_)/L)); c.apply_translation((a_+b_)/2); segs.append(c)
        sp=trimesh.creation.icosphere(subdivisions=1,radius=0.6); sp.apply_translation(b_); segs.append(sp)
    parts["filo_%d"%(i+1)]=col(trimesh.util.concatenate(segs),wcols[i])
R=200/(2*math.pi)
wheel=trimesh.boolean.difference([cylX(17.22,27.22,35,49.55,R,180), cylX(17,27.5,35,49.55,4)]); parts["ruota_encoder_200mm"]=col(wheel,[60,170,90,255])
parts["albero_encoder"]=col(cylX(-2,26.5,35,49.55,3),[160,160,160,255])
parts["encoder_LPD3806"]=col(cylX(4.2-35.5,4.2,35,49.55,19),[40,40,40,255])   # corpo Ø38 appoggiato sul fondo della sede (X 4.22)
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
    sc.export(O+"FlylineProfiler_RazorGauge_assieme.glb"); sc.export(O+"FlylineProfiler_RazorGauge_assieme.3mf")
    trimesh.util.concatenate(list(parts.values())).export(O+"FlylineProfiler_RazorGauge_assieme.stl")
sc.export("assieme_%d.glb" % int(pull))
print("ok", pull)
