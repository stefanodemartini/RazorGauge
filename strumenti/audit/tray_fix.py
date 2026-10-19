import trimesh, numpy as np
T=trimesh.transformations
Mt=T.translation_matrix([22.22,64.41,21.55])@T.rotation_matrix(-np.pi/2,[1,0,0])
P=trimesh.load("profiler.stl")
box=trimesh.creation.box([50,22,40]); box.apply_translation([22,55,15])       # zona slitta in coordinate piastra
P=trimesh.boolean.intersection([P,box]); P.apply_transform(np.linalg.inv(Mt))
R=trimesh.load("tray.stl")
def probe(m,p0,d,L=12,step=0.01):
    t=np.arange(0,L,step); q=np.array(p0,float)+np.outer(t,d); c=m.contains(q); return round(float(t[np.argmax(c)]),2) if c.any() else None
print("== linguetta posteriore nella sede ==",flush=True)
print("gioco sotto", probe(P,[-15,3.5,-5.501],[0,0,-1]), " sopra", probe(P,[-15,3.5,-3.499],[0,0,1]))
print("gioco lati", probe(P,[-15,-3.501,-4.5],[0,-1,0]), probe(P,[-15,10.501,-4.5],[0,1,0]))
print("gioco in fondo", probe(P,[-17.301,3.5,-4.5],[-1,0,0]))
xs=np.arange(-17.3,-10,0.1); up=P.contains(np.c_[xs,np.full_like(xs,3.5),np.full_like(xs,-3.2)]); dn=P.contains(np.c_[xs,np.full_like(xs,3.5),np.full_like(xs,-5.8)])
both=xs[up&dn]; print("linguetta guidata sopra e sotto da tx %.1f a %.1f -> presa %.1f mm (linguetta lunga 4.8)"%(both.min(),both.max(),both.max()-both.min()+0.1),flush=True)
print("== appoggio anteriore e vite ==",flush=True)
pts=np.array([[17.0+dx,16.65+dy,-5.55] for dx in np.arange(-3.2,3.21,0.4) for dy in np.arange(-2.6,2.61,0.4)])
tray_under=R.contains(pts+[0,0,0.1]); col=P.contains(pts)
print("sotto la linguetta anteriore c'e la colonnina in %d punti su %d della linguetta"%((tray_under&col).sum(),tray_under.sum()))
print("cima colonnina a tz", round(-5.55+ (probe(P,[15.0,15.0,-5.3],[0,0,-1],1,0.002) or 0)*-1 -0.25+0.25,3), "(faccia inferiore slitta -5.50)")
r=[probe(P,[17.0,16.65,-8.0],[np.cos(a),np.sin(a),0],4,0.005) for a in np.linspace(0,2*np.pi,24,endpoint=False)]
fondo=-8.0-probe(P,[17.0,16.65,-8.0],[0,0,-1],12)
print("foro colonnina Ø %.2f, fondo a tz %.2f -> lunghezza filettabile %.1f mm"%(2*np.median(r),fondo,-5.5-fondo))
def wall(m,c,z,r0):
    out=[]
    for a in np.linspace(0,2*np.pi,24,endpoint=False):
        t=np.arange(r0+0.05,7,0.01); q=np.c_[c[0]+t*np.cos(a),c[1]+t*np.sin(a),np.full_like(t,z)]; k=m.contains(q)
        out.append(t[np.argmin(k)]-r0 if (~k).any() else 9)
    return min(out)
print("parete minima attorno al foro nella colonnina %.2f mm"%wall(P,(17.0,16.65),-8.0,1.25))
print("materiale minimo attorno al foro nella linguetta %.2f mm"%wall(R,(17.0,16.65),-4.5,1.7))
rr=[probe(R,[17.0,16.65,-4.5],[np.cos(a),np.sin(a),0],4,0.005) for a in np.linspace(0,2*np.pi,24,endpoint=False)]
print("foro linguetta Ø %.2f"%(2*np.median(rr)))
d=probe(P,[15.0,15.0,-5.0],[0,0,-1],2,0.002); print("cima colonnina tz %.3f (faccia inferiore slitta -5.500)"%(-5.0-d))
d=probe(P,[-15.0,3.5,-5.0],[0,0,-1],2,0.002); print("fondo sede posteriore tz %.3f"%(-5.0-d))
# trave e colonnina: sezioni
print("trave: sezione 2.5 x 5 mm, lunga %.1f mm dalla piastra alla colonnina"%(13-(-19.42)))
