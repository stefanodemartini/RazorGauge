import trimesh, numpy as np, sys
from scipy.cluster.hierarchy import fcluster, linkage
P=trimesh.load(sys.argv[1]); lim=float(sys.argv[2]) if len(sys.argv)>2 else 0.98
c=P.triangles_center; n=P.face_normals; a=P.area_faces
R=trimesh.ray.ray_pyembree.RayMeshIntersector(P); o=c-n*0.003
l,ri,_=R.intersects_location(o,-n,multiple_hits=False)
th=np.full(len(c),99.0); th[ri]=np.linalg.norm(l-o[ri],axis=1)
sel=(th<lim)&(a>1e-6)
print('area <%.2f mm: %.2f mm2'%(lim,a[sel].sum()))
if sel.sum()>1:
    pts=c[sel]; lab=fcluster(linkage(pts,'single'),3.0,'distance')
    rows=[(a[sel][lab==k].sum(), pts[lab==k].min(0), pts[lab==k].max(0), th[sel][lab==k].min()) for k in np.unique(lab)]
    for r in sorted(rows,key=lambda r:-r[0])[:30]:
        print('area %6.2f  min %.2f  X %5.1f-%5.1f Y %6.1f-%6.1f Z %6.1f-%6.1f'%(r[0],r[3],r[1][0],r[2][0],r[1][1],r[2][1],r[1][2],r[2][2]))
