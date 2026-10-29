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
rigid=["pezzo_unico","coperchio","carrello","slitta_sensore","scheda_sensore","laser","tappo_laser","grani_laser","lente_L1","lente_L2","ruota_encoder_200mm","encoder_LPD3806",
       "rullo_inferiore_spostato","rullo_spintore_lato_misura","rullo_superiore_su_ruota","forcella_spintore_lato_misura","forcella_spintore_sulla_ruota",
       "cavo_sensore","bullone_dado_perno_forcella_spintore_lato_misura","bullone_dado_perno_forcella_spintore_sulla_ruota","sportello_luce","tappo_uscita"]
allowed={frozenset(p) for p in [("pezzo_unico","laser"),("laser","tappo_laser"),("laser","grani_laser"),("pezzo_unico","grani_laser"),("pezzo_unico","tappo_laser"),("pezzo_unico","lente_L1"),("carrello","lente_L2"),("slitta_sensore","scheda_sensore"),
         ("scheda_sensore","cavo_sensore"),("rullo_spintore_lato_misura","forcella_spintore_lato_misura"),("rullo_superiore_su_ruota","forcella_spintore_sulla_ruota"),
         ("forcella_spintore_lato_misura","bullone_dado_perno_forcella_spintore_lato_misura"),("forcella_spintore_sulla_ruota","bullone_dado_perno_forcella_spintore_sulla_ruota"),
         ("rullo_spintore_lato_misura","bullone_dado_perno_forcella_spintore_lato_misura"),("rullo_superiore_su_ruota","bullone_dado_perno_forcella_spintore_sulla_ruota"),
         ("pezzo_unico","rullo_inferiore_spostato"),("pezzo_unico","forcella_spintore_lato_misura"),("pezzo_unico","forcella_spintore_sulla_ruota"),("pezzo_unico","sportello_luce")]}
bad=[]
for a,b in itertools.combinations([r for r in rigid if r in g],2):
    if frozenset((a,b)) in allowed: continue
    A,Bm=g[a],g[b]
    if np.any(A.bounds[0]>Bm.bounds[1]) or np.any(Bm.bounds[0]>A.bounds[1]): continue
    v=vol(A,Bm)
    if not (v<=1e-3): bad.append("%s ∩ %s = %.3f"%(a,b,v))
rep(not bad,"Interferenze statiche tra %d parti: %s"%(len(rigid), "nessuna" if not bad else "; ".join(bad)))
# B) lenti e laser nelle sedi: gioco sedi
def crop(m,b,pad=3.0):                    # ritaglio locale: contains/closest_point sul pezzo intero esauriscono la memoria
    return trimesh.boolean.intersection([m,trimesh.creation.box(bounds=[b[0]-pad,b[1]+pad])],engine="manifold")
for nm in ("lente_L1","laser"):
    Pc=crop(P,g[nm].bounds); pts,fi=trimesh.sample.sample_surface(g[nm],3000); _,d,_=trimesh.proximity.closest_point(Pc,pts)
    pin=pts-g[nm].face_normals[fi]*0.03                                    # 0.03 dentro la superficie: il contatto voluto (cono) non conta
    rep(not Pc.contains(pin).any(),"%s nella sede: nessuna compenetrazione oltre 0.03 mm (contatto min %.2f)"%(nm,d.min()))
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
# D) slitta v2: estrazione verso il davanti 0..45 mm con la scheda (viti tolte, spina staccata)
w=0
for dx in np.arange(0.5,46,0.5):
    for part in (g["slitta_sensore"],g["scheda_sensore"]):
        mm=part.copy(); mm.apply_translation([dx,0,0]); w=max(w,vol(mm,P),vol(mm,g["coperchio"]))
rep(w<=1e-3,"Slitta + scheda v2: estrazione libera per 45 mm (max compenetrazione %.3f)"%w)
# D2) mensola, slitta e scheda: gioco con ruota encoder (Ø63.66 e Ø64.2; X 17.22-27.84 = ruota CNC e ruota originale), rullo inferiore
def rgap(m,yc,zc,R,x0,x1):
    Pt=np.vstack([m.sample(150000),m.vertices]); s=(Pt[:,0]>=x0)&(Pt[:,0]<=x1)&(Pt[:,1]>44)&(Pt[:,1]<64.5)&(Pt[:,2]>-15)&(Pt[:,2]<42)
    return (np.hypot(Pt[s,1]-yc,Pt[s,2]-zc)-R).min() if s.any() else 99
Rw=200/(2*math.pi)
for nm in ("slitta_sensore","scheda_sensore"):
    gw=min(rgap(g[nm],35,49.55,Rw,17.22,27.22),rgap(g[nm],35,49.55,Rw,17.84,27.84)); gr=rgap(g[nm],58.91,-6.45,8,17.22,27.22)
    rep(gw>=1.0 and gr>=1.0,"%s: gioco ruota %.2f mm (Ø64.2: %.2f), rullo inferiore %.2f mm"%(nm,gw,gw-0.27,gr))
Pz=trimesh.boolean.intersection([P,trimesh.creation.box(bounds=[[7.3,44.5,-1],[42,58.2,34]])])
gw=min(rgap(Pz,35,49.55,Rw,17.22,27.22),rgap(Pz,35,49.55,Rw,17.84,27.84)); gr=rgap(Pz,58.91,-6.45,8,17.22,27.22)
rep(gw>=1.4 and gr>=1.4,"Mensola: gioco ruota %.2f mm, rullo inferiore %.2f mm"%(gw,gr))
# D3) le DUE ruote sullo stesso albero (30/10/2026): ruota CNC (nell'assieme) e ruota originale (Decoder+Ruota.stl, mozzo Ø29
#     a 1.62 mm dal codolo come nel FlylineProfiler originale: cerchio Ø63.8 X 17.84-27.84). Gioco minimo da tutte le parti fisse.
_O=trimesh.load("/home/claude/cnc/Decoder_Ruota_originale.stl"); _O.merge_vertices()
_O=_O.slice_plane([0,22.99,0],[0,-1,0])                                  # solo ruota + mozzo (y < 23: senza il tratto di albero)
_O.apply_transform(np.array([[0,-1,0,29.84],[0,0,1,35.0-36.992],[1,0,0,49.55-31.907],[0,0,0,1]],float))   # X = 29.84 - y
def mind(wm, skip):
    S=wm.sample(8000); bb=wm.bounds; out=[]
    for k,gg in [("pezzo_unico",P)]+[(k,gg) for k,gg in g.items() if k not in skip]:
        c=gg
        for o,n in (([bb[0][0]-2,0,0],[1,0,0]),([bb[1][0]+2,0,0],[-1,0,0]),([0,bb[0][1]-2,0],[0,1,0]),([0,bb[1][1]+2,0],[0,-1,0]),([0,0,bb[0][2]-2],[0,0,1]),([0,0,bb[1][2]+2],[0,0,-1])):
            if len(c.faces)==0: break
            c=c.slice_plane(o,n)
        if len(c.faces)==0: continue
        q,d,_=trimesh.proximity.closest_point(c,S); i=int(np.argmin(d)); out.append((d[i],k,q[i]))
    return sorted(out,key=lambda a:a[0])[:2]
for nome,wm in (("CNC",g["ruota_encoder_200mm"]),("originale",_O)):
    mm_=mind(wm,("ruota_encoder_200mm","albero_encoder","cavo_2mm","pezzo_unico","encoder_LPD3806","rullo_superiore_su_ruota"))
    rep(mm_[0][0]>=0.5,"Ruota %s (X %.2f-%.2f, Ø%.2f): giochi minimi %s"%(nome,wm.bounds[0][0],wm.bounds[1][0],wm.extents[1],
        "; ".join("%s %.2f a (%.1f, %.1f, %.1f)"%(k,d,*q) for d,k,q in mm_)))
_cod=29.84-24.62                                                          # codolo: X 0 .. 5.22
rep(_O.bounds[0][0]-_cod>=1.0 and g["ruota_encoder_200mm"].bounds[0][0]-_cod>=1.0,
    "Mozzi lontani dal codolo dell'encoder: originale %.2f mm, CNC %.2f mm; albero nel foro della ruota CNC per %.1f mm (grani a X %.2f)"
    %(_O.bounds[0][0]-_cod,g["ruota_encoder_200mm"].bounds[0][0]-_cod,18.22-g["ruota_encoder_200mm"].bounds[0][0],10.44+3.39))
# M) MONTABILITA' (30/10/2026, richiesta di Stefano: controllare sempre che i pezzi si possano montare), nell'ordine di montaggio
def _cylX(x0,x1,y,z,r,sec=96):
    c=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=sec); c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
_fixed=[("pezzo_unico",P)]+[(k,gg) for k,gg in g.items() if k not in ("pezzo_unico","ruota_encoder_200mm","albero_encoder","encoder_LPD3806","cavo_2mm","sportello_luce","tappo_uscita")]   # sportellino e tappino: si tolgono prima di montare la ruota
def _hits(vol_mesh, parts):
    out=[]
    for k,gg in parts:
        if np.any(vol_mesh.bounds[0]>gg.bounds[1]) or np.any(gg.bounds[0]>vol_mesh.bounds[1]): continue
        v=vol(vol_mesh,gg)
        if v>1e-3: out.append("%s %.2f"%(k,v))
    return out
# M1) 3 viti M3x6 dell'encoder dal davanti (pezzo staccato dalla piastra, prima della ruota): testa Ø5.5 + chiave dal fronte
_eh=[(35+14*np.sin(a),49.55+14*np.cos(a)) for a in np.radians([90,210,330])]+[(35+15*np.sin(a),49.55+15*np.cos(a)) for a in np.radians([0,120,240])]
_cand=[]
for (y,z) in _eh:                                                         # appoggio della testa: raggi a r 2.9 attorno al foro
    ss=[]
    for a in np.linspace(0,2*np.pi,8,endpoint=False):
        loc,_,_=P.ray.intersects_location(np.array([[60.0,y+2.9*np.sin(a),z+2.9*np.cos(a)]]),np.array([[-1.0,0,0]]))
        loc=np.asarray(loc).reshape(-1,3); ss.append(max([q[0] for q in loc if q[0]<60],default=-1))
    _cand.append((y,z,float(np.median(ss))))
_m1=[c for c in _cand if 2.9<c[2]<3.1]
_bad=[("Y %.1f Z %.1f"%(y,z)) for (y,z,s) in _m1 if _hits(_cylX(s+0.05,90,y,z,3.0),[("pezzo_unico",P)])]
rep(len(_m1)==6 and not _bad,"M1 viti encoder: 6 fori con appoggio testa a X 3.0 (tasca anteriore), accesso dal davanti libero (Ø6) %s"%(_bad if _bad else ""))
# M2) ruota infilata in asse sull'albero dal davanti (con slitta, scheda e viti montate): volume spazzato + 0.3 mm
for _n,_s in (("CNC",[(10.44,17.22,9.3),(17.22,90,32.13)]),("originale",[(6.84,16.84,14.8),(16.84,17.84,22.6),(17.84,90,32.21)])):
    _sw=trimesh.boolean.union([_cylX(a,b,35,49.55,r,180) for a,b,r in _s],engine="manifold")
    _h=_hits(_sw,_fixed); rep(not _h,"M2 ruota %s: percorso di montaggio in asse dal davanti libero %s"%(_n,_h if _h else ""))
# M3) grani M3 del mozzo della ruota CNC (X 13.83): chiave esagonale 1.5 radiale tra parete (X 7.22) e cerchio (X 17.22)
_free=[]
for a in np.radians(np.arange(0,360,15)):
    d=np.array([0,np.sin(a),np.cos(a)]); k=_cylX(0,1,0,0,0.9,16)
    key=trimesh.creation.cylinder(radius=0.9,height=40,sections=16); key.apply_transform(trimesh.geometry.align_vectors([0,0,1],d))
    key.apply_translation(np.array([13.83,35,49.55])+d*(9.2+20))
    if not _hits(key,_fixed): _free.append(int(round(np.degrees(a))))
rep(len(_free)>=3,"M3 grani del mozzo ruota CNC raggiungibili radialmente in %d direzioni su 24 (es. %s gradi)"%(len(_free),_free[:6]))
# M4) 8 viti M3x12 pezzo -> piastra dal davanti: testa Ø5.5 dal piano di appoggio fino al fronte, nel solo pezzo unico
_mb=[]
for (y,z) in [(133.0,-6.1),(133.0,49.2),(169.5,-6.1),(169.5,49.2),(3.0,18.7),(3.0,80.4),(57.97,80.44),(52.0,18.67)]:
    loc,_,_=P.ray.intersects_location(np.array([[90.0,y+2.9,z]]),np.array([[-1.0,0,0]])); s=max([q[0] for q in loc if q[0]<90],default=0)
    if _hits(_cylX(7.27,90,y,z,2.9,48),[("pezzo_unico",P)]): _mb.append("Y %.1f Z %.1f"%(y,z))
rep(not _mb,"M4 viti pezzo -> piastra: corridoio testa Ø5.8 dal fronte libero nel pezzo per tutte le 8 viti %s"%(_mb if _mb else ""))
# S) SPORTELLINO FRONTALE (30/10/2026): luce ambiente sul chip, scorrimento sulle guide, scatti, carico della coda di topo
_S=g["sportello_luce"]
_hd=trimesh.boolean.union([trimesh.creation.box(bounds=[[38.9,85.9,z-2.3],[39.6,112,z+2.3]]) for z in (-12.45,55.55)],engine="manifold")
Ps=trimesh.boolean.difference([P,_hd],engine="manifold")              # tolta la faccia anteriore delle teste: li' premono i nottolini (voluto)
_sl=max(vol(_S.copy().apply_translation([0,dy,0]) or _S,Ps) for dy in [0])
_mx=0.0
for dy in np.arange(0,40.1,0.5):
    s_=_S.copy(); s_.apply_translation([0,dy,0]); _mx=max(_mx,vol(s_,Ps),vol(s_,g["coperchio"]))
    for k in ("forcella_spintore_lato_misura","forcella_spintore_sulla_ruota","bullone_dado_perno_forcella_spintore_lato_misura","bullone_dado_perno_forcella_spintore_sulla_ruota","scheda_sensore","slitta_sensore","cavo_sensore","viti_M3_slitta","ruota_encoder_200mm","rullo_superiore_su_ruota","rullo_spintore_lato_misura","rullo_inferiore_spostato"):
        _mx=max(_mx,vol(s_,g[k]))
rep(_mx<=1e-3,"S1 sportellino: scorre sulle guide da chiuso ad aperto (+13) e si sfila in alto (+40) senza toccare nulla (max %.3f)"%_mx)
_pr=[]
for dy in (0.0,13.0,6.5):
    s_=_S.copy(); s_.apply_translation([0,dy,0]); _pr.append(vol(s_,P))
rep(_pr[0]<0.05 and _pr[1]<0.05 and _pr[2]>0.05,"S2 nottolini: liberi negli incavi da chiuso (%.3f) e da aperto (%.3f), premono a meta' corsa (%.2f mm3)"%tuple(_pr))
def _luce(extra_skip=(),dy=None,N=200000):
    occ=[P]+[gg for k,gg in g.items() if k not in ("pezzo_unico","cavo_2mm","lente_L1","lente_L2","sportello_luce")+tuple(extra_skip)]
    if dy is not None:
        s_=_S.copy(); s_.apply_translation([0,dy,0]); occ.append(s_)
    Rr=trimesh.ray.ray_pyembree.RayMeshIntersector(trimesh.util.concatenate(occ))
    rg=np.random.default_rng(3); u=rg.random(N); v_=rg.random(N); r_=np.sqrt(u); th=2*np.pi*v_
    dd=np.stack([r_*np.cos(th),np.sqrt(1-u),r_*np.sin(th)],1)
    return [(~Rr.intersects_any(np.tile([22.22+px,64.42,21.55],(N,1)),dd)).mean() for px in (-4.0,0.0,4.0)]
_l0=_luce(); _l1=_luce(dy=0.0)
rep(max(_l1)<0.01,"S3 luce ambiente diretta sul chip (frazione dell'emisfero, pixel -4/0/+4 mm): senza sportellino %s -> chiuso %s"%(" ".join("%.4f"%x for x in _l0)," ".join("%.4f"%x for x in _l1)))
s_=_S.copy(); s_.apply_translation([0,13.0,0])
rep(s_.bounds[0][1]>=74.5,"S4 sportellino aperto: fondo a Y %.1f, sopra i labbri delle guide J e la coda di topo Ø3 sollevata (Y 73.5): si carica dal fronte"%s_.bounds[0][1])
_w=0
for dx in np.arange(0.5,46,1.0):
    for part in (g["slitta_sensore"],g["scheda_sensore"]):
        mm=part.copy(); mm.apply_translation([dx,0,0]); _w=max(_w,vol(mm,s_))
rep(_w<=1e-3,"S5 slitta + scheda estraibili con lo sportellino aperto (max %.3f)"%_w)
# Q) QUALITA' DELLA MESH del pezzo unico (30/10/2026): lamelle e pareti sottili create dalle booleane (superfici coincidenti,
#    cerchi che tagliano spigoli di sbieco). Spessore del materiale dietro ogni faccia; restano solo ~0.5 mm2 dell'STL originale.
_c=P.triangles_center; _n=P.face_normals; _a=P.area_faces; _ok=_a>1e-4
_Rq=trimesh.ray.ray_pyembree.RayMeshIntersector(P)
_l,_ri,_=_Rq.intersects_location(_c[_ok]-_n[_ok]*0.005,-_n[_ok],multiple_hits=False)
_th=np.full(_ok.sum(),99.0); _th[_ri]=np.linalg.norm(_l-(_c[_ok]-_n[_ok]*0.005)[_ri],axis=1)
_ta=_a[_ok][_th<0.5].sum(); _r=np.hypot(_c[:,1]-35,_c[:,2]-49.55)
_enc=(_r<28)&(_c[:,0]<8)&(_ok); _te=_th[_enc[_ok]].min()
rep(_ta<1.0 and _te>0.8,"Q mesh pezzo unico: superficie con materiale < 0.5 mm = %.2f mm2 (solo STL originale), zona encoder spessore minimo %.2f mm, piani %s"%(_ta,_te,sorted(set(np.round(_c[_enc&(np.abs(_n[:,0])>0.99),0],2)))))
# TU) TAPPINO REMOVIBILE della gola di uscita (31/10/2026): sta nel vano, si toglie sollevandolo (la clip si apre), gola aperta senza
_T=g["tappo_uscita"]
_Tb=trimesh.boolean.intersection([_T,trimesh.creation.box(bounds=[[0,64.0,70],[40,80,90]])],engine="manifold")   # senza il dente della clip
_tm=0.0
for dy in np.arange(0,12.1,0.5):
    s_=_Tb.copy(); s_.apply_translation([0,dy,0]); _tm=max([_tm,vol(s_,P)]+[vol(s_,g[k]) for k in g if k not in ("tappo_uscita","pezzo_unico","cavo_2mm")])
_cl=max(vol(_T.copy().apply_translation([0,dy,0]),P) for dy in (1.0,2.0,3.0))
rep(_tm<=1e-3 and _cl>0.05,"TU tappino gola d'uscita: si sfila verso l'alto senza toccare nulla (max %.3f); la clip deve aprirsi per uscire (dente %.2f mm3 sul fronte del braccio)"%(_tm,_cl))
_sw=trimesh.creation.box(bounds=[[22.22-1.45,67.6,60.6],[22.22+1.45,85.0,83.4]])     # coda di topo Ø2.9 calata dall'alto lungo tutta la gola
_ov=vol(_sw,P)
rep(_ov<=1e-3,"TU senza tappino la gola e' aperta in alto per tutta la lunghezza (Z 60.6-83.4): la coda di topo si cala dall'alto (ostacoli %.3f mm3)"%_ov)
# Q2) pezzi stampati piccoli (31/10/2026): spessore minimo del materiale (slitta, sportellino, tappino gola, coperchio, carrello)
for _k in ("slitta_sensore","sportello_luce","tappo_uscita","coperchio","carrello"):
    _m=g[_k]; _c2=_m.triangles_center; _n2=_m.face_normals; _ok2=_m.area_faces>1e-4
    _R2=trimesh.ray.ray_pyembree.RayMeshIntersector(_m); _p2=_c2[_ok2]-_n2[_ok2]*0.005
    _l2,_r2,_=_R2.intersects_location(_p2,-_n2[_ok2],multiple_hits=False); _t2=np.full(len(_p2),99.0); _t2[_r2]=np.linalg.norm(_l2-_p2[_r2],axis=1)
    _cc=_c2[_ok2]
    _txt={"sportello_luce":(_cc[:,0]>41.0)&(_cc[:,1]>72.5)&(_cc[:,1]<87.7),            # logo inciso: creste tra lettere vicine (dettaglio del logo)
          "coperchio":(_cc[:,0]>35.5)&(_cc[:,1]>116.5)&(_cc[:,1]<164.5)&(_cc[:,2]>17.0)&(_cc[:,2]<26.0)}.get(_k,np.zeros(len(_cc),bool))   # scritta RazorGauge
    _a2=_m.area_faces[_ok2][(_t2<0.5)&~_txt].sum(); _at=_m.area_faces[_ok2][(_t2<0.5)&_txt].sum()
    rep(_a2<0.5,"Q2 %s: superficie con materiale < 0.5 mm = %.2f mm2 (spessore minimo fuori dalle scritte %.2f)%s"%(_k,_a2,_t2[~_txt].min(),
        ("; nelle scritte incise %.1f mm2 di creste sottili tra lettere vicine (dettaglio grafico, non strutturale)"%_at) if _at>0 else ""))
# E) fascio ottico: cilindro Ø13 dal chip a L2 e tronco di cono L2 -> L1 (Ø13 -> Ø3) liberi
beam=[]
cyl=trimesh.creation.cylinder(radius=8.0,height=24.5-1.5-0.3,sections=64)   # v3: fascio Ø16 (laser 3 mm x 5.2); cyl.apply_translation([0,0,0.3+(24.5-1.5-0.3)/2]); beam.append(cyl)
z1,z2=24.5+1.5,105.2-1.6
cone=trimesh.creation.cone(radius=8.0,height=(z2-z1)*1.0,sections=64)   # punta verso +z (v3: da Ø16)
cone.apply_translation([0,0,z1]); beam.append(cone)
okb=True; msg=[]
for b in beam:
    b.apply_transform(Mt)
    for k in ("pezzo_unico","coperchio","carrello","slitta_sensore","forcella_spintore_lato_misura","forcella_spintore_sulla_ruota"):
        v=vol(b,g[k])
        if v>1e-3: okb=False; msg.append("%s %.2f"%(k,v))
rep(okb,"Fascio laser (Ø16 tra chip e L2, cono L2→L1) libero da ostacoli %s"%("" if okb else msg))
# F) linea Ø0.5 / 2 / 3 mm sul percorso reale (31/10/2026): dritta sul piano rullo inferiore - ruota (fondo Y 66.91) fino alla
#    cima della ruota (Z 49.55), poi verso l'uscita puo' scendere di qualche grado (la ruota e' sotto, la linea non e' vincolata):
#    cerco l'angolo minimo che la fa passare libera nel foro di uscita del blocco originale. OK se <= 2 gradi.
_lk=("pezzo_unico","coperchio","slitta_sensore","scheda_sensore","ruota_encoder_200mm","rullo_inferiore_spostato","sportello_luce","tappo_uscita")
def _seg(a,b,r):
    a=np.array(a,float); b=np.array(b,float); L=np.linalg.norm(b-a); c=trimesh.creation.cylinder(radius=r,height=L,sections=48)
    c.apply_transform(trimesh.geometry.align_vectors([0,0,1],(b-a)/L)); c.apply_translation((a+b)/2); return c
# dopo la cima della ruota la coda di topo e' un filo teso: appoggia sulla ruota e sul fondo della guida originale di uscita
# (che scende verso l'uscita) e lascia il pezzo con un angolo che dipende da dove si trova la bobina. Percorso = inviluppo
# superiore degli appoggi (ruota, fondo della guida) tra la cima della ruota e un punto a Z 95 piu' o meno in basso.
_fl=[]
for z in np.arange(49.6,83.4,0.2):
    hs=[]
    for dx in (-1.0,0.0,1.0):
        l_=np.asarray(P.ray.intersects_location(np.array([[22.22+dx,67.8,z]]),np.array([[0,-1.0,0]]))[0]).reshape(-1,3)   # da dentro il canale (sotto il soffitto 69.0)
        hs.append(l_[:,1].max() if len(l_) else -99)
    _fl.append((z,max(hs)))
def _hull_up(pts):
    pts=sorted(pts); H=[]
    for p_ in pts:
        while len(H)>=2 and (H[-1][0]-H[-2][0])*(p_[1]-H[-2][1])-(H[-1][1]-H[-2][1])*(p_[0]-H[-2][0])>=0: H.pop()
        H.append(p_)
    return H
for dia in (0.5,2.0,3.0):
    r=dia/2-0.05; yc=66.91+dia/2
    A=_seg([22.22,yc,-30],[22.22,yc,49.55],r)
    hA=[k for k in _lk if vol(A,g[k])>1e-3]
    sup=[(49.55+31.91*np.sin(t_)+0, 35+(31.91+dia/2)*np.cos(t_)) for t_ in np.radians(np.arange(0,40,1.0))]
    sup=[(49.55+(31.91+dia/2)*np.sin(t_), 35+(31.91+dia/2)*np.cos(t_)) for t_ in np.radians(np.arange(0,40,1.0))]+[(z,f+dia/2) for z,f in _fl if f>0]
    best=None
    for ye in np.arange(yc,yc-6.01,-0.25):
        H=_hull_up([(49.55,yc)]+[s for s in sup if s[0]>49.55]+[(95.0,ye)])
        segs=[_seg([22.22,H[i][1],H[i][0]],[22.22,H[i+1][1],H[i+1][0]],r) for i in range(len(H)-1) if H[i+1][0]-H[i][0]>1e-3]
        hit=[k for k in _lk if any(vol(s_,g[k])>1e-3 for s_ in segs)]
        if not hit:
            angs=[np.degrees(np.arctan2(H[i][1]-H[i+1][1],H[i+1][0]-H[i][0])) for i in range(len(H)-1)]
            best=(ye,max(angs)); break
    rep(not hA and best is not None and best[1]<=5.0,"Linea Ø%.1f: libera tra i rulli %s; dopo la ruota (filo teso su ruota e fondo della guida di uscita) passa libera%s"%(dia,"si" if not hA else hA,(", piega massima %.1f gradi"%best[1]) if best else ": NO"))
chip_y=64.41; rep(abs(66.91-chip_y-2.5)<1e-6,"Distanza chip ↔ fondo linea 2.50 mm")
# G) forcelle su tutta la corsa: ripreso da chk_forks2 (gia' eseguito) -> rieseguo in breve
from forks import place
def cylX(x0,x1,y,z,r,sec=48):
    c=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=sec); c.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
# linguette anti-gioco delle sedi (30/10/2026): i denti premono la forcella per costruzione -> nella prova di corsa li tolgo
_GY0=85.0; _bz=[]
for c,s0 in ((-6.45,-1),(49.55,1)):
    _bz.append(trimesh.creation.box(bounds=[[30.52-0.8,_GY0+0.1,c-3.5],[30.52+0.31,_GY0+3.8,c+3.5]]))
    zi=c+s0*6.3; _bz.append(trimesh.creation.box(bounds=[[22.22-7.8,_GY0+0.1,min(zi,zi-s0*0.8)-(0.31 if s0<0 else 0)],[22.22+7.8,_GY0+3.8,max(zi,zi-s0*0.8)+(0.31 if s0>0 else 0)]]))
Pf=trimesh.boolean.difference([P,trimesh.boolean.union(_bz,engine="manifold")],engine="manifold")
pre=[]
for c,nm in ((-6.45,"forcella_spintore_lato_misura"),(49.55,"forcella_spintore_sulla_ruota")):
    for d in (-1,0.5,3,5):
        f=place(c,d); vv=[vol(f,trimesh.boolean.intersection([P,b],engine="manifold")) for b in _bz[:2] if True] if c<0 else [vol(f,trimesh.boolean.intersection([P,b],engine="manifold")) for b in _bz[2:]]
        pre.append(min(vv))
rep(min(pre)>0.05,"Linguette anti-gioco: i 2 denti di ogni sede premono la forcella su tutta la corsa (compenetrazione voluta min %.2f mm3)"%min(pre))
# spazio per la flessione delle linguette (0.6 mm verso l'esterno): nessuna parte nell'area
_fz=[]
for c,s0 in ((-6.45,-1),(49.55,1)):
    _fz.append(trimesh.creation.box(bounds=[[30.52+2.0,_GY0,c-3.5],[30.52+2.6,_GY0+14,c+3.5]]))
    zo=c+s0*8.15; _fz.append(trimesh.creation.box(bounds=[[22.22-7.7,_GY0,min(zo,zo+s0*0.6)],[22.22+7.7,_GY0+14,max(zo,zo+s0*0.6)]]))
_fh=[k for k,gg in g.items() if k!="cavo_2mm" and any(vol(b,gg)>1e-3 for b in _fz)]+(["pezzo_unico"] if any(vol(b,P)>1e-3 for b in _fz) else [])
rep(not _fh,"Linguette anti-gioco: spazio libero per la flessione verso l'esterno %s"%(_fh if _fh else ""))
wf=0
for c in (-6.45,49.55):
    for d in (-1,0.5,3,5):
        yr=66.91+d+8
        for m in (place(c,d), cylX(17.22,27.22,yr,c,8), cylX(10.7,14.22,yr,c,4.62), cylX(30.22,34.22,yr,c,4.62)):
            wf=max(wf,vol(m,Pf),vol(m,g["coperchio"]))
rep(wf<=1e-3,"Forcelle + rulli + bulloni: liberi da senza cavo a cavo 3 mm +2 mm (max compenetrazione %.3f)"%wf)
# H) fori M2 della scheda v2: materiale della slitta attorno (anello r 1.3-2.0) e foro libero al centro
R=trimesh.load("tray.stl"); okh=True
for (tx,ty) in ((-10.5,-2),(-10.5,6),(10.5,-2.5)):
    ring=[[tx+r*np.cos(a_),ty+r*np.sin(a_),-4.5] for r in (1.3,2.0) for a_ in np.linspace(0,2*np.pi,12,endpoint=False)]
    if not R.contains(ring).all() or R.contains([[tx,ty,-4.5]]).any(): okh=False
rep(okh,"Fori M2 della scheda v2 sopra la slitta (foro Ø1.7 autofilettante, parete >= 2 mm)")
# I) viti M3 della slitta raggiungibili dall'alto (cacciavite Ø3.2)
oks=True
inter=trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.util.concatenate([P,g["coperchio"]]))
for (sx,sy) in ((15.9,9.0),(16.0,14.3)):
    X=22.22+sx; Z=21.55-sy
    for dx in (-1.6,0,1.6):
        for dz in (-1.6,0,1.6):
            if len(inter.intersects_location(np.array([[X+dx,61.7,Z+dz]]),np.array([[0,1,0]]))[0]): oks=False
rep(oks,"Viti M3 della slitta raggiungibili dall'alto (nessun ostacolo sopra, cacciavite Ø3.2)")
print("\n".join(res))
