import sys; sys.path.insert(0,"/home/claude/fp/v3/audit")
from common import *
g=load_G(0); C=g["carrello"]; L=g["coperchio"]; S=g["vite_M3_carrello"]
P=crop(load_P(),C.bounds,8)
print("carrello bounds",C.bounds.round(2)); print("vite",S.bounds.round(2))
for dy in (-5,-4,-2,0,2,4,6):
    c=C.copy(); c.apply_translation([0,dy,0]); s=S.copy(); s.apply_translation([0,dy,0])
    a=inter(c,P); b=inter(c,L); e=inter(s,L); f=inter(s,P)
    rep(a<0.01 and b<0.01 and e<0.01 and f<0.01,"carrello dY %+d: ∩pezzo %.3f ∩coperchio %.3f vite∩coperchio %.3f vite∩pezzo %.3f"%(dy,a,b,e,f))
# battuta: a -5 il carrello tocca il fondo? distanza minima
c=C.copy(); c.apply_translation([0,-5.0,0]); pts=c.sample(6000); _,d,_=trimesh.proximity.closest_point(P,pts); print("gioco min a fine corsa bassa %.2f"%d.min())
c=C.copy(); c.apply_translation([0,-5.3,0]); print("a -5.3 ∩pezzo %.3f (battuta)"%inter(c,P))
