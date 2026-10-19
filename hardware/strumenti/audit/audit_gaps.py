# spessori minimi e fessure strette (MJF: fessure < 0.5 mm interne allo stesso pezzo rischiano di chiudersi)
import trimesh, numpy as np, sys
from collections import defaultdict
f=sys.argv[1]; m=trimesh.load(f); N=int(sys.argv[2]) if len(sys.argv)>2 else 40000
pts,fi=trimesh.sample.sample_surface(m,N,seed=11); nrm=m.face_normals[fi]
def cast(org,d):
    loc,ri,_=m.ray.intersects_location(org,d,multiple_hits=False); out=np.full(len(org),np.inf); out[ri]=np.linalg.norm(loc-org[ri],axis=1); return out
th=cast(pts-nrm*1e-3,-nrm)     # spessore (verso l'interno)
gp=cast(pts+nrm*1e-3,nrm)      # fessura (verso l'esterno, fino alla prossima parete dello stesso pezzo)
def clusters(mask,vals,label):
    cl=defaultdict(list)
    for p,v in zip(pts[mask],vals[mask]): cl[tuple(np.round(p/2)*2)].append(v)
    items=sorted(cl.items(),key=lambda kv:min(kv[1]))
    print("%s: %d punti in %d zone"%(label,mask.sum(),len(items)))
    for k,v in items[:25]: print("   ~(%.0f, %.0f, %.0f)  min %.2f  n %d"%(*k,min(v),len(v)))
print(f, "watertight",m.is_watertight,"corpi",len(m.split(only_watertight=False)),"vol %.2f cm3"%(m.volume/1000))
clusters(th<1.0,th,"SPESSORE < 1.0 mm")
clusters(gp<0.5,gp,"FESSURA < 0.5 mm")
