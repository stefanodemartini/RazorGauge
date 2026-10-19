import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np, math
from matplotlib.patches import Polygon, Circle
D=200/math.pi; R=D/2; G=0.0; GB=2.4; W=10; HL=6.78; HR=9; B=3; PR1=R-4; PD=3.5; PF=6.5; L=HL+W
fig=plt.figure(figsize=(11.7,8.3))
ax=fig.add_axes([0.04,0.12,0.5,0.76]); ax.set_aspect('equal'); ax.axis('off')
# sezione assiale: asse orizzontale = z, verticale = r (sopra e sotto)
def prof(s):
    pts=[(0,B),(0,HR),(HL,HR),(HL,PR1),(HL+0.0,PR1),(HL,R-0.5),(HL+0.5,R),(L-0.5,R),(L,R-0.5),(L,PR1),(L-PD,PR1),(L-PD,PF),(L,PF),(L,B)]
    # tasca lato encoder: da z=HL a HL+PD tra r=HR e PR1
    pts=[(0,B),(0,HR),(HL+PD,HR),(HL+PD,PR1),(HL,PR1),(HL,R-0.5),(HL+0.5,R),(L-0.5,R),(L,R-0.5),(L,PR1),(L-PD,PR1),(L-PD,PF),(L,PF),(L,B)]
    return [(z,s*r) for z,r in pts]
for s in (1,-1): ax.add_patch(Polygon(prof(s),closed=True,fc='#c9d3dd',ec='k',lw=1,hatch='///'))
ax.plot([-4,L+4],[0,0],'k-.',lw=0.6)
def dim(x0,y0,x1,y1,t,off=(0,0),rot=0):
    ax.annotate('',(x0,y0),(x1,y1),arrowprops=dict(arrowstyle='<->',lw=0.7))
    ax.text((x0+x1)/2+off[0],(y0+y1)/2+off[1],t,ha='center',va='center',fontsize=8,rotation=rot,bbox=dict(fc='white',ec='none',pad=0.5))
dim(-6,-R,-6,R,'Ø63.66 ±0.10\n(circonf. 200.00)',(-5,0),90)
dim(HL,R+4,L,R+4,'10.00')
dim(0,R+9,L,R+9,'16.78')
dim(0,-R-4,HL,-R-4,'6.78')
dim(L+3,-B,L+3,B,'Ø6.05 ±0.05',(-3.5,0),90)
dim(L+9,-PR1,L+9,PR1,'Ø55.66',(4,0),90)
dim(HL+PD,-PF-3,L-PD,-PF-3,'3.0')
dim(-2.5,-HR,-2.5,HR,'Ø18',(-3,0),90)
ax.plot([HL/2,HL/2],[HR,HR+3],'k-',lw=0.6); ax.text(-3,HR+5,'2 × M3 grano\na 90°, z 3.39',ha='right',fontsize=7.5)
ax.text(HL+W/2,R+14,'MEZZERIA = linea della coda di topo',ha='center',fontsize=7.5,color='#c23a2b'); ax.plot([HL+W/2]*2,[-R-2,R+12],color='#c23a2b',lw=0.7,ls='--')
ax.text(-4,-R-12,'lato ENCODER (mozzo)',fontsize=8,ha='right'); ax.text(L+4,-R-12,'lato ESTERNO',fontsize=8,ha='left')
ax.set_xlim(-22,L+22); ax.set_ylim(-R-16,R+18)
# vista frontale lato encoder
bx=fig.add_axes([0.56,0.3,0.4,0.55]); bx.set_aspect('equal'); bx.axis('off')
for r,fc in ((R,'#c9d3dd'),(PR1,'#e6ebf0'),(HR,'#b7c3cf'),(B,'white')): bx.add_patch(Circle((0,0),r,fc=fc,ec='k',lw=1))
for a in (0,90):
    x,y=math.cos(math.radians(a)),math.sin(math.radians(a)); bx.plot([B*x,HR*x],[B*y,HR*y],'k-',lw=2.2)
bx.text(0,-R-6,'vista dal lato encoder: grani M3 a 90° (chiaro = tasca prof. 3.5 su ogni lato, anima 3)',ha='center',fontsize=8)
bx.set_xlim(-R-4,R+4); bx.set_ylim(-R-9,R+4)
fig.text(0.04,0.95,'RG_ruota_encoder — ruota misura lunghezza (alleggerita, ~47 g), alluminio 6061-T6, senza finitura — quote in mm',fontsize=12,weight='bold')
fig.text(0.55,0.27,"""Note di lavorazione
• Diametro battistrada Ø63.66 ±0.10 (circonferenza 200.00 ±0.31 mm, da tarare),
   battistrada liscio, finitura normale di tornio (Ra ≤ 3.2)
• Eccentricità battistrada / foro ≤ 0.05
• Foro Ø6.05 ±0.05 passante (6.00–6.10, scorrevole sull'albero Ø6), smusso 0.3
• Smussi 0.5 × 45° sugli spigoli del battistrada, altri spigoli rotti 0.2
• 2 fori M3 radiali a 90° a metà mozzo (z 3.39), per grani M3×4 punta piana
• Tolleranze non indicate ISO 2768-m · nessun trattamento superficiale
   (NON anodizzare: stringe il foro)
Montaggio: faccia posteriore del mozzo a 1.2 mm dal codolo dell'encoder\n   (LPD3806: codolo Ø20×5, albero Ø6×13 con piano a 5.5);
un grano sul PIANO dell'albero (stringere per primo), l'altro sulla parte tonda;
distanza parete (faccia anteriore) – faccia posteriore del cerchio = 10.0 mm""",fontsize=8,va='top')
fig.savefig('/home/claude/ruota/RG_ruota_encoder.pdf'); fig.savefig('/home/claude/ruota/disegno.png',dpi=70)
