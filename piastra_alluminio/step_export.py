# Esporta le 4 lastre in STEP con geometria pulita (archi veri, primitive + booleane), lastra stesa: spessore Z 0..6
import pickle, math, cadquery as cq
R=pickle.load(open('/tmp/fori.pkl','rb')); H=R['HOLES']; PL=R['PL']; XPB=R['XPB']; XPF=0.0
O='/mnt/user-data/outputs/RazorGauge/piastra_alluminio/cnc/'; T=6.0
LZ=R['LZ']; LY1=5.0+16.0
CFG={'P':dict(sx=-1,sy=1,nome='RG_piastra_verticale',csk='top',
              rect=(PL['z0'],PL['y0'],PL['z1'],PL['y1']),r8=[(PL['z0'],PL['y1']),(PL['z1'],PL['y1'])],
              tabs=[(z0,PL['y0']-6,z1,PL['y0']) for z0,z1 in R['BASE_TABS']]),
     'M':dict(sx=1,sy=-1,nome='RG_mensola',csk='top',
              rect=(-95.0,-162.0,XPB,-46.0),r8=[(-95.0,-162.0),(-95.0,-46.0)],
              tabs=[(XPB,z0,XPF,z1) for z0,z1 in R['SH_TABS']]),
     'B':dict(sx=1,sy=-1,nome='RG_base',csk='bottom',
              rect=(-120.0,PL['z0'],45.0,PL['z1']),r8=[(-120.0,PL['z0']),(-120.0,PL['z1']),(45.0,PL['z0']),(45.0,PL['z1'])],tabs=[]),
     'L':dict(sx=-1,sy=1,nome='RG_piastrina_presa_IEC',csk='top',
              rect=(LZ[0],PL['y0'],LZ[1],LY1),r8=[(LZ[0],LY1),(LZ[1],LY1)],
              tabs=[(-180.0,PL['y0']-6,-160.0,PL['y0'])])}
ROUND={'M3':2.5,'M4':3.3,'M3 svasato':3.4,'Ø12':12.2,'Ø42':42.0,'Ø14':14.0,'Ø3.4':3.4}
def boxsolid(x0,y0,x1,y1,z0=0.0,z1=T): 
    return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0,centered=False).translate((x0,y0,z0))
for L,c in CFG.items():
    sx,sy=c['sx'],c['sy']
    def tfp(u,v): return (sx*u, sy*v)
    def tbox(u0,v0,u1,v1):
        a=tfp(u0,v0); b=tfp(u1,v1); return (min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
    boxes=[tbox(*c['rect'])]+[tbox(*t) for t in c['tabs']]
    x0=min(b[0] for b in boxes); y0=min(b[1] for b in boxes)
    def F(u,v): p=tfp(u,v); return (p[0]-x0,p[1]-y0)
    def FB(u0,v0,u1,v1): b=tbox(u0,v0,u1,v1); return (b[0]-x0,b[1]-y0,b[2]-x0,b[3]-y0)
    rb=FB(*c['rect']); w=boxsolid(*rb)
    for (cu,cv) in c['r8']:
        px,py=F(cu,cv)
        w=w.edges(cq.selectors.BoxSelector((px-0.1,py-0.1,-1),(px+0.1,py+0.1,T+1))).fillet(8.0)
    for t in c['tabs']:
        w=w.union(boxsolid(*FB(*t)))
    hs=[h for h in H if h['lastra']==L and h['d']!='M3?']
    for h in hs:
        if h['tipo']=='B': continue
        x,y=F(h['u'],h['v'])
        if h['w'] is not None:
            ww,hh=(h['w'],h['h'])
            if L=='M' and 'asola' in h['nota']:           # asola ad estremi tondi
                cut=cq.Workplane('XY').workplane(offset=-1).center(x,y).slot2D(ww,hh,0).extrude(T+2)
            else:
                rr=8.0 if ww>100 else 1.0
                cut=boxsolid(x-ww/2,y-hh/2,x+ww/2,y+hh/2,-1,T+1).edges('|Z').fillet(rr)
                if h['cod']=='A4' and L=='P':                 # tacca laser: fondo tondo R4, aperta sul bordo
                    yb=PL['y1']-10.0; xb,ybb=F(h['u'],yb)
                    cut=boxsolid(x-4,min(ybb,ybb+sy*11),x+4,max(ybb,ybb+sy*11),-1,T+1).union(
                        cq.Workplane('XY').workplane(offset=-1).center(xb,ybb).circle(4).extrude(T+2))
            w=w.cut(cut)
        else:
            d=ROUND[h['d']]
            w=w.cut(cq.Workplane('XY').workplane(offset=-1).center(x,y).circle(d/2).extrude(T+2))
            if h['tipo']=='S':
                z=T if c['csk']=='top' else 0.0; dz=-1 if c['csk']=='top' else 1
                cone=cq.Solid.makeCone(3.75,0,3.75,cq.Vector(x,y,z-0.5*dz),cq.Vector(0,0,dz))
                w=w.cut(cq.Workplane().add(cone))
    # fori filettati nel bordo
    bb=w.val().BoundingBox(); cxm=(bb.xmin+bb.xmax)/2; cym=(bb.ymin+bb.ymax)/2
    for h in hs:
        if h['tipo']!='B': continue
        depth=float(h['prof']); x,y=F(h['u'],h['v'])
        dv=cq.Vector(-1 if x>cxm else 1,0,0) if L=='M' else cq.Vector(0,1 if y<cym else -1,0)
        w=w.cut(cq.Workplane().add(cq.Solid.makeCylinder(1.25,depth+0.5,cq.Vector(x,y,T/2)-dv*0.5,dv)))
    v=w.val()
    from OCP.BRepCheck import BRepCheck_Analyzer
    ok=BRepCheck_Analyzer(v.wrapped).IsValid()
    fs=w.faces().vals()
    from collections import Counter
    print('%-24s vol %.1f cm3  valido %s  BRepCheck %s  facce %d %s  bbox %.1f x %.1f'%(c['nome'],v.Volume()/1000,v.isValid(),ok,len(fs),dict(Counter(f.geomType() for f in fs)),bb.xlen,bb.ylen))
    cq.exporters.export(w,O+c['nome']+'.step')
