import sys; sys.path.insert(0,"/home/claude/fp/v3")
import trimesh, numpy as np
T=trimesh.transformations
g=dict(trimesh.load("assieme_0.glb").geometry); P=trimesh.load("profiler.stl")
# 1) simmetria
print("interasse laser -> ruota %.2f  laser -> rullo inferiore %.2f  laser -> spintore lato misura %.2f"%(49.55-21.55, 21.55-(-6.45), 21.55-(-6.45)),flush=True)
# 2) linea Ø3 e Ø0.5 da Z -30 a 76
for dia in (0.5,3.0):
    c=trimesh.creation.cylinder(radius=dia/2-0.03,height=106,sections=48); c.apply_translation([22.22,66.91+dia/2,23])
    print("linea Ø%.1f Z -30..76 ∩ pezzo %.4f"%(dia,trimesh.boolean.intersection([c,P]).volume),flush=True)
# 3) rullo inferiore: appoggio linea e perno nel braccio
R=g["rullo_inferiore_spostato"]; print("cima rullo inferiore Y %.2f (fondo linea 66.91), Z centro %.2f"%(R.bounds[1][1],(R.bounds[0][2]+R.bounds[1][2])/2),flush=True)
xs=np.arange(0,32,0.1); c_=P.contains(np.c_[xs,np.full_like(xs,58.91),np.full_like(xs,-6.45)])
print("materiale del braccio sull'asse del perno (X):", [round(v,1) for v in xs[c_][[0,-1]]] if c_.any() else None,flush=True)
pts=R.sample(4000); _,d,_=trimesh.proximity.closest_point(P,pts); print("rullo inferiore ↔ pezzo (braccio) gioco %.2f"%d.min(),flush=True)
# 4) J lato rullo: giochi
def dmin(a,b,n=3000):
    pts=a.sample(n); _,d,_=trimesh.proximity.closest_point(b,pts); return -1 if (b.is_watertight and b.contains(pts).any()) else round(d.min(),2)
Jb=trimesh.creation.box([24,9,12]); Jb.apply_translation([18.5,68.8,7.6]); J=trimesh.boolean.intersection([P,Jb])
print("J lato rullo Z %.2f-%.2f"%(J.bounds[0][2],J.bounds[1][2]),flush=True)
print("J ↔ rullo inferiore",dmin(R,J),"↔ scheda",dmin(g["scheda_sensore"],J),flush=True)
from forks import place
def cylX(x0,x1,y,z,r,sec=64):
    c=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=sec); c.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
w=99
for d in (-1,0,1,3,5):
    w=min(w,dmin(cylX(17.22,27.22,66.91+d+8,-6.45,8),J,1500))
print("J ↔ rullo spintore (tutta la corsa) %.2f"%w,flush=True)
