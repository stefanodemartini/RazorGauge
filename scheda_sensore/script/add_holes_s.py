# Fori di fissaggio della scheda sensore (31/10/2026): 3 fori NPTH Ø2.2 per viti M2 autofilettanti nella slitta, con area
# senza rame Ø4.4 (testa M2 Ø3.8). Posizioni = S_HOLES dello SCAD (x torre -10/-10/+10, y -2/+6/-2.5): 0.9 mm dal bordo.
# Si applica alla scheda gia' sbrogliata (le tracce sono lontane >= 2.8 mm): sostituisce le aree provvisorie FORO_TBD.
import sys, math, pcbnew
from pcbnew import FromMM as MM
path = sys.argv[1]
HOLES = [(2.0, 14.0), (2.0, 6.0), (22.0, 14.5)]
_FP = [pcbnew.FootprintLoad("/usr/share/kicad/footprints/MountingHole.pretty", "MountingHole_2.2mm_M2") for _ in HOLES]   # prima di LoadBoard
board = pcbnew.LoadBoard(path)
_old = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith("FORO_")]   # si tolgono alla fine (dopo, swig si confonde)
for ref in ("H1", "H2", "H3"):
    f = board.FindFootprintByReference(ref)
    if f: board.Remove(f)
for i, (x, y) in enumerate(HOLES):
    fp = _FP[i]
    fp.SetReference("H%d" % (i + 1)); fp.SetValue("M2"); fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    try:
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    except Exception: pass
    board.Add(fp)
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True); z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls); z.SetZoneName("FORO_M2_%d" % (i + 1))
    o = z.Outline(); o.NewOutline()
    for k in range(32): a = 2 * math.pi * k / 32; o.Append(MM(x + 2.2 * math.cos(a)), MM(y + 2.2 * math.sin(a)))
    board.Add(z)
for z in _old: board.Remove(z)
pcbnew.SaveBoard(path, board)
print("fori M2:", HOLES)
