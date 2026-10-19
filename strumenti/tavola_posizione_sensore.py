import trimesh, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.image as mpimg
from shapely.geometry import Polygon
from shapely.ops import unary_union
T=trimesh.transformations
tw=trimesh.load('v_tower.stl')
s=trimesh.load('sensor.stl'); s.apply_transform(T.rotation_matrix(np.pi,[1,0,0])); s.apply_translation([-12.6,15.5,0.2])
GREY='#b9bcc2'; EDGE='#6b6f76'; OR='#ff5a1f'; RED='#d0021b'; BLUE='#1f5fbf'

def proj(mesh, drop):   # silhouette projection along axis 'drop' (0=x,1=y,2=z)
    keep=[i for i in range(3) if i!=drop]
    polys=[]
    for f in mesh.triangles:
        p=Polygon(f[:,keep])
        if p.area>1e-6: polys.append(p)
    return unary_union(polys)
def sec(mesh, n, o, keep):
    ss=mesh.section(plane_origin=o, plane_normal=n)
    out=[]
    if ss is None: return out
    for e in ss.discrete: out.append(e[:,keep])
    return out
def fillgeom(ax,g,**kw):
    gs=[g] if g.geom_type=='Polygon' else list(g.geoms)
    for p in gs:
        ax.fill(*p.exterior.xy,**kw)
        for h in p.interiors: ax.fill(*h.xy,color='white',lw=0)
def dim(ax,p1,p2,txt,off=(0,0),col=BLUE,fs=9):
    ax.annotate('',xy=p1,xytext=p2,arrowprops=dict(arrowstyle='<->',color=col,lw=1))
    ax.text((p1[0]+p2[0])/2+off[0],(p1[1]+p2[1])/2+off[1],txt,color=col,fontsize=fs,ha='center',va='center',
            bbox=dict(fc='white',ec='none',pad=1))

fig=plt.figure(figsize=(17,12))
gsp=fig.add_gridspec(2,3,height_ratios=[1,1])
# ---- 3D images
for k,(fn,t) in enumerate([('hl_iso.png','Vista 3D dal fronte'),('hl_below.png','Vista 3D da sotto (connettore sul retro)')]):
    ax=fig.add_subplot(gsp[0,k]); ax.imshow(mpimg.imread(fn)[40:1060,60:1340]); ax.axis('off'); ax.set_title(t,fontsize=12)

# ---- Pianta da sotto (XY), tower sezionata a z=2.75 + guance
ax=fig.add_subplot(gsp[0,2])
tsec=sec(tw,[0,0,1],[0,0,2.75],[0,1])
for e in tsec: ax.fill(e[:,0],e[:,1],color=GREY,ec=EDGE,lw=.6)
b=s.bounds
ax.add_patch(plt.Rectangle((b[0][0],b[0][1]),b[1][0]-b[0][0],b[1][1]-b[0][1],fc=OR,alpha=.35,ec=OR,lw=2))
ax.add_patch(plt.Rectangle((-5.5,-2),11,4,fc=OR,ec='k',lw=1))            # finestra chip
ax.add_patch(plt.Rectangle((-7.5,2.4),15,7.1,fc='none',ec=OR,lw=1.2,ls='--'))  # connettore (retro)
for x in [-10.6,10.6]:
    for y in [-6.5,0,6.5]: ax.add_patch(plt.Circle((x,y),1,fc='white',ec='k',lw=.8))
ax.plot(0,0,'+',color=RED,ms=16,mew=2); ax.plot([-4.07,4.07],[0,0],color=RED,lw=3)
ax.axvline(-35.4,color='k',lw=2); ax.text(-35,20,'PIANO\nfissaggio',fontsize=8,va='top')
ax.axhspan(-30,30,xmin=0,xmax=0,alpha=0)
ax.plot([-1.75,-1.75],[-30,30],':',color='gold'); ax.plot([1.75,1.75],[-30,30],':',color='gold'); ax.text(2.2,-27,'cavo (lungo Y)',color='#a08000',fontsize=8)
dim(ax,(-35.4,-24),(0,-24),'35.4')
dim(ax,(-12.6,19),(12.6,19),'25.2')
dim(ax,(16.5,-8.5),(16.5,15.5),'24',off=(1.8,0))
dim(ax,(-10.6,-13),(10.6,-13),'fori 21.2 (asole 20÷21.2)',fs=8)
dim(ax,(14,0),(14,15.5),'15.5',off=(1.8,0),fs=8)
ax.text(0.5,-4.2,'chip = asse fascio',color=RED,fontsize=8)
ax.set_aspect('equal'); ax.set_xlim(-38,22); ax.set_ylim(-30,30); ax.grid(alpha=.25)
ax.set_title('Pianta (sez. Z=2.75): scheda arancio',fontsize=12); ax.set_xlabel('X  (← piano | fronte →)'); ax.set_ylabel('Y')

# ---- Sezione laterale XZ (Y=0)
ax=fig.add_subplot(gsp[1,0:2])
for e in sec(tw,[0,1,0],[0,0,0],[0,2]): ax.fill(e[:,0],e[:,1],color=GREY,ec=EDGE,lw=.6)
for e in sec(s,[0,1,0],[0,0.01,0],[0,2]): ax.fill(e[:,0],e[:,1],color=OR,ec='k',lw=.6)
ax.add_patch(plt.Circle((0,2.5+1.5),1.5,color='gold',ec='k')); ax.add_patch(plt.Circle((0,2.5+1),1,color='#e0b000'))
ax.axvline(0,color=RED,lw=1,ls='-.'); ax.axvline(-35.4,color='k',lw=2)
ax.axhline(0,color=RED,lw=.6,ls=':')
dim(ax,(-35.4,-6),(0,-6),'35.4 piano ↔ asse fascio')
dim(ax,(20,0),(20,2.5),'',fs=8); ax.text(21,1.25,' 2.5  appoggio cavo ↔ chip',fontsize=8.5,va='center',color=BLUE)
dim(ax,(20,-1.9),(20,0),'',fs=8); ax.text(21,-0.95,' 1.9  chip sopra PCB',fontsize=8.5,va='center',color=BLUE)
dim(ax,(20,-9.15),(20,-3.5),'',fs=8); ax.text(21,-6.3,' 5.65  connettore XH (retro)',fontsize=8.5,va='center',color=BLUE)
ax.text(-1,0.35,'Z=0 faccia chip',color=RED,fontsize=8,ha='right')
ax.set_xlim(-40,45); ax.set_ylim(-14,24); ax.set_aspect('equal'); ax.grid(alpha=.25)
ax.set_title('Sezione laterale Y=0 (zona sensore)',fontsize=12); ax.set_xlabel('X'); ax.set_ylabel('Z')

# ---- Sezione frontale YZ (X=0)
ax=fig.add_subplot(gsp[1,2])
for e in sec(tw,[1,0,0],[0,0,0],[1,2]): ax.fill(e[:,0],e[:,1],color=GREY,ec=EDGE,lw=.6)
for e in sec(s,[1,0,0],[0.01,0,0],[1,2]): ax.fill(e[:,0],e[:,1],color=OR,ec='k',lw=.6)
ax.plot([-35,35],[4,4],color='gold',lw=6,solid_capstyle='butt',alpha=.8); ax.text(-27,5.5,'cavo',color='#a08000',fontsize=8)
ax.axvline(0,color=RED,lw=1,ls='-.'); ax.axhline(0,color=RED,lw=.6,ls=':')
dim(ax,(-8.5,-12),(15.5,-12),'scheda 24 (chip a 15.5 dal bordo)',fs=8)
ax.set_xlim(-30,30); ax.set_ylim(-16,22); ax.set_aspect('equal'); ax.grid(alpha=.25)
ax.set_title('Sezione frontale X=0',fontsize=12); ax.set_xlabel('Y'); ax.set_ylabel('Z')
fig.suptitle('Posizione del Sensor Assembly nella torre  —  origine: centro finestra chip (asse fascio), faccia chip Z=0',fontsize=14,weight='bold')
plt.tight_layout(rect=[0,0,1,0.96]); plt.savefig('posizione_sensore.png',dpi=110)
