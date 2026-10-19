import sys; sys.path.insert(0,"/home/claude/fp/v3/audit")
from common import *
g=trimesh.load(V+"assieme_0.glb").geometry; P=load_P()
for nm in ("scheda_sensore","slitta_sensore","fascetta_2_5mm"):
    part=g[nm]; lo,hi=part.bounds; Pc=trimesh.boolean.intersection([P,B(lo[0]-2,hi[0]+48,lo[1]-2,hi[1]+2,lo[2]-2,hi[2]+2)])
    p0=part.sample(2500); w=99
    for dx in np.arange(0,46,1.0):
        q=p0+[dx,0,0]
        if Pc.contains(q).any(): w=-1; print(nm,"COLLISIONE a dx",dx); break
        _,d,_=trimesh.proximity.closest_point(Pc,q); w=min(w,d.min())
    rep(w>=0.4,"%s in estrazione 0-45 mm: gioco min %.2f"%(nm,w))
