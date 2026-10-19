# Aggiunge i piani di massa GND su entrambi i lati, riempie le zone e fa il DRC
import sys, pcbnew
from pcbnew import FromMM as MM, ToMM
path = sys.argv[1]
W, H = 175.0, 125.0
board = pcbnew.LoadBoard(path)
# pin GND dei circuiti integrati (molti pin vicini): collegamento pieno al piano, evita razze di termico isolate
for fp in board.GetFootprints():
    if fp.GetReference() in ("U3", "U4"):
        for pad in fp.Pads():
            if pad.GetNetname() == "GND": pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
for z in list(board.Zones()):
    if not z.GetIsRuleArea(): board.Remove(z)
gnd = board.FindNet("GND")
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(gnd); z.SetZoneName("GND_" + board.GetLayerName(layer))
    z.SetLocalClearance(MM(0.4)); z.SetMinThickness(MM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.4)); z.SetThermalReliefSpokeWidth(MM(0.6))
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
