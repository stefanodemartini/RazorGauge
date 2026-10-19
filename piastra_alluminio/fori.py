# ===================== FORI, LINGUETTE E ASOLE delle tre lastre (unica fonte per modello 3D, disegni e tabella) =====================
# tipi: 'F' filettato (vite nel foro, niente dado) | 'P' passante (vite + dado) | 'S' passante svasato 90° (vite a testa piana) |
#       'B' filettato nel BORDO (preforo sul bordo, profondita indicata) | 'A' apertura/asola/foro di passaggio (nessuna vite)
HOLES=[]
def H(lastra,cod,tipo,u,v,d,nota,prof=None,w=None,h=None): HOLES.append(dict(lastra=lastra,cod=cod,tipo=tipo,u=u,v=v,d=d,nota=nota,prof=prof,w=w,h=h))
# --- PIASTRA VERTICALE: coordinate (Z, Y) dell'assieme; disegno = vista dal FRONTE
for i,(y,z) in enumerate(AS_HOLES): H('P','P%d'%(i+1),'F',z,y,'M3','assieme di misura: vite M3x12 dal fronte (attraverso il pezzo MJF)',prof='passante')
for i,(y,z) in enumerate(RB_HOLES): H('P','P%d'%(i+9),'F',z,y,'M3','RazorBoard: distanziale M3x10 maschio-femmina dal retro, filetto maschio max 6 mm (P12 e coperto dal pezzo MJF: non deve sporgere)',prof='passante')
SH_TABS=[(-140,-120),(-90,-70)]                      # linguette della mensola (Z) -> asole nella piastra
SH_SCREWS=[-155.0,-105.0,-55.0]                      # viti svasate piastra -> bordo mensola
for i,z in enumerate(SH_SCREWS): H('P','P%d'%(13+i),'S',z,YSH-3,'M3 svasato','mensola: vite M3x12 testa piana dal FRONTE nel bordo della mensola (6 mm in presa)')
BASE_TABS=[(-200,-180),(-70,-50),(50,70)]            # linguette in basso della piastra (Z)
BASE_EDGE=[-212.0,-125.0,-5.0,82.0]                  # viti dal basso della base nel bordo della piastra
for i,z in enumerate(BASE_EDGE): H('P','P%d'%(16+i),'B',z,PL['y0'],'M3','base: filetto nel bordo inferiore (foro 10, filetto utile min 8), vite M3x12 testa piana dal basso della base',prof='10')
H('P','A1','A',49.55,35.0,'Ø42','corpo encoder (passaggio)')
H('P','A2','A',ZS,YS,'Ø14','albero + mozzo bobina (passaggio)')
H('P','A3','A',12.5,43.0,'10x9','asola fili sensore (dietro la tacca del pezzo MJF)',w=9,h=10)
H('P','A4','A',21.55,PL['y1']-5,'8x10','tacca cavo laser sul bordo superiore',w=8,h=10)
H('P','A5','A',-140.0,176.0,'144x42 R8','finestra di accesso al retro della bobina',w=144,h=42)
BTN=[('SCAN',170.0),('FAST_S',145.0),('FAST_O',120.0)]; ZBTN=-38.0     # pulsanti da pannello Ø12 in colonna sul fronte
for i,(n,y) in enumerate(BTN): H('P','P%d'%(20+i),'P',ZBTN,y,'Ø12','pulsante %s: foro passante Ø12, fissato con dado e controdado'%n)
for i,(z0,z1) in enumerate(SH_TABS): H('P','A%d'%(6+i),'A',(z0+z1)/2,YSH-3,'22.4x6.2 R1','asola per linguetta della mensola (gioco 1.2 per lato: lascia posto al raccordo alla radice della linguetta)',w=22.4,h=6.2)
# --- MENSOLA: coordinate (X, Z); disegno = vista dall'ALTO
FORK_H=[(7.8-73.9+DF,95.6-235.6),(32.2-73.9+DF,117.9-235.6)]
for i,(x,z) in enumerate(FORK_H): H('M','M%d'%(i+1),'F',x,z,'M3','forcella bobina (i fori della forcella Ø3 vanno portati a Ø3.4 per la M3)',prof='passante')
for i,dz in enumerate((-15.0,15.0)): H('M','M%d'%(3+i),'P',-63.4,ZM+dz,'asola 4.5x14','staffa NEMA: vite M4 + dado sotto, asola lungo Z = tensione cinghia ±5 mm',w=14,h=4.5)
for i,z in enumerate(SH_SCREWS): H('M','M%d'%(5+i),'B',XPB,z,'M3','filetto nel bordo anteriore (vite dalla piastra)',prof='10')
# --- BASE: coordinate (X, Z); disegno = vista dall'ALTO
for i,(z0,z1) in enumerate(BASE_TABS): H('B','A%d'%(i+1),'A',(XPB+XPF)/2,(z0+z1)/2,'6.2x22.4 R1','asola per linguetta della piastra (gioco 1.2 per lato)',w=6.2,h=22.4)
for i,z in enumerate(BASE_EDGE): H('B','B%d'%(i+1),'S',(XPB+XPF)/2,z,'M3 svasato','vite M3x12 testa piana DAL BASSO nel bordo della piastra (svasatura sul lato inferiore)')
for i,p in enumerate(DRV_HOLES): H('B','B%d'%(5+i),'F',float(p[0]),float(p[2]),'M4','driver TB6600: vite M4x8 nelle asole della flangia',prof='passante')
for i,(x,z) in enumerate(((-108,-210),(-108,80),(33,-210),(33,80))): H('B','B%d'%(7+i),'F',x,z,'M4','piedino in gomma a vite M4',prof='passante')
# alimentatore 183x49 steso (X -61..-12, Z -218..-35): asole in angoli opposti, interasse 175 x 35 -> 4 fori M3 (entrambe le diagonali, se ne usano 2)
PSX=(-61.0+7.0,-12.0-7.0); PSZ=(-218.0+4.0,-35.0-4.0)
for i,(x,z) in enumerate(((PSX[0],PSZ[0]),(PSX[1],PSZ[1]),(PSX[0],PSZ[1]),(PSX[1],PSZ[0]))):
    H('B','B%d'%(14+i),'F',x,z,'M3','alimentatore: vite M3x8 nell\'asola (interasse 175 x 35; 4 fori = due diagonali, se ne usano 2)',prof='passante')
# --- PIASTRINA PRESA IEC sul RETRO (bordo posteriore della base, zona alimentatore): coordinate (Z, Y); disegno = vista da DIETRO
XL=-116.0                                             # faccia esterna 4 mm dentro il bordo posteriore della base (X -120), spessore verso +X
ZIEC,YIEC=-170.0,5.0                                  # presa orizzontale, centro 25 mm sopra la base
LZ=(ZIEC-28,ZIEC+28); LY1=YIEC+16                     # 56 x 41: flangia 50 + 3 per lato, 5 sopra la flangia
L_TABS=[(ZIEC-10,ZIEC+10)]
L_SCREWS=[ZIEC-22,ZIEC+22]
H('L','A1','A',ZIEC,YIEC,'27.6x19.6 R1','presa IEC C14 (dima 27x19): foro 27.6x19.6 con angoli R1, maggiorato 0.3 per lato perche il corpo a spigoli vivi entri negli angoli raccordati',w=27.6,h=19.6)
for i,dz in enumerate((-20.0,20.0)): H('L','P%d'%(1+i),'P',ZIEC+dz,YIEC,'Ø3.4','presa IEC C14 + cover 220 V: vite M3 testa cilindrica dall\'esterno + dado sulla cover (interasse 40)')
for i,z in enumerate(L_SCREWS): H('L','B%d'%(1+i),'B',z,PL['y0'],'M3','base: filetto nel bordo inferiore (foro 10, filetto utile min 8), vite M3x12 testa piana dal basso della base',prof='10')
for i,(z0,z1) in enumerate(L_TABS): H('B','A%d'%(4+i),'A',XL+3,(z0+z1)/2,'6.2x22.4 R1','asola per linguetta della piastrina presa IEC (gioco 1.2 per lato)',w=6.2,h=22.4)
for i,z in enumerate(L_SCREWS): H('B','B%d'%(12+i),'S',XL+3,z,'M3 svasato','piastrina presa IEC: vite M3x12 testa piana DAL BASSO nel bordo (svasatura sul lato inferiore)')
# ------------------------------------------------------------------------- geometria 2D
def _hole_shape(h,rot=False):
    if h['tipo'] in ('B',): return None
    d=h['d']
    if h['w'] is not None:
        w,hh=(h['w'],h['h'])
        bx=sg.box(h['u']-w/2,h['v']-hh/2,h['u']+w/2,h['v']+hh/2)
        if 'asola' in h['nota'] and h['lastra']=='M': return bx.buffer(-min(w,hh)/2*0.999).buffer(min(w,hh)/2*0.999,16)
        return bx.buffer(-1.0,join_style=2).buffer(1.0,16)          # spigoli interni R1 (fresa Ø2)
    r={'Ø12':6.1,'M3':1.25,'M4':1.65,'M3 svasato':1.7,'Ø42':21.0,'Ø14':7.0,'M3?':1.25,'Ø3.4':1.7}.get(d,1.25)   # filettati: preforo; svasati: passaggio 3.4
    return sg.Point(h['u'],h['v']).buffer(r,32)
def poly(lastra):
    if lastra=='P':
        out=sg.box(PL['z0'],PL['y0'],PL['z1'],PL['y1']).buffer(-8,32).buffer(8,32).union(sg.box(PL['z0'],PL['y0'],PL['z1'],PL['y0']+20))   # R8 solo in alto; spigoli vivi contro la base
        out=so.unary_union([out]+[sg.box(z0,PL['y0']-6,z1,PL['y0']+0.01) for z0,z1 in BASE_TABS])
    elif lastra=='M':
        out=sg.box(-95,-162,XPB,-46).buffer(-8,32).buffer(8,32).union(sg.box(-50,-162,XPB,-46))   # R8 sui due spigoli posteriori, vivi contro la piastra
        out=so.unary_union([out]+[sg.box(XPB-0.01,z0,XPF,z1) for z0,z1 in SH_TABS])
    elif lastra=='L':
        out=sg.box(LZ[0],PL['y0'],LZ[1],LY1).buffer(-8,32).buffer(8,32).union(sg.box(LZ[0],PL['y0'],LZ[1],PL['y0']+15))   # R8 in alto, vivi contro la base
        out=so.unary_union([out]+[sg.box(z0,PL['y0']-6,z1,PL['y0']+0.01) for z0,z1 in L_TABS])
    else:
        out=sg.box(-120,PL['z0'],45,PL['z1']).buffer(-8,32).buffer(8,32)                   # spigoli R8
    hs=[_hole_shape(h) for h in HOLES if h['lastra']==lastra and h['d']!='M3?']   # foro alimentatore in sospeso: non si lavora
    if lastra=='P': hs.append(sg.Point(21.55,PL['y1']-10).buffer(4,32))      # fondo tondo della tacca laser
    if lastra=='P': hs=[x if not (x.bounds[2]-x.bounds[0]>100) else sg.box(-212,155,-68,197).buffer(-8).buffer(8,32) for x in hs if x is not None]
    return out.difference(so.unary_union([x for x in hs if x is not None]))
def ext(pg,thick,M):
    m=trimesh.creation.extrude_polygon(pg,thick); m.apply_transform(np.array(M,float)); return m
pm=ext(poly('P'),6.0,[[0,0,1,XPB],[0,1,0,0],[1,0,0,0],[0,0,0,1]])              # (u=Z,v=Y,w) -> (X=w+XPB, Y=v, Z=u): det -1 -> inverto
if pm.volume<0: pm.invert()
pm.visual.face_colors=[170,175,185,255]; P['piastra']=pm
mm=ext(poly('M'),6.0,[[1,0,0,0],[0,0,1,YSH-6],[0,1,0,0],[0,0,0,1]])            # (u=X,v=Z,w) -> (X=u, Y=w+YSH-6, Z=v)
if mm.volume<0: mm.invert()
mm.visual.face_colors=[150,155,165,255]; P['mensola']=mm
bm=ext(poly('B'),6.0,[[1,0,0,0],[0,0,1,PL['y0']-6],[0,1,0,0],[0,0,0,1]])
if bm.volume<0: bm.invert()
bm.visual.face_colors=[140,145,155,255]; P['base']=bm

# pulsanti nel modello 3D: testa sul fronte, corpo dietro
for n,y in BTN:
    hd=trimesh.creation.cylinder(radius=7.0,height=4,sections=40); hd.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); hd.apply_translation([XPF+2,y,ZBTN])
    bd=trimesh.creation.cylinder(radius=6.0,height=24,sections=40); bd.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); bd.apply_translation([XPB-12+6,y,ZBTN])
    m=trimesh.util.concatenate([hd,bd]); m.visual.face_colors=[40,40,45,255]; P['pulsante_'+n]=m

lm=ext(poly('L'),6.0,[[0,0,1,XL],[0,1,0,0],[1,0,0,0],[0,0,0,1]])            # (u=Z,v=Y,w) -> (X=XL+w, Y, Z=u): det -1 -> inverto
if lm.volume<0: lm.invert()
lm.visual.face_colors=[160,165,175,255]; P['piastrina_IEC']=lm
# presa IEC C14: flangia 50x22 all'esterno (dietro), corpo 27x19 dentro (faston compresi ~24 mm); spina inserita = ingombro indicativo
fl=trimesh.creation.box([3,22,50]); fl.apply_translation([XL-1.5,YIEC,ZIEC])
cb=trimesh.creation.box([24.4,19,27]); cb.apply_translation([XL+12-0.2,YIEC,ZIEC])
m=trimesh.util.concatenate([fl,cb]); m.visual.face_colors=[30,30,32,255]; P['presa_IEC']=m
sp=trimesh.creation.box([16,24,30.5]); sp.apply_translation([XL-3-8,YIEC,ZIEC]); sp.visual.face_colors=[90,90,95,255]; P['spina_IEC']=sp
