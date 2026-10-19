# Ruota encoder su misura (alluminio 6061, tornita): circonferenza 200.00 mm, mozzo posteriore Ø18 con 2 grani M3
import cadquery as cq, math
D=200.0/math.pi            # 63.662
W=10.0; HUB_D=18.0; HUB_L=6.78; BORE=6.0     # mozzo 6.78: faccia mozzo a X 10.44 (0.5 dal codolo... vedi verifica)
PK_R0F,PK_R0B,PK_R1,PK_DEP=6.5,HUB_D/2,D/2-4.0,3.5   # alleggerimenti: web 3 mm, cerchio radiale 4 mm
L=HUB_L+W
prof=(cq.Workplane('XZ')            # profilo (r, z) da rivoluzionare attorno a Z
  .polyline([(BORE/2,0),(HUB_D/2,0),(HUB_D/2,HUB_L),(PK_R1,HUB_L),(PK_R1,HUB_L+0.001)]).close())
w=(cq.Workplane('XY').circle(HUB_D/2).extrude(HUB_L)
   .faces('>Z').workplane().circle(D/2).extrude(W))
w=w.cut(cq.Workplane('XY').workplane(offset=HUB_L).circle(PK_R1).circle(PK_R0B).extrude(PK_DEP))          # tasca lato encoder
w=w.cut(cq.Workplane('XY').workplane(offset=L-PK_DEP).circle(PK_R1).circle(PK_R0F).extrude(PK_DEP+0.1))   # tasca lato esterno
w=w.cut(cq.Workplane('XY').workplane(offset=-1).circle(BORE/2).extrude(L+2))                               # foro Ø6 H7
w=w.edges(cq.selectors.RadiusNthSelector(0)).chamfer(0.4) if False else w
# smussi 0.5 sugli spigoli del battistrada
w=w.edges(cq.selectors.BoxSelector((-40,-40,HUB_L-0.01),(40,40,HUB_L+0.01))).edges(cq.selectors.RadiusNthSelector(-1)).chamfer(0.5)
w=w.edges(cq.selectors.BoxSelector((-40,-40,L-0.01),(40,40,L+0.01))).edges(cq.selectors.RadiusNthSelector(-1)).chamfer(0.5)
# 2 grani M3 radiali a 90° a meta' mozzo (preforo Ø2.5)
for a in (0,90):
    c=cq.Solid.makeCylinder(1.25,HUB_D/2+1,cq.Vector(0,0,HUB_L/2),cq.Vector(math.cos(math.radians(a)),math.sin(math.radians(a)),0))
    w=w.cut(cq.Workplane().add(c))
v=w.val(); print('D %.3f  L %.2f  vol %.1f cm3  massa %.0f g  valido %s'%(D,L,v.Volume()/1000,v.Volume()/1000*2.70,v.isValid()))
cq.exporters.export(w,'/home/claude/ruota/RG_ruota_encoder.step'); cq.exporters.export(w,'/home/claude/ruota/RG_ruota_encoder.stl',tolerance=0.02,angularTolerance=0.1)
