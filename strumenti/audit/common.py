import trimesh, numpy as np, sys
sys.path.insert(0,"/home/claude/fp/v3")
T=trimesh.transformations
V="/home/claude/fp/v3/"
def B(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box([x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
def load_P(): return trimesh.load(V+"profiler.stl")
def load_G(n=0):
    g={k:v for k,v in trimesh.load(V+"assieme_%d.glb"%n).geometry.items()}
    for k in g: g[k].merge_vertices(digits_vertex=4)
    return g
def crop(m,bounds,pad=2.0):
    lo=np.array(bounds[0])-pad; hi=np.array(bounds[1])+pad
    return trimesh.boolean.intersection([m,B(lo[0],hi[0],lo[1],hi[1],lo[2],hi[2])])
def inter(a,b):
    if a.is_empty or b.is_empty: return 0.0
    if np.any(a.bounds[0]>b.bounds[1]) or np.any(b.bounds[0]>a.bounds[1]): return 0.0
    try: return trimesh.boolean.intersection([a,b]).volume
    except Exception:
        pts=a.sample(4000); return float(b.contains(pts).mean()*a.volume) if b.is_watertight else float('nan')
Mt=T.translation_matrix([22.22,64.41,21.55])@T.rotation_matrix(-np.pi/2,[1,0,0])
OUT=[]
def rep(ok,txt):
    s=("OK  " if ok else "!!  ")+txt; OUT.append(s); print(s,flush=True)
