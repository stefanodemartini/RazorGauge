# Stima 18/11/2026: file QC "(Real)" -> densita' = media della linea finita (core compreso).
# Conserva la massa totale, ricava la densita' del coating per ogni scenario di core, ricalcola.
import json, glob, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stima_affondamento_core import cyl_speed, A, SCEN, ROOT
for p in sorted({q.lower(): q for q in glob.glob(os.path.join(ROOT,'Razorblade','QC Extrahover','*eal*.flp'))}.values()):
    d=json.load(open(p,encoding='utf-8-sig')); n=sorted(d['DesignNodes'],key=lambda q:q['X'])
    if len(n)<2 or not d.get('CoreDiameterMm'): continue
    dc=d['CoreDiameterMm']; rho=d['SharedDensityGCm3']; t=d.get('WaterTempC') or 20
    # integrate area along x (1 cm steps)
    L=n[-1]['X']-n[0]['X']; SA=0
    for a,b in zip(n,n[1:]):
        k=max(1,int(b['X']-a['X']))
        for i in range(k):
            D=a['Y']+(b['Y']-a['Y'])*(i+0.5)/k; SA+=A(D)*(b['X']-a['X'])/k
    M=rho*SA
    print(os.path.basename(p), f'rho_mean {rho:.4f}  L {L:.0f} cm  mass {M*0.01:.1f} g')
    tip=n[0]; thin=min(n,key=lambda q:q['Y']); fat=max(n,key=lambda q:q['Y'])
    for k,rc in SCEN.items():
        rcoat=(M-rc*A(dc)*L)/(SA-A(dc)*L)
        out=[]
        for q in (tip,thin,fat):
            D=q['Y']; re=(rc*A(dc)+rcoat*(A(D)-A(dc)))/A(D)
            out.append(f"D{D:.2f}: now {cyl_speed(False,t,D,rho):+.2f} -> {cyl_speed(False,t,D,re):+.2f}")
        print(f'  {k:5} coat {rcoat:.3f} | '+' | '.join(out))
