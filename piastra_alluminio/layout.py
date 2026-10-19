import trimesh, numpy as np
T=trimesh.transformations
U="/mnt/user-data/uploads/RazorGauge/Stl_esterrni/"
def B(x0,x1,y0,y1,z0,z1,c):
    b=trimesh.creation.box([x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); b.visual.face_colors=c; return b
P={}
# --- parametri layout (coordinate dell'assieme: X fuori dalla piastra, Y su, Z lungo il cavo; retro assieme X=0)
SP=0.0                      # assieme appoggiato direttamente sulla piastra (niente distanziali)
XPF=-SP; XPB=XPF-6          # faccia anteriore / posteriore piastra alluminio
YS,ZS=108.0,-140.0          # asse bobina: coda di topo sul lato INFERIORE della bobina (orizzontale a meta riempimento)
YSH=YS-32.0                 # piano superiore mensola (base forcella)
ZM=ZS+58.6                  # asse motore
PL=dict(z0=-222,z1=92,y0=-20,y1=207)
import shapely.geometry as sg, shapely.ops as so
def plate_poly():
    # coordinate 2D (u, v) = (-Z, Y): vista dal RETRO della piastra
    out=sg.box(-PL['z1'],PL['y0'],-PL['z0'],PL['y1'])
    holes=[sg.Point(-49.55,35.0).buffer(21.0,96),                       # corpo encoder Ø42
           sg.Point(-ZS,YS).buffer(7.0,64),                             # albero + mozzo bobina Ø14
           sg.box(-17.0,38.0,-8.0,48.0).buffer(0,join_style=1),       # asola fili sensore 10 x 9 (dietro la tacca)
           sg.box(-25.55,PL['y1']-10,-17.55,PL['y1']+1).union(sg.Point(-21.55,PL['y1']-10).buffer(4,32)),   # tacca cavo laser
           sg.box(68+8,155+8,212-8,197-8).buffer(8,32),                 # FINESTRA di accesso al retro della bobina 144 x 42 (Y 155-197, Z -212..-68)
           ]
    for (y,z) in AS_HOLES: holes.append(sg.Point(-z,y).buffer(1.25,24))  # M3 filettati assieme (preforo 2.5)
    for (y,z) in RB_HOLES: holes.append(sg.Point(-z,y).buffer(1.25,24))  # M3 filettati distanziali scheda
    return out.difference(so.unary_union(holes))
PLATE_POLY=None
P['mensola']=B(-95,XPB,YSH-6,YSH,-162,-46,[150,155,165,255])   # ridotta: forcella + motore con +-5 mm di tensionamento

# --- BASE orizzontale (6 mm) sotto la piastra: piastra con 3 linguette nelle asole della base + 3 angolari sul retro
YB=PL['y0']                                   # piano superiore della base = filo inferiore piastra
P['base']=B(-120,45,YB-6,YB,PL['z0'],PL['z1'],[140,145,155,255])   # ridotta

# --- ELETTRONICA sul retro
# RazorBoard 150x95 in verticale dietro l'assieme, su distanziali M3 da 10 (sopra il corpo encoder)
BZ0,BY0=-6.0,57.0                                   # angolo basso-destro (vista dal retro) della scheda
rb=trimesh.load("/tmp/razorboard_mesh.ply",process=False)
rb.apply_transform(np.array([[0,0,-1,XPB-10],[-1,0,0,BY0+150],[0,1,0,BZ0+95],[0,0,0,1]],float))   # scheda in verticale, componenti verso il retro
P['RazorBoard']=rb
def hexs(x0,x1,y,z,s=5.5,c=[200,200,205,255]):          # distanziale esagonale M3 lungo X
    h=trimesh.creation.cylinder(radius=s/np.sqrt(3),height=x1-x0,sections=6); h.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); h.apply_translation([(x0+x1)/2,y,z]); h.visual.face_colors=c; return h
RB_HOLES=[(BY0+150-x, BZ0+95-y) for x,y in ((4,4),(146,4),(4,91),(146,91))]     # (Y,Z) dei fori della scheda
P['distanziali_scheda']=trimesh.util.concatenate([hexs(XPB-10,XPB,y,z) for y,z in RB_HOLES])
AS_HOLES=[(133.0,-6.1),(133.0,49.2),(169.5,-6.1),(169.5,49.2),(3.0,18.7),(3.0,80.4),(57.97,80.44),(52.0,18.67)]   # fori M3 filettati nella piastra
# alimentatore 183x49x24 sotto la mensola, steso
P['alimentatore']=B(XPB-6-49,XPB-6,PL['y0'],PL['y0']+24,-218,-35,[200,200,60,255])   # steso sulla base, sotto la mensola
# driver TB6600: flangia (96x28.3) contro la piastra, corpo sporge 58 mm; sotto la mensola sopra l'alimentatore
dr=trimesh.load(U+"driver.stl"); dr.apply_transform(np.array([[0,0,1,0],[0,-1,0,0],[1,0,0,0],[0,0,0,1]],float))   # flangia in basso, sulla base
b=dr.bounds; _t=np.array([XPB-70-b[1][0], PL['y0']-b[0][1], -128-b[0][2]]); dr.apply_translation(_t);
DRV_HOLES=[(np.array([[0,0,1],[0,-1,0],[1,0,0]])@np.array(p)+_t) for p in ((198.35,123.8,162.17),(285.35,123.8,162.17))]   # centri asole driver (X,Y,Z)
dr.visual.face_colors=[200,60,60,255]; P['driver']=dr
g=trimesh.load("/home/claude/fp/v3/assieme_0.glb")
for k,m in g.geometry.items():
    m=m.copy(); P['A_'+k]=m
# bobina: piastra a X 73.9 dell'albero -> coda di topo al centro della zona di avvolgimento; mozzo dentro il foro della piastra.
# L'albero scorre in forcella e puleggia: forcella + puleggia 60T avanzate di DF verso la piastra (3 mm dalla faccia posteriore).
DF=15.6
raw=trimesh.load(U+"Bobinaconforcella.stl")
def cylX(x0,x1,r,y=95.6,z=95.6):
    c=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=48); c.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
fork=trimesh.boolean.difference([trimesh.boolean.intersection([raw,B(-1,49.4,0,200,0,200,[0,0,0,255])]),cylX(-2,52,2.6)])
spool=trimesh.boolean.difference([raw,B(-1,49.4,0,200,0,200,[0,0,0,255])])
shaft=cylX(0,49.5,2.5)
for m in (fork,spool,shaft): m.apply_translation([XPF-73.9,YS-95.6,ZS-95.6])
fork.apply_translation([DF,0,0])
fork.visual.face_colors=[40,90,170,255]; spool.visual.face_colors=[60,120,200,255]; shaft.visual.face_colors=[170,170,175,255]
P['bobina']=spool; P['forcella']=fork; P['albero_bobina']=shaft
sp=trimesh.util.concatenate([spool,fork,shaft])
mo=trimesh.load(U+"Nema17con supporto.stl"); mo.apply_translation([-104+DF,YSH,ZM-25.25]); mo.visual.face_colors=[60,60,60,255]; P['motore']=mo
exec(open('/home/claude/piastra/fori.py').read())
import pickle; pickle.dump({k:(v.vertices,v.faces,np.array(v.visual.face_colors[0]) if hasattr(v.visual,'face_colors') else None) for k,v in P.items()},open('/tmp/layout.pkl','wb'))
# --- verifiche
def bx(m): return m.bounds.round(1).tolist()
print("bobina",bx(sp)); print("motore",bx(mo))
A=trimesh.util.concatenate([v for k,v in P.items() if k.startswith('A_')])
def hit(a,b):
    try: return trimesh.boolean.intersection([a,b]).volume
    except Exception as e: return 'err'
for a,b in (('bobina','piastra'),('motore','piastra'),('bobina','mensola'),('forcella','mensola'),('forcella','piastra'),('forcella','motore'),('motore','mensola'),('bobina','motore'),('A_encoder_LPD3806','piastra'),('motore','A_encoder_LPD3806'),('driver','mensola'),('driver','alimentatore'),('RazorBoard','A_encoder_LPD3806'),('distanziali_scheda','A_encoder_LPD3806'),('A_pezzo_unico','piastra'),('pulsante_SCAN','bobina'),('pulsante_FAST_O','bobina'),('pulsante_FAST_O','motore'),('pulsante_SCAN','A_pezzo_unico'),('pulsante_FAST_O','mensola'),('driver','motore'),('base','bobina'),('base','A_pezzo_unico'),('presa_IEC','alimentatore'),('piastrina_IEC','alimentatore'),('piastrina_IEC','piastra'),('piastrina_IEC','bobina'),('presa_IEC','bobina'),('spina_IEC','bobina'),('alimentatore','driver'),('alimentatore','pulsante_FAST_O'),('alimentatore','piastra'),('piastrina_IEC','base'),('piastrina_IEC','driver'),('presa_IEC','driver'),('piastrina_IEC','mensola')):
    print(a,b,hit(P[a],P[b]) if P[a].is_watertight and P[b].is_watertight else 'n/w')
# puleggia: estensioni in X delle pulegge
s=sp.section(plane_origin=[0,YS+19,ZS],plane_normal=[0,1,0])
print("bobina: sezione a Y asse+19 X", s.bounds[:,0].round(1) if s is not None else None)
for xx in np.arange(-60,-20,2):
    q=mo.section(plane_origin=[xx,0,0],plane_normal=[1,0,0])
    if q is not None: print(" motore X%.0f Y %s Z %s"%(xx,q.bounds[:,1].round(1),q.bounds[:,2].round(1)))
pickle.dump(dict(HOLES=HOLES,L=poly('L'),LZ=LZ,P=poly('P'),M=poly('M'),B=poly('B'),PL=PL,XPB=XPB,XPF=XPF,BASE_TABS=BASE_TABS,SH_TABS=SH_TABS,YSH=YSH),open('/tmp/fori.pkl','wb'))
