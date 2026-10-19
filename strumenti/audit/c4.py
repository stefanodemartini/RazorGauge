import trimesh, numpy as np
g=dict(trimesh.load("assieme_0.glb").geometry); g["pezzo_unico"]=trimesh.load("profiler.stl")
def corridor(p0,dirv,L,r,skip=()):
    hits=set(); dirv=np.array(dirv,float); p0=np.array(p0,float)
    perp=np.cross(dirv,[1,0,0] if abs(dirv[0])<0.9 else [0,1,0]); perp/=np.linalg.norm(perp); perp2=np.cross(dirv,perp)
    lo=np.minimum(p0,p0+dirv*L)-r; hi=np.maximum(p0,p0+dirv*L)+r
    for k,m in g.items():
        if k in skip or not m.is_watertight: continue
        if np.any(m.bounds[0]>hi) or np.any(m.bounds[1]<lo): continue
        for rr in (0,r):
            for a in (np.linspace(0,2*np.pi,9)[:-1] if rr else [0]):
                q=p0+rr*(np.cos(a)*perp+np.sin(a)*perp2)+np.outer(np.arange(0,L,0.5),dirv)
                if m.contains(q).any(): hits.add(k); break
    return sorted(hits)
ZM=21.55
print("vite slitta dall'alto:", corridor([39.22,61.2,ZM-16.65],[0,1,0],150,2.75,skip=("vite_M3_slitta",)) or "libero",flush=True)
print("vite carrello dal davanti:", corridor([36.4,92.66,ZM-6.5],[1,0,0],60,2.8,skip=("vite_M3_carrello",)) or "libero",flush=True)
for y in (104.41,139.41,197.41):
    for z in (ZM-14.75,ZM+14.75): print("vite coperchio",y,round(z,2), corridor([36.4,y,z],[1,0,0],60,2.8) or "libero",flush=True)
for (y,z) in ((133,-6.1),(133,49.2),(169.5,-6.1),(169.5,49.2)): print("fissaggio",y,z, corridor([7.4,y,z],[1,0,0],70,3.5) or "libero",flush=True)
for c in (-6.45,49.55):
    for x in (10.6,33.4): print("vite tappo",x,c, corridor([x,117.9,c],[0,1,0],60,2.8,skip=("viti_tappo_lato_misura","viti_tappo_sulla_ruota")) or "libero",flush=True)
    print("estrazione forcella+stelo dall'alto",c, corridor([22.22,118,c],[0,1,0],60,4.0,skip=tuple(k for k in g if "forcella" in k or "tappo" in k)) or "libero",flush=True)
