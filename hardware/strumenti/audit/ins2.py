import sys; sys.path.insert(0,"/home/claude/fp/v3")
import trimesh, numpy as np
from forks import place
P=trimesh.load("profiler.stl"); TP=trimesh.load("tappo_blocco_guida.stl")
def B(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box([x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
for c in (-6.45,49.55):
    crop=trimesh.boolean.intersection([P,B(5,40,60,130,c-15,c+15)])
    f0=place(c,-1.0); need=111.8-f0.bounds[0][1]+0.5
    hit=None
    for s in np.arange(0,need+0.01,0.5):
        f=f0.copy(); f.apply_translation([0,s,0])
        if trimesh.boolean.intersection([f,crop]).volume>1e-3: hit=s;break
    print("Z %.2f: estrazione/inserimento DALL'ALTO (tappo tolto) per %.1f mm: %s"%(c,need,"LIBERO" if hit is None else "urta a %.1f"%hit),flush=True)
    t=TP.copy(); t.apply_translation([0,0,c+6.45])
    print("   tappo ∩ pezzo %.4f"%trimesh.boolean.intersection([t,crop]).volume)
    for d in (-1,0,3,5):
        f=place(c,d); print("   tappo ∩ forcella (d=%g) %.4f"%(d,trimesh.boolean.intersection([t,f]).volume))
    # foro stelo allineato
    print("   foro stelo nel tappo libero sull'asse:", not t.contains(np.c_[np.full(50,22.22),np.linspace(110,118,50),np.full(50,c)]).any())
    # dente nel tappo dentro la sede: gioco
    for dz in (-6.15,6.15):
        q=np.c_[np.full(20,22.22),np.linspace(110.4,111.7,20),np.full(20,c+dz*0.999)]
        print("   parete sede a dz %+.2f: tappo la tocca?"%dz, t.contains(q).any())
    # viti del tappo: fori allineati con le spalle
    for x in (10.6,33.4):
        q=np.c_[np.full(80,x),np.linspace(102,117.7,80),np.full(80,c)]
        print("   asse vite X %.1f: pezzo pieno da Y %.2f, tappo pieno? %s"%(x, q[P.contains(q)][:,1].max() if P.contains(q).any() else -1, t.contains(q).any()))
        fb=q[(~P.contains(q))&(q[:,1]<111.8)][:,1]; print("      foro nel pezzo da Y %.2f a 111.8 -> profondita %.1f"%(fb.min(),111.8-fb.min()))
