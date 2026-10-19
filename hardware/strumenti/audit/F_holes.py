import sys; sys.path.insert(0,"/home/claude/fp/v3/audit")
from common import *
P=load_P()
def frame(ax):
    ax=np.array(ax,float); ax/=np.linalg.norm(ax); u=np.cross(ax,[1,0,0] if abs(ax[0])<0.9 else [0,1,0]); u/=np.linalg.norm(u); return ax,u,np.cross(ax,u)
def diam(m,c,ax,rmax=15,step=0.005):
    ax,u,v=frame(ax); rs=[]
    for a in np.linspace(0,2*np.pi,24,endpoint=False):
        d=np.cos(a)*u+np.sin(a)*v; t=np.arange(0.2,rmax,step); k=m.contains(np.array(c)+np.outer(t,d))
        rs.append(t[np.argmax(k)] if k.any() else np.inf)
    rs=np.array(rs); return 2*np.median(rs), 2*rs.min()
def depth(m,mouth,ax,L=20,step=0.02,off=(0,0)):
    m=loc(m,np.array(mouth)+np.array(ax)*L/2,L/2+3); ax,u,v=frame(ax); p=np.array(mouth)+off[0]*u+off[1]*v; t=np.arange(0,L,step); k=m.contains(p+np.outer(t,ax))
    # primo materiale dopo l'imbocco
    return t[np.argmax(k)] if k.any() else None
def loc(m,c,R):
    c=np.array(c,float); return trimesh.boolean.intersection([m,B(*(c[0]-R,c[0]+R),*(c[1]-R,c[1]+R),*(c[2]-R,c[2]+R))])
def chk(name,m,c,ax,nom,tol=(0.0,0.35)):
    m=loc(m,c,nom/2+6); med,mn=diam(m,c,ax,rmax=nom/2+5,step=0.005 if nom<10 else 0.02); ok=(nom+tol[0]-0.02)<=mn and med<=nom+tol[1]
    rep(ok,"%-48s Ø nominale %.2f  misurato %.2f (min %.2f)"%(name,nom,med,mn)); return med
# piastra: fori passanti asse X (misurati a metà spessore originale X 1.5)
chk("fissaggio piastra (52.0, 18.67) nuovo",P,[1.5,52.0,18.67],[1,0,0],3.3)
for (y,z) in [(3.0,18.7),(3.0,80.4),(57.97,80.44),(49.01,49.53),(47.98,42.03),(35.0,64.53),(28.02,61.69),(28.02,37.42),(22.03,42.06)]:
    try:
        if np.hypot(y-35,z-49.55)<11.5: continue   # dentro il foro encoder
        chk("foro originale Ø3.3 (%.2f, %.2f)"%(y,z),P,[5.7 if np.hypot(y-35,z-49.55)<27 else 1.5,y,z],[1,0,0],3.3)
    except Exception as e: print("err",y,z,e)
chk("foro encoder Ø22",P,[5.7,35.0,49.55],[1,0,0],22.0)
md=chk("sede corpo encoder Ø53",P,[2.0,35.0,49.55+0.0],[1,0,0],53.0,(0,0.4))
f=depth(P,[-1,35.0+18,49.55],[1,0,0]); rep(abs(f-1-4.22)<0.05,"fondo sede encoder a X %.2f -> fondo %.2f mm (orig 3.0)"%(f-1,7.22-(f-1)))
for y in (133.0,169.5):
    for z in (-6.1,49.2): chk("fissaggio assieme (%.1f, %.1f)"%(y,z),P,[3.6,y,z],[1,0,0],3.4)
# filetti M3 nei blocchi guida (asse -Y dalla sommità 111.8)
for c in (-6.45,49.55):
    for x in (10.6,33.4):
        chk("maschio M3 tappo X %.1f Z %.2f"%(x,c),P,[x,108.0,c],[0,1,0],2.5,(-0.1,0.3))
        d=depth(P,[x,111.9,c],[0,-1,0]); rep(d is not None and d-0.1>=8.4-0.05,"   profondità %.2f mm (vite M3x12: 6 in presa)"%(d-0.1))
    chk("sede forcella (rettangolare) - larghezza minima",P,[22.22,100,c],[0,1,0],12.6,(-0.1,4.5))
# colonnina slitta
chk("maschio M3 colonnina slitta",P,[39.22,64.41-10,21.55-16.65],[0,1,0],2.5,(-0.1,0.3))
# viti coperchio (asse X nella colonna)
for zt in (40,75,133.2):
    for ty in (-14.75,14.75):
        y=64.41+zt; z=21.55-ty
        try: chk("maschio M3 coperchio Y %.1f Z %.1f"%(y,z),P,[30.0,y,z],[1,0,0],2.5,(-0.1,0.3))
        except Exception as e: print(e)
print("\n".join(OUT[-0:]) if False else "")
