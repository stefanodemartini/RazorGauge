# Tappo removibile dei blocchi guida delle forcelle (2 pezzi uguali): sostituisce il cappello integrato.
# Stesso spessore (6 mm) e stessa quota (Y 111.8-117.8) del supporto originale, foro Ø5.5 per lo stelo M5, centraggio con
# un dente 16.2 x 12.2 x 1.5 nella sede, 2 viti M3 x 12 nelle spalle del blocco. Uscita: tappo in coordinate piastra (Z del
# blocco lato rullo) e copia orientata per la stampa.
import trimesh, numpy as np, sys
T=trimesh.transformations
XB=22.22; SX,SZ=16.6,12.6; GZ=8.15; GTOP=111.8; CAPT=6.0; TAP_X=(10.6,33.4); XF=TAP_X[1]+2.75; XBK=7.32
def B(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box([x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
def cylY(x,z,r,y0,y1,sec=48):
    c=trimesh.creation.cylinder(radius=r,height=y1-y0,sections=sec); c.apply_transform(T.rotation_matrix(np.pi/2,[1,0,0])); c.apply_translation([x,(y0+y1)/2,z]); return c
def tappo(c):
    body=trimesh.boolean.union([B(XBK,XF,GTOP,GTOP+CAPT,c-GZ,c+GZ), B(XB-SX/2+0.2,XB+SX/2-0.2,GTOP-1.5,GTOP+0.01,c-SZ/2+0.2,c+SZ/2-0.2)])
    cuts=[cylY(XB,c,2.75,GTOP-2,GTOP+CAPT+1)]+[cylY(x,c,1.7,GTOP-1,GTOP+CAPT+1) for x in TAP_X]
    # smussi di stampa: spigoli verticali anteriori 0.7 (uguali a quelli delle spalle del blocco), perimetro della faccia
    # superiore 0.5, invito 0.3 sul bordo inferiore del dente di centraggio. Faccia inferiore (appoggio sul blocco) e fori: vivi.
    YT=GTOP+CAPT
    for sz in (-1,1): cuts.append(wedge("y",(XF,c+sz*GZ),(1,sz),0.7,GTOP-0.1,YT+0.1))
    for sz in (-1,1): cuts.append(wedge("x",(YT,c+sz*GZ),(1,sz),0.5,XBK-0.1,XF+0.1))
    cuts.append(wedge("z",(XBK,YT),(-1,1),0.5,c-GZ-0.1,c+GZ+0.1))   # lato anteriore (XF) vivo: parete 1.05 davanti al foro M3
    x0,x1,z0,z1=XB-SX/2+0.2,XB+SX/2-0.2,c-SZ/2+0.2,c+SZ/2-0.2; yb=GTOP-1.5
    for sz,zz in ((-1,z0),(1,z1)): cuts.append(wedge("x",(yb,zz),(-1,sz),0.3,x0-0.1,x1+0.1))
    for sx,xx in ((-1,x0),(1,x1)): cuts.append(wedge("z",(xx,yb),(sx,-1),0.3,z0-0.1,z1+0.1))
    return trimesh.boolean.difference([body,trimesh.boolean.union(cuts)])
def wedge(axis,corner,sgn,L,a0,a1):
    """prisma triangolare che smussa di L lo spigolo parallelo ad 'axis' nel punto corner=(u,v), sgn=(su,sv) verso l'esterno.
    piano (u,v): axis y -> (x,z); axis x -> (y,z); axis z -> (x,y)"""
    import shapely.geometry as sg
    u,v=corner; su,sv=sgn
    tri=sg.Polygon([(u+0.3*su,v+0.3*sv),(u-(L+0.3)*su,v+0.3*sv),(u+0.3*su,v-(L+0.3)*sv)])
    w=trimesh.creation.extrude_polygon(tri,a1-a0)       # (u,v) nel piano XY, estrusione lungo Z da 0
    P={"y":[[1,0,0,0],[0,0,1,a0],[0,1,0,0],[0,0,0,1]],      # (u,v,t) -> (x=u, y=a0+t, z=v)
       "x":[[0,0,1,a0],[1,0,0,0],[0,1,0,0],[0,0,0,1]],      # (u,v,t) -> (x=a0+t, y=u, z=v)
       "z":[[1,0,0,0],[0,1,0,0],[0,0,1,a0],[0,0,0,1]]}[axis]
    w.apply_transform(np.array(P,dtype=float))
    if w.volume<0: w.invert()
    return w
if __name__=="__main__":
    import io
    t=tappo(-6.45)
    for dig in (5,4,6,3):
        q=t.copy(); q.merge_vertices(digits_vertex=dig); q.update_faces(q.nondegenerate_faces()); q.remove_unreferenced_vertices()
        b=io.BytesIO(); q.export(b,file_type="stl"); b.seek(0); r=trimesh.load(b,file_type="stl")
        if r.is_watertight and r.is_volume and len(r.split(only_watertight=False))==1: t=q; break
    t.export("tappo_blocco_guida.stl")
    p=t.copy(); p.apply_translation(-p.bounds[0]); p.export("tappo_blocco_guida_stampa.stl")
    print("tappo", t.is_watertight, round(t.volume/1000,2), t.extents.round(2).tolist())
