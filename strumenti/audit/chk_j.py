import sys; sys.path.insert(0,"/home/claude/fp/v3")
import trimesh, numpy as np
from forks import place
T=trimesh.transformations
P=trimesh.load("profiler.stl")
def B(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box([x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
Jzone=trimesh.boolean.intersection([P, trimesh.boolean.union([B(6.95,30,64.5,73,4.0,13.5),B(6.95,30,64.5,73,28.5,39)])])
print("volume J", round(Jzone.volume,1))
def cylX(x0,x1,y,z,r,sec=96):
    c=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=sec); c.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0])); c.apply_translation([(x0+x1)/2,y,z]); return c
def dmin(a,b,n=6000):
    pts=a.sample(n); _,d,_=trimesh.proximity.closest_point(b,pts); return -1 if b.contains(pts).any() else d.min()
worst={}
for c in (-6.45,49.55):
    for d in (-1,0,0.5,1,2,3,4,5):
        yr=66.91+d+8
        for nm,m in (("rullo spintore",cylX(17.22,27.22,yr,c,8)),("forcella",place(c,d)),("testa/dado",trimesh.util.concatenate([cylX(10.7,14.22,yr,c,4.62),cylX(30.22,34.22,yr,c,4.62)]))):
            v=dmin(m,Jzone,1500); key=(c,nm); worst[key]=min(worst.get(key,99),v)
for k,v in worst.items(): print("J ↔ %s (Z %.2f): gioco min su tutta la corsa %.2f"%(k[1],k[0],v))
g=trimesh.load("assieme_0.glb").geometry
print("J ↔ ruota %.2f"%dmin(g["ruota_encoder_200mm"],Jzone,6000))
print("J ↔ rullo inferiore %.2f"%dmin(g["rullo_inferiore_spostato"],Jzone,4000))
S=g["scheda_sensore"]; pts0=S.sample(12000); pts0=pts0[pts0[:,1]>62.4]; w=99
for dx in range(0,46,2):
    _,dd,_=trimesh.proximity.closest_point(Jzone,pts0+[dx,0,0]); w=min(w,dd.min())
print("J ↔ scheda durante l'estrazione %.2f"%w)
for dia in (0.5,3.0):
    cc=trimesh.creation.cylinder(radius=dia/2-0.02,height=60,sections=48); cc.apply_translation([22.22,66.91+dia/2,21])
    print("linea Ø%.1f ∩ J"%dia, round(trimesh.boolean.intersection([Jzone,cc]).volume,4))
