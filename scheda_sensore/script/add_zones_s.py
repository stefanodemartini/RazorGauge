# Aggiunge i piani di massa GND su entrambi i lati, riempie le zone e fa il DRC
import sys, pcbnew
from pcbnew import FromMM as MM, ToMM
path = sys.argv[1]
W, H = 24.0, 18.0
board = pcbnew.LoadBoard(path)
# pin GND dei circuiti integrati (molti pin vicini): collegamento pieno al piano, evita razze di termico isolate
for fp in board.GetFootprints():
    if fp.GetReference() in ("U1", "U2"):
        for pad in fp.Pads():
            if pad.GetNetname() == "GND": pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
for z in list(board.Zones()):
    if not z.GetIsRuleArea(): board.Remove(z)
gnd = board.FindNet("GND")
# via di cucitura GND: il piano inferiore deve essere collegato al GND superiore
import math
def _free(x, y, need=0.3 + 0.18 + 0.05):       # via Ø0.6: posto libero da tracce/vie/piazzole di altre reti (31/10/2026)
    for tr in board.GetTracks():
        if tr.GetNetname() == "GND": continue
        if tr.GetClass() == "PCB_VIA":
            d = math.hypot(ToMM(tr.GetPosition().x) - x, ToMM(tr.GetPosition().y) - y) - ToMM(tr.GetWidth())/2
        else:
            ax, ay, bx, by = ToMM(tr.GetStart().x), ToMM(tr.GetStart().y), ToMM(tr.GetEnd().x), ToMM(tr.GetEnd().y)
            dx, dy = bx - ax, by - ay; L = dx*dx + dy*dy; s = 0 if L == 0 else max(0, min(1, ((x-ax)*dx + (y-ay)*dy)/L))
            d = math.hypot(x - (ax + s*dx), y - (ay + s*dy)) - ToMM(tr.GetWidth())/2
        if d < need: return False
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetname() == "GND": continue
            bb = pd.GetBoundingBox(); x1, y1, x2, y2 = ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())
            if math.hypot(max(x1 - x, 0, x - x2), max(y1 - y, 0, y - y2)) < need + 0.1: return False
    for (hx, hy) in ((2.0, 14.0), (2.0, 6.0), (22.0, 14.5)):
        if math.hypot(hx - x, hy - y) < 2.2 + 0.4: return False
    return True
_cand = [(6.0, 16.6), (10.0, 16.6), (14.0, 16.6), (18.0, 16.8), (12.0, 14.3), (18.6, 13.3), (4.6, 11.6), (19.5, 0.9),
         (16.0, 15.4), (8.0, 14.6), (20.0, 11.0), (17.5, 12.2), (19.0, 3.0)]
_vias = [p for p in _cand if _free(*p)]
print("vie di cucitura GND:", _vias)
for (x, y) in _vias:
    v = pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); board.Add(v)
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(gnd); z.SetZoneName("GND_" + board.GetLayerName(layer))
    z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    for (x, y) in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
        z.AppendCorner(pcbnew.VECTOR2I(MM(x), MM(y)), -1)
    board.Add(z)
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.BuildConnectivity()
# (il conteggio delle connessioni mancanti e nel report DRC)
pcbnew.SaveBoard(path, board)
rep = path.replace(".kicad_pcb", "_drc.rpt")
pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
print("report DRC:", rep)
