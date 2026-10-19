import pickle, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import shapely.affinity as sa
R=pickle.load(open('/tmp/fori.pkl','rb')); H=R['HOLES']; PL=R['PL']
TIPI={'X':('DA DEFINIRE (non lavorare)','#c00000'),'F':('filettato','#1f6fd1'),'P':('passante + dado','#2e9e44'),'S':('passante svasato 90° (testa piana)','#d07a14'),'B':('filettato nel bordo','#b5179e'),'A':('apertura / asola (nessuna vite)','#666666')}
def draw(ax,poly,tf,hs,title,xlabel,ylabel):
    def T(x,y): return tf(x,y)
    for g in getattr(poly,'geoms',[poly]):
        xs,ys=zip(*[T(*p) for p in g.exterior.coords]); ax.fill(xs,ys,color='#e3e6ea',ec='k',lw=1)
        for r in g.interiors:
            xs,ys=zip(*[T(*p) for p in r.coords]); ax.fill(xs,ys,color='white',ec='k',lw=0.8)
    for h in hs:
        x,y=T(h['u'],h['v']); c=TIPI[h['tipo']][1]
        if h['tipo']=='B':
            ax.plot([x],[y],marker='v',ms=9,color=c)
        else:
            ax.plot([x],[y],marker='+',ms=8,color=c,mew=1.2)
        lab=h['cod']+((' '+h['d'].split()[0]+(' x'+h['prof'] if h['tipo']=='B' else ' THRU')) if h['tipo'] in 'FB' and h['d']!='M3?' else '')
        ax.annotate(lab,(x,y),xytext=(4,4),textcoords='offset points',fontsize=7.5,color=c,weight='bold')
    ax.set_aspect('equal'); ax.set_title(title,fontsize=11,loc='left'); ax.set_xlabel(xlabel,fontsize=8); ax.set_ylabel(ylabel,fontsize=8)
    ax.grid(True,lw=0.3,alpha=0.5); ax.tick_params(labelsize=7)
    for k,(n,c) in TIPI.items(): ax.plot([],[],marker='+' if k!='B' else 'v',ls='',color=c,label=n)
    ax.legend(fontsize=7,loc='upper right',framealpha=0.9)
def thread_box(fig,hs,extra=''):
    from collections import Counter
    c=Counter((h['d'],'edge' if h['tipo']=='B' else 'thru') for h in hs if h['tipo'] in 'FB' and h['d']!='M3?')
    cs=sum(1 for h in hs if h['tipo']=='S')
    txt='THREADS: '+', '.join('%d x %s %s'%(n,d,('tapped in plate EDGE, depth '+[h['prof'] for h in hs if h['tipo']=='B'][0]+' mm') if k=='edge' else 'tapped through') for (d,k),n in c.items())
    if cs: txt+='\nCOUNTERSINKS: %d x M3 90° (Ø6.5)'%cs
    txt+='\nAll other holes plain (no thread). Material Al 6061-T6, 6 mm. ISO 2768-m.'+extra
    fig.text(0.5,0.985,txt,ha='center',va='top',fontsize=9,weight='bold',color='#1f4e8c',bbox=dict(fc='#eef3fa',ec='#1f4e8c',pad=4))
def table(ax,hs,tf,cols):
    ax.axis('off')
    rows=[]
    for h in hs:
        x,y=tf(h['u'],h['v'])
        rows.append([h['cod'],TIPI[h['tipo']][0],h['d'],h['prof'] or '',f"{x:.2f}",f"{y:.2f}",h['nota']])
    t=ax.table(cellText=rows,colLabels=['Cod','Tipo','Misura','Prof.',cols[0],cols[1],'Uso / vite'],loc='upper left',cellLoc='left',colLoc='left',
               colWidths=[0.05,0.17,0.09,0.06,0.07,0.07,0.49])
    t.auto_set_font_size(False); t.set_fontsize(6.6); t.scale(1,1.25)
pdf=PdfPages('/mnt/user-data/outputs/RazorGauge/piastra_alluminio/Piastre_fori.pdf')
# PIASTRA: vista dal FRONTE, origine = angolo in basso a sinistra (bordo Z max, filo inferiore)
tfP=lambda u,v:(PL['z1']-u, v-PL['y0'])
hs=[h for h in H if h['lastra']=='P']
fig=plt.figure(figsize=(11.7,16.5)); ax=fig.add_axes([0.06,0.47,0.9,0.455]); draw(ax,R['P'],tfP,hs,'PIASTRA VERTICALE — alluminio 6 mm, 314 × 227 (+ 3 linguette 20 × 6 in basso) — vista dal FRONTE (lato assieme)','x [mm] da bordo sinistro','y [mm] da filo inferiore')
thread_box(fig,hs); table(fig.add_axes([0.03,0.02,0.94,0.42]),hs,tfP,('x','y')); pdf.savefig(fig); plt.close(fig)
# MENSOLA: vista dall'alto, origine = angolo anteriore destro (bordo contro la piastra, lato bobina)
tfM=lambda u,v:(v-(-162), R['XPB']-u)
hs=[h for h in H if h['lastra']=='M']
fig=plt.figure(figsize=(11.7,16.5)); ax=fig.add_axes([0.08,0.5,0.86,0.42]); draw(ax,R['M'],tfM,hs,"MENSOLA — alluminio 6 mm, 116 × 89 (+ 2 linguette 20 × 6 verso la piastra) — vista dall'ALTO",'x [mm] lungo la piastra','y [mm] dal bordo contro la piastra (linguette a y<0)')
ax.invert_yaxis(); thread_box(fig,hs); table(fig.add_axes([0.03,0.05,0.94,0.4]),hs,tfM,('x','y')); pdf.savefig(fig); plt.close(fig)
# BASE: vista dall'alto, origine = angolo posteriore destro
tfB=lambda u,v:(v-PL['z0'], u-(-120))
hs=[dict(h,tipo='X') if h['d']=='M3?' else h for h in H if h['lastra']=='B']
fig=plt.figure(figsize=(11.7,16.5)); ax=fig.add_axes([0.06,0.5,0.9,0.46]); draw(ax,R['B'],tfB,hs,"BASE — alluminio 6 mm, 314 × 165 — vista dall'ALTO (svasature B1–B4 e B12–B13 sul lato INFERIORE)",'x [mm] lungo la piastra','y [mm] dal bordo posteriore')
thread_box(fig,hs); table(fig.add_axes([0.03,0.05,0.94,0.4]),hs,tfB,('x','y')); pdf.savefig(fig); plt.close(fig)
# PIASTRINA PRESA IEC: vista da DIETRO (dall'esterno), origine = angolo in basso a sinistra
tfL=lambda u,v:(u-R['LZ'][0], v-PL['y0'])
hs=[h for h in H if h['lastra']=='L']
fig=plt.figure(figsize=(11.7,16.5)); ax=fig.add_axes([0.2,0.55,0.6,0.36]); draw(ax,R['L'],tfL,hs,"PIASTRINA PRESA IEC C14 (retro) — alluminio 6 mm, 56 × 41\n(+ 1 linguetta 20 × 6 in basso) — vista da DIETRO",'x [mm] dal bordo sinistro','y [mm] da filo inferiore')
ax.legend(fontsize=6,loc='upper left',bbox_to_anchor=(1.02,1))
thread_box(fig,hs); table(fig.add_axes([0.03,0.3,0.94,0.2]),hs,tfL,('x','y'))
fig.text(0.05,0.25,"Montaggio: linguetta nell'asola A4 della base, 2 viti M3x12 testa piana dal basso (B12–B13) nei filetti B1–B2 del bordo.\nPresa C14 dall'esterno; all'interno la cover 220 V fissata con le stesse 2 viti M3 (P1–P2) e dadi.\nSpazio libero dietro la piastrina: circa 50 (profondità) × 56 (larghezza) × 90 (altezza), fino all'alimentatore e al driver.",fontsize=9,va='top')
pdf.savefig(fig); plt.close(fig)
pdf.close()
for k in 'PMB': fig=None
print(len(H),'elementi')
