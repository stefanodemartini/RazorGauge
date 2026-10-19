import trimesh, numpy as np
g=dict(trimesh.load("assieme_0.glb").geometry); P=trimesh.load("profiler.stl")
def dmin(a,b,n=3000):
    pts=a.sample(n); _,d,_=trimesh.proximity.closest_point(b,pts); return -1 if (b.is_watertight and b.contains(pts).any()) else round(d.min(),2)
W=g["ruota_encoder_200mm"]
for k in ("scheda_sensore","slitta_sensore","fascetta_2_5mm"): print(k,"↔ ruota",dmin(g[k],W),flush=True)
pts=W.sample(6000); pts=pts[(pts[:,2]<40)]; _,d,_=trimesh.proximity.closest_point(P,pts); print("pezzo (J, piastra) ↔ ruota %.2f"%d.min(),flush=True)
for i in range(1,6): print("filo",i,"↔ pezzo",dmin(g["filo_%d"%i],P,500),"↔ ruota",dmin(g["filo_%d"%i],W,500),flush=True)
