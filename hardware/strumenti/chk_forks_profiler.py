import sys; sys.path.insert(0,"/home/claude/fp/v3")
import trimesh, numpy as np, math
from forks import place
T=trimesh.transformations
P=trimesh.load("profiler.stl")
sc=trimesh.load("assieme_0.glb"); g=sc.geometry
others={k:g[k] for k in ("pezzo_unico","coperchio","slitta_sensore","scheda_sensore","ruota_encoder_200mm","rullo_inferiore_spostato","carrello")}
def boltnut(yr,z):
    hx=trimesh.creation.cylinder(radius=4.62,height=3.5,sections=6); hx.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); hx.apply_translation([22.22-8-1.75,yr,z])
    nt=trimesh.creation.cylinder(radius=4.62,height=4.0,sections=6); nt.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); nt.apply_translation([22.22+8+2.0,yr,z])
    sh=trimesh.creation.cylinder(radius=2.5,height=21.5,sections=24); sh.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); sh.apply_translation([22.22+1.75,yr,z])
    # rotazione del dado/testa: inviluppo cilindrico (caso peggiore)
    hx2=trimesh.creation.cylinder(radius=4.62,height=3.5,sections=48); hx2.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); hx2.apply_translation([22.22-8-1.75,yr,z])
    nt2=trimesh.creation.cylinder(radius=4.62,height=4.0,sections=48); nt2.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); nt2.apply_translation([22.22+8+2.0,yr,z])
    return trimesh.util.concatenate([hx2,nt2,sh])
for c in (-6.45,49.55):
    for d in (-1,0.5,2,3,4,4.5,5,5.5):
        yr=66.91+d+8; f=place(c,d); bn=boltnut(yr,c)
        hits=[]
        for k,o in others.items():
            for nm,m in (("forcella",f),("bullone/dado",bn)):
                pts=m.sample(900); _,dd,_=trimesh.proximity.closest_point(o,pts)
                ins=o.contains(pts).any() if o.is_watertight else False
                if ins or dd.min()<0.1: hits.append("%s↔%s %s"%(nm,k,"DENTRO" if ins else "%.2f"%dd.min()))
        armtop=yr+13; eng=max(0,armtop-85.0)
        print("c=%6.2f d=%4.1f  guida rettangolare in presa %.1f mm  %s"%(c,d,eng,"; ".join(hits) if hits else "libera"))
