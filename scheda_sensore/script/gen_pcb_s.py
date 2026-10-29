# Scheda sensore TSL1401CL: piazzamento, contorno, aree vietate, serigrafia, export DSN (KiCad 7)
import pcbnew, sys, json
sys.path.insert(0, "/home/claude/sens")
import sens_def as BD
from pcbnew import FromMM as MM, ToMM
OUT = "/home/claude/sens/RazorSensor/RazorSensor.kicad_pcb"
FPL = "/usr/share/kicad/footprints/"
W, H = 24.0, 18.0
# Coordinate: X KiCad = x torre + 12 (x torre: attraverso il cavo, + = verso il fronte / lontano dalla piastra)
#             Y KiCad = 12 - y torre (y torre: lungo il cavo, + = lato rullo inferiore; - = lato ruota encoder)
# Centro della linea di pixel (asse laser) in (12, 12).
board = pcbnew.BOARD()
ds = board.GetDesignSettings(); ds.SetCopperLayerCount(2)
ds.m_TrackMinWidth = MM(0.15); ds.m_MinClearance = MM(0.15); ds.m_ViasMinSize = MM(0.5); ds.m_MinThroughDrill = MM(0.3)
ds.m_HoleToHoleMin = MM(0.5); ds.m_CopperEdgeClearance = MM(0.3)
ns = ds.m_NetSettings; d = ns.m_DefaultNetClass
d.SetTrackWidth(MM(0.25)); d.SetClearance(MM(0.18)); d.SetViaDiameter(MM(0.6)); d.SetViaDrill(MM(0.3))
nc = pcbnew.NETCLASS("Supply"); nc.SetTrackWidth(MM(0.4)); nc.SetClearance(MM(0.18)); nc.SetViaDiameter(MM(0.7)); nc.SetViaDrill(MM(0.35))
ns.m_NetClasses["Supply"] = nc
nets = {}
for n in sorted(BD.nets()): ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni
for n in ("VDD", "GND"): nets[n].SetNetClass(nc)
def edge(pts):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
        s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1]))); board.Add(s)
edge([(0, 0), (W, 0), (W, H), (0, H)])
P = {
    "U1": (12.0, 12.0, 180),            # pin 1-4 verso il lato rullo, pin 1 verso il fronte (pixel 1 verso il fronte)
    "J1": (20.95, 6.1, 90),             # ingresso cavo sul bordo anteriore: fronte del connettore a X 23.4, piazzole MP entro 23.65; pin 1 = 3V3 (Y 9.2)
    # tutto sul lato rullo: lato ruota libero per i fori di fissaggio (da definire)
    # sotto la guida J lato rullo (X <= 15.5, Y <= 3.5) solo 0603 (0.5 mm); U2 (1.45 mm) ruotato: corpo a Y 4.05-5.65, 0.55 fuori dalla zona J
    "C2": (5.9, 8.2, 90), "C1": (8.1, 8.2, 90), "R3": (9.7, 8.2, 90), "R2": (13.0, 8.2, 90), "R1": (15.8, 8.2, 90),
    "R6": (5.8, 4.6, 90), "R5": (7.4, 4.6, 90), "R7": (9.0, 4.6, 90), "R4": (10.6, 4.6, 90), "U2": (13.6, 4.6, 90),
    "C3": (5.8, 1.6, 90), "R8": (7.4, 1.6, 90), "R9": (9.0, 1.6, 90), "C4": (10.6, 1.6, 90), "R10": (16.8, 1.6, 90),
}
fps = {}
for c in BD.C:
    lib, name = c["fp"].split(":")
    path = FPL + lib + ".pretty" if lib != "RazorSensor" else "/home/claude/sens/RazorSensor/RazorSensor.pretty"
    fp = pcbnew.FootprintLoad(path, name)
    fp.SetReference(c["ref"]); fp.SetValue(c["value"]); fp.SetFPID(pcbnew.LIB_ID(lib, name))
    x, y, r = P[c["ref"]]; fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); fp.SetOrientationDegrees(r)
    board.Add(fp)
    for pad in fp.Pads():
        n = c["pins"].get(pad.GetNumber())
        if n: pad.SetNet(nets[n])
    t = fp.Reference(); t.SetTextSize(pcbnew.VECTOR2I(MM(0.6), MM(0.6))); t.SetTextThickness(MM(0.1)); t.SetVisible(False)
    fps[c["ref"]] = fp
# --- aree vietate (rame e via) dove andranno i fori di fissaggio: POSIZIONI PROVVISORIE, DA CONFERMARE
HOLES_TBD = [(1.5, 14.0), (1.5, 6.0), (22.5, 14.5)]     # = S_HOLES dello SCAD (x torre -10.5/-10.5/+10.5, y -2/+6/-2.5)
def rule_circle(x, y, r, name):
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True); z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(True); z.SetDoNotAllowFootprints(True)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls); z.SetZoneName(name)
    o = z.Outline(); o.NewOutline()
    import math
    for i in range(24): a = 2 * math.pi * i / 24; o.Append(MM(x + r * math.cos(a)), MM(y + r * math.sin(a)))
    board.Add(z)
for i, (x, y) in enumerate(HOLES_TBD): rule_circle(x, y, 2.2, "FORO_TBD_%d" % (i + 1))
# --- controlli di piazzamento
def cbox(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd); b = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return (ToMM(b.GetLeft()), ToMM(b.GetTop()), ToMM(b.GetRight()), ToMM(b.GetBottom()))
bad = 0; boxes = {r: cbox(f) for r, f in fps.items()}
for r, (x1, y1, x2, y2) in boxes.items():
    if x1 < -0.01 or y1 < -0.01 or x2 > W + 0.8 or y2 > H + 0.01: print("FUORI SCHEDA", r, [round(v, 2) for v in (x1, y1, x2, y2)]); bad += 1
    for (hx, hy) in HOLES_TBD:
        if x1 < hx + 2.2 and hx - 2.2 < x2 and y1 < hy + 2.2 and hy - 2.2 < y2: print("SU FORO PROVVISORIO", r); bad += 1
rs = list(boxes)
for i in range(len(rs)):
    for j in range(i + 1, len(rs)):
        a, b = boxes[rs[i]], boxes[rs[j]]
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]: print("SOVRAPPOSTI", rs[i], rs[j]); bad += 1
# vincoli meccanici: sotto la guida J lato rullo (X <= 15.5, Y <= 3.5) solo componenti <= 1.5 mm (qui solo 0603);
# U2 (1.45 mm, 0.25 sopra la faccia del chip) e' nel fascio ma a 3 mm dalla linea di pixel: la sua ombra cade sul PCB, non sui pixel.
print("problemi di piazzamento:", bad)
json.dump({r: [round(v, 2) for v in b] for r, b in boxes.items()}, open("/home/claude/sens/boxes.json", "w"))
def silk(txt, x, y, size=0.8, rot=0, layer=pcbnew.F_SilkS, mirror=False):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetLayer(layer); t.SetMirrored(mirror)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15)); t.SetTextAngleDegrees(rot); board.Add(t)
for pad in fps["J1"].Pads():
    if pad.GetNumber() in "123456" and len(pad.GetNumber()) == 1:
        p = pad.GetPosition(); silk(["3V3", "GND", "SI", "CLK", "AO", "SH"][int(pad.GetNumber()) - 1], ToMM(p.x) + 1.6, ToMM(p.y), 0.8, 0, pcbnew.B_SilkS, True)
silk("RazorGauge TSL1401CL v1", 10.5, 17.1, 0.8, 0, pcbnew.B_SilkS, True)
silk("RazorBlade 2026", 10.5, 15.9, 0.8, 0, pcbnew.B_SilkS, True)
silk("LATO RULLO", 9.0, 1.1, 0.8, 0, pcbnew.B_SilkS, True)
silk("FRONTE ->", 13.0, 13.8, 0.8, 0, pcbnew.B_SilkS, True)
board.Save(OUT)
pcbnew.ExportSpecctraDSN(board, OUT.replace(".kicad_pcb", ".dsn"))
print("DSN esportato")
