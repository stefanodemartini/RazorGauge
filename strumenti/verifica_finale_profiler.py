import sys; sys.path.insert(0,"/home/claude/fp/v3")
import trimesh, numpy as np, itertools, math
T=trimesh.transformations
I=trimesh.boolean.intersection
def vol(a,b):
    try: return I([a,b]).volume
    except Exception as e: return float('nan')
def clean(m):
    m=m.copy(); m.merge_vertices(digits_vertex=4); return m
P=trimesh.load("profiler.stl")
g={k:clean(v) for k,v in trimesh.load("assieme_0.glb").geometry.items()}
g["pezzo_unico"]=P
res=[]
def rep(ok,txt): res.append(("OK " if ok else "!! ")+txt); print(res[-1],flush=True)
# A) interferenze statiche tra parti rigide (escluse le coppie a contatto voluto)
rigid=["pezzo_unico","coperchio","carrello","slitta_sensore","scheda_sensore","laser","lente_L1","lente_L2","ruota_encoder_200mm","encoder_LPD3806",
       "rullo_inferiore_spostato","rullo_spintore_lato_misura","rullo_superiore_su_ruota","forcella_spintore_lato_misura","forcella_spintore_sulla_ruota",
       "fascetta_2_5mm","bullone_dado_perno_forcella_spintore_lato_misura","bullone_dado_perno_forcella_spintore_sulla_ruota"]
allowed={frozenset(p) for p in [("pezzo_unico","laser"),("pezzo_unico","lente_L1"),("carrello","lente_L2"),("slitta_sensore","scheda_sensore"),
         ("slitta_sensore","fascetta_2_5mm"),("rullo_spintore_lato_misura","forcella_spintore_lato_misura"),("rullo_superiore_su_ruota","forcella_spintore_sulla_ruota"),
         ("forcella_spintore_lato_misura","bullone_dado_perno_forcella_spintore_lato_misura"),("forcella_spintore_sulla_ruota","bullone_dado_perno_forcella_spintore_sulla_ruota"),
         ("rullo_spintore_lato_misura","bullone_dado_perno_forcella_spintore_lato_misura"),("rullo_superiore_su_ruota","bullone_dado_perno_forcella_spintore_sulla_ruota"),
         ("pezzo_unico","rullo_inferiore_spostato")]}
bad=[]
for a,b in itertools.combinations([r for r in rigid if r in g],2):
    if frozenset((a,b)) in allowed: continue
    A,Bm=g[a],g[b]
    if np.any(A.bounds[0]>Bm.bounds[1]) or np.any(Bm.bounds[0]>A.bounds[1]): continue
    v=vol(A,Bm)
    if not (v<=1e-3): bad.append("%s ∩ %s = %.3f"%(a,b,v))
rep(not bad,"Interferenze statiche tra %d parti: %s"%(len(rigid), "nessuna" if not bad else "; ".join(bad)))
# B) lenti e laser nelle sedi: gioco sedi
for nm in ("lente_L1","laser"):
    pts=g[nm].sample(3000); _,d,_=trimesh.proximity.closest_point(P,pts); rep(not P.contains(pts).any(),"%s nella sede: nessuna compenetrazione (contatto min %.2f)"%(nm,d.min()))
pts=g["lente_L2"].sample(3000); rep(not g["carrello"].contains(pts).any(),"lente L2 nel carrello: nessuna compenetrazione")
# C) carrello su tutta la corsa (-5..+6) nella colonna e sotto il coperchio
Mt=T.translation_matrix([22.22,64.41,21.55]) @ T.rotation_matrix(-np.pi/2,[1,0,0])
C0=trimesh.load("carriage.stl"); worst=[]
for dz in np.arange(-5,6.01,1.0):
    c=C0.copy(); c.apply_translation([0,0,24.5+dz]); c.apply_transform(Mt)
    worst.append(max(vol(c,P),vol(c,g["coperchio"])))
rep(max(worst)<=1e-3,"Carrello L2 libero su tutta la corsa −5/+6 mm (max compenetrazione %.3f mm3)"%max(worst))
# asola coperchio allineata al foro carrello su tutta la corsa
L=g["coperchio"]; ok=True
for dz in (-5,0,6):
    y=64.41+24.5+3.75+dz; xs=np.arange(33.6,36.6,0.05)
    if L.contains(np.c_[xs,np.full_like(xs,y),np.full_like(xs,15.05)]).any(): ok=False
rep(ok,"Asola del coperchio libera sull'asse della vite del carrello per tutta la corsa")
# D) slitta: estrazione 0..45 mm con scheda, fascetta, vite tolta
S=trimesh.util.concatenate([g["slitta_sensore"],g["scheda_sensore"],g["fascetta_2_5mm"]]); w=0
for dx in np.arange(1,46,1.0):
    m=S.copy(); m.apply_translation([dx,0,0])
    for part in (g["slitta_sensore"],g["scheda_sensore"],g["fascetta_2_5mm"]):
        mm=part.copy(); mm.apply_translation([dx,0,0]); w=max(w,vol(mm,P))
rep(w<=1e-3,"Slitta + scheda + fascetta: estrazione libera per 45 mm (max compenetrazione %.3f)"%w)
# E) fascio ottico: cilindro Ø13 dal chip a L2 e tronco di cono L2 -> L1 (Ø13 -> Ø3) liberi
beam=[]
cyl=trimesh.creation.cylinder(radius=6.5,height=24.5-1.5-0.3,sections=64); cyl.apply_translation([0,0,0.3+(24.5-1.5-0.3)/2]); beam.append(cyl)
z1,z2=24.5+1.5,105.2-1.6
cone=trimesh.creation.cone(radius=6.5,height=(z2-z1)*1.0,sections=64)   # punta verso +z
cone.apply_translation([0,0,z1]); beam.append(cone)
okb=True; msg=[]
for b in beam:
    b.apply_transform(Mt)
    for k in ("pezzo_unico","coperchio","carrello","slitta_sensore","forcella_spintore_lato_misura","forcella_spintore_sulla_ruota"):
        v=vol(b,g[k])
        if v>1e-3: okb=False; msg.append("%s %.2f"%(k,v))
rep(okb,"Fascio laser (Ø13 tra chip e L2, cono L2→L1) libero da ostacoli %s"%("" if okb else msg))
# F) linea: Ø0.5 / 2 / 3 mm dritta sul piano di scorrimento, dal rullo inferiore oltre la ruota
for dia in (0.5,2.0,3.0):
    c=trimesh.creation.cylinder(radius=dia/2-0.03,height=120,sections=48); c.apply_translation([22.22,66.91+dia/2,30])
    hits=[k for k in ("pezzo_unico","coperchio","slitta_sensore","scheda_sensore","ruota_encoder_200mm","rullo_inferiore_spostato") if vol(c,g[k])>1e-3]
    rep(not hits,"Linea Ø%.1f: passa libera (guide J, guida originale, scheda, coperchio) %s"%(dia,hits if hits else ""))
chip_y=64.41; rep(abs(66.91-chip_y-2.5)<1e-6,"Distanza chip ↔ fondo linea 2.50 mm")
# G) forcelle su tutta la corsa: ripreso da chk_forks2 (gia' eseguito) -> rieseguo in breve
from forks import place
def cylX(x0,x1,y,z,r,sec=48):
    c=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=sec); c.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
wf=0
for c in (-6.45,49.55):
    for d in (-1,0.5,3,5):
        yr=66.91+d+8
        for m in (place(c,d), cylX(17.22,27.22,yr,c,8), cylX(10.7,14.22,yr,c,4.62), cylX(30.22,34.22,yr,c,4.62)):
            wf=max(wf,vol(m,P),vol(m,g["coperchio"]))
rep(wf<=1e-3,"Forcelle + rulli + bulloni: liberi da senza cavo a cavo 3 mm +2 mm (max compenetrazione %.3f)"%wf)
# H) fori della scheda allineati alle asole della slitta
R=trimesh.load("tray.stl"); okh=True
for ty in (0,6.5):
    for tx in (-10.6,10.6):
        if R.contains([[tx,ty,-4.5]]).any(): okh=False
rep(okh,"Fori M2 della scheda (±10.6, ty 0 e 6.5) sopra le asole della slitta")
print("\n".join(res))
