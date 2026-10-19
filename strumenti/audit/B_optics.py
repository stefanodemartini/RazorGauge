import sys; sys.path.insert(0,"/home/claude/fp/v3/audit")
from common import *
P=load_P(); g=load_G(0)
Pc=crop(P,[[8,74,0],[36,203,36]],0)
Pt=Pc.copy(); Pt.apply_transform(np.linalg.inv(Mt))          # colonna in coordinate torre
def probe(m,p0,d,L,step=0.005):
    t=np.arange(0,L,step); q=np.array(p0,float)+np.outer(t,d); c=m.contains(q); return float(t[np.argmax(c)]) if c.any() else None
# L1: sede
r=[probe(Pt,[0,0,105.2],[np.cos(a),np.sin(a),0],10) for a in np.linspace(0,2*np.pi,36,endpoint=False) if np.cos(a)<0.3]
rep(abs(2*min(r)-12.77)<0.1,"Sede L1: Ø %.2f (lente Ø12.47 → gioco %.2f)"%(2*min(r),2*min(r)-12.47))
up=probe(Pt,[-5.5,0,105.2],[0,0,1],5); dn=probe(Pt,[-5.5,0,105.2],[0,0,-1],5)
rep(abs(up+dn-3.41)<0.05,"Sede L1: altezza %.2f (lente 3.11 → gioco %.2f)"%(up+dn,up+dn-3.11))
ok=True
for dx in np.arange(0,16,0.5):
    l=trimesh.creation.cylinder(radius=12.47/2,height=3.11,sections=64); l.apply_translation([dx,0,105.2])
    if inter(l,Pt)>1e-3: ok=False
rep(ok,"L1 si infila dal fronte fino in sede")
# laser
r=[probe(Pt,[0,0,122.2],[np.cos(a),np.sin(a),0],5) for a in np.linspace(0,2*np.pi,36,endpoint=False)]
rep(abs(2*min(r)-4.3)<0.08,"Sede laser: Ø %.2f (laser Ø4 → gioco %.2f)"%(2*min(r),2*min(r)-4.0))
b=probe(Pt,[1.8,0,121],[0,0,-1],5); rep(b is not None and abs(121-b-120.2)<0.05,"Battuta laser a z %.2f (faccia laser 120.2), foro fascio sotto Ø3"%(121-b))
ok=True
for dz in np.arange(0,25,0.5):
    l=trimesh.creation.cylinder(radius=1.98,height=14,sections=48); l.apply_translation([0,0,120.2+7+dz])
    if inter(l,Pt)>1e-3: ok=False; break
rep(ok,"Laser Ø4 si infila dall'alto (foro Ø5 nel tappo superiore)")
# fascio
beam=[trimesh.creation.cylinder(radius=6.5,height=22.2,sections=64), trimesh.creation.cone(radius=6.5,height=105.2-1.6-26.0,sections=64)]
beam[0].apply_translation([0,0,0.3+11.1]); beam[1].apply_translation([0,0,26.0])
L=g["coperchio"].copy(); L.apply_transform(np.linalg.inv(Mt)); C=g["carrello"].copy(); C.apply_transform(np.linalg.inv(Mt))
v=sum(inter(bm,m) for bm in beam for m in (Pt,L))
rep(v<1e-3,"Fascio Ø13 (chip→L2) e cono L2→L1 liberi da pezzo e coperchio")
cl=trimesh.creation.cylinder(radius=6.95,height=8,sections=64); cl.apply_translation([0,0,24.5])
rep(inter(cl,C)<1e-3,"Foro libero del carrello ≥ Ø14 (fascio utile L2)")
# coperchio sul pezzo, costola nella scanalatura del blocco L1
rep(inter(L,Pt)<1e-3,"Coperchio ↔ colonna: nessuna compenetrazione (costola nella scanalatura del blocco L1)")
