import sys; sys.path.insert(0,"/home/claude/fp/v3/audit")
from common import *
import itertools
P=load_P(); g=load_G(0); g["pezzo_unico"]=P
rigid=[k for k in g if not k.startswith("filo") and not k.startswith("molla") and not k.startswith("cavo") and not k.startswith("viti_") and not k.startswith("vite_") and not k.startswith("perno_") and k not in ("albero_encoder",)]
allowed={frozenset(p) for p in [("pezzo_unico","laser"),("pezzo_unico","lente_L1"),("carrello","lente_L2"),("slitta_sensore","scheda_sensore"),("slitta_sensore","fascetta_2_5mm"),("pezzo_unico","rullo_inferiore_spostato")]}
for s in ("lato_misura","sulla_ruota"):
    f="forcella_spintore_"+s; b="boccola_filettata_forcella_spintore_"+s; st="stelo_M5_forcella_spintore_"+s; bd="bullone_dado_perno_forcella_spintore_"+s
    r="rullo_spintore_lato_misura" if s=="lato_misura" else "rullo_superiore_su_ruota"
    allowed |= {frozenset(p) for p in [(f,b),(st,b),(f,bd),(r,bd),(f,r),(f,st)]}
bad=[]; n=0
for a,b in itertools.combinations(rigid,2):
    if frozenset((a,b)) in allowed: continue
    A,Bm=g[a],g[b]
    if np.any(A.bounds[0]>Bm.bounds[1]) or np.any(Bm.bounds[0]>A.bounds[1]): continue
    if a=="pezzo_unico": A=crop(P,Bm.bounds)
    if b=="pezzo_unico": Bm=crop(P,A.bounds)
    v=inter(A,Bm); n+=1
    if not (v<=1e-3): bad.append("%s ∩ %s = %.3f"%(a,b,v))
rep(not bad,"Interferenze statiche: %d coppie vicine controllate tra %d parti: %s"%(n,len(rigid),"nessuna" if not bad else "; ".join(bad)))
