# RazorBoard — piazzamento componenti e struttura PCB (KiCad 7, pcbnew python)
import pcbnew, sys, json
import board_def as BD
from pcbnew import FromMM as MM, ToMM

OUT = "/home/claude/board/RazorBoard/RazorBoard.kicad_pcb"
FPL = "/usr/share/kicad/footprints/"
W, H = 175.0, 125.0

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
# regole: compatibili con i servizi economici (JLCPCB/PCBWay 2 strati)
ds.m_TrackMinWidth = MM(0.25); ds.m_MinClearance = MM(0.25); ds.m_ViasMinSize = MM(0.7); ds.m_MinThroughDrill = MM(0.35)
ds.m_HoleToHoleMin = MM(0.5); ds.m_CopperEdgeClearance = MM(0.5)
ns = ds.m_NetSettings
dflt = ns.m_DefaultNetClass
dflt.SetTrackWidth(MM(0.4)); dflt.SetClearance(MM(0.3)); dflt.SetViaDiameter(MM(0.9)); dflt.SetViaDrill(MM(0.45))
def mk_nc(name, tw, cl, vd, vdr):
    nc = pcbnew.NETCLASS(name); nc.SetTrackWidth(MM(tw)); nc.SetClearance(MM(cl)); nc.SetViaDiameter(MM(vd)); nc.SetViaDrill(MM(vdr))
    ns.m_NetClasses[name] = nc; return nc
NC_PWR = mk_nc("Power", 1.0, 0.35, 1.2, 0.6)
NC_3V3 = mk_nc("Supply3V3", 0.6, 0.3, 1.0, 0.5)
PWR_NETS = {"+24V_IN", "+24V_F", "+24V", "+5V_BUCK", "+5V", "+5V_EXT", "M_VIN", "S_VIN", "GND"}
S3_NETS = {"+3V3_M", "+3V3_S", "LASER_P", "LASER_SEL", "LASER_N"}

# --- net
nets = {}
for n in sorted(BD.nets().keys()):
    ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni

# --- contorno scheda
def edge_line(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); board.Add(s)
for a, b in [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]: edge_line(*a, *b)

# --- piazzamento: ref -> (x, y, rotazione_gradi)   [mm, origine in alto a sinistra, y verso il basso]
MX, SX, MY = 58.0, 105.0, 9.0          # pin 1 master / slave (fila sinistra), y del pin 1
P = {
    # alimentazione (colonna sinistra)
    "J1": (5.2, 16.0, -90), "J2": (5.2, 40.0, -90),
    "F1": (15.0, 10.0, 0), "D1": (15.0, 19.0, 0), "D2": (15.0, 26.0, 0),
    "C1": (17.0, 35.0, 0), "C2": (31.0, 35.0, 0),
    "U1": (17.0, 50.0, 0), "C3": (32.0, 49.0, 0), "JP1": (42.0, 45.0, 0),
    "C4": (17.0, 61.0, 0), "C5": (31.0, 61.0, 0),
    "R1": (15.0, 70.0, 0), "D3": (32.0, 70.0, 0),
    "D4": (15.0, 77.0, 0), "D5": (15.0, 84.0, 0),
    # moduli
    "A1": (MX, MY, 0), "A2": (SX, MY, 0),
    # UART tra i moduli
    "R10": (89.0, 28.0, 90), "R11": (94.5, 28.0, 90), "J7": (91.75, 32.0, 0),
    # encoder (sotto il master, a sinistra)
    "U3": (47.0, 62.0, 0),
    "R30": (59.0, 62.0, 0), "R31": (59.0, 67.0, 0), "R32": (59.0, 72.0, 0), "R33": (59.0, 77.0, 0),
    "C7": (47.0, 84.0, 0), "C8": (56.0, 84.0, 0), "C9": (65.0, 84.0, 0),
    # RazorGauge (sotto il master, a destra)
    "R40": (75.0, 62.0, 0), "R41": (75.0, 67.0, 0), "R42": (75.0, 72.0, 0),
    "R44": (75.0, 77.0, 0), "R45": (75.0, 82.0, 0), "R43": (75.0, 87.0, 0),
    "D9": (90.0, 62.0, 0), "D10": (90.0, 67.0, 0), "C10": (90.0, 72.0, 0),
    "C11": (91.0, 78.0, 0), "C12": (90.0, 84.0, 0), "Q1": (90.0, 90.0, 0), "JP2": (99.5, 76.0, 0),
    # uscite TB6600 (sotto lo slave)
    "U4": (106.0, 62.0, 0),
    "R20": (117.0, 62.0, 0), "R21": (117.0, 67.0, 0), "R22": (117.0, 72.0, 0),
    "R23": (117.0, 77.0, 0), "R24": (117.0, 82.0, 0), "R25": (117.0, 87.0, 0),
    "R26": (131.0, 62.0, 0), "R27": (131.0, 67.0, 0), "R28": (131.0, 72.0, 0),
    "D6": (132.0, 79.0, 0), "D7": (132.0, 85.0, 0), "D8": (132.0, 91.0, 0), "C6": (106.0, 92.0, 0),
    # pulsanti (colonna destra) + RC
    "SW1": (150.0, 9.0, 0), "SW2": (150.0, 20.0, 0), "SW3": (150.0, 31.0, 0), "SW4": (150.0, 42.0, 0),
    "R52": (146.0, 58.0, 0), "R53": (146.0, 63.0, 0), "R54": (146.0, 68.0, 0), "R55": (146.0, 73.0, 0),
    "R56": (146.0, 78.0, 0), "R57": (146.0, 83.0, 0), "R50": (146.0, 88.0, 0), "R51": (146.0, 93.0, 0),
    "C14": (162.0, 58.0, 0), "C15": (162.0, 64.0, 0), "C16": (162.0, 70.0, 0), "C13": (162.0, 76.0, 0),
    # morsetti sul bordo inferiore (ingresso fili verso il bordo)
    "J4": (45.0, 119.5, 0), "J5": (73.0, 119.5, 0), "J3": (115.0, 119.5, 0), "J6": (142.0, 119.5, 0),
    # fori M3
    "H1": (4.0, 4.0, 0), "H2": (171.0, 4.0, 0), "H3": (4.0, 121.0, 0), "H4": (171.0, 121.0, 0),
}

fps = {}
for c in BD.C:
    lib, name = c["fp"].split(":")
    path = FPL + lib + ".pretty" if lib != "RazorBoard" else "/home/claude/board/RazorBoard/RazorBoard.pretty"
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None: sys.exit("footprint non trovato: " + c["fp"])
    fp.SetReference(c["ref"]); fp.SetValue(c["value"])
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    x, y, r = P[c["ref"]]
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    fp.SetOrientationDegrees(r)
    board.Add(fp)
    for pad in fp.Pads():
        net = c["pins"].get(pad.GetNumber())
        if net: pad.SetNet(nets[net])
    fps[c["ref"]] = fp

# netclass sulle net
for n, ni in nets.items():
    if n in PWR_NETS: ni.SetNetClass(NC_PWR)
    elif n in S3_NETS: ni.SetNetClass(NC_3V3)

# --- aree vietate sotto le antenne dei moduli (niente rame, piste, via)
def rule_area(x1, y1, x2, y2, name):
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True)
    z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
    z.SetZoneName(name)
    o = z.Outline(); o.NewOutline()
    for (x, y) in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]: o.Append(MM(x), MM(y))
    board.Add(z)
for ref, x in (("A1", MX), ("A2", SX)):
    rule_area(x + 12.7 - 14.25, MY + 38.4, x + 12.7 + 14.25, MY + 45.4 + 2.0, "ANT_" + ref)

# --- controlli di piazzamento: dentro la scheda e courtyard non sovrapposti
def cbox(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    b = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    return (ToMM(b.GetLeft()), ToMM(b.GetTop()), ToMM(b.GetRight()), ToMM(b.GetBottom()))
bad = 0
boxes = {r: cbox(f) for r, f in fps.items()}
for r, (x1, y1, x2, y2) in boxes.items():
    if x1 < -0.01 or y1 < -0.01 or x2 > W + 0.01 or y2 > H + 0.01:
        if not r.startswith("A"): print("FUORI SCHEDA", r, [round(v, 1) for v in (x1, y1, x2, y2)]); bad += 1
refs = list(boxes)
for i in range(len(refs)):
    for j in range(i + 1, len(refs)):
        a, b = boxes[refs[i]], boxes[refs[j]]
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
            # i moduli stanno sopra gli zoccoli: ammessa sovrapposizione solo con componenti bassi? no -> segnala
            print("SOVRAPPOSTI", refs[i], refs[j]); bad += 1
print("problemi di piazzamento:", bad)
board.Save(OUT)
json.dump({r: [round(v, 2) for v in b] for r, b in boxes.items()}, open("/home/claude/board/boxes.json", "w"))

for r, f in fps.items():
    if r[0] in "HA": f.Reference().SetVisible(False)
# --- etichette serigrafiche per i morsetti e i jumper
def silk(txt, x, y, size=1.2, rot=0, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetLayer(layer)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15)); t.SetTextAngleDegrees(rot); board.Add(t)
def term_labels(ref, labels):
    fp = fps[ref]
    for pad in fp.Pads():
        i = int(pad.GetNumber()) - 1
        p = pad.GetPosition()
        silk(labels[i], ToMM(p.x), ToMM(p.y) - 8.7, 1.1)
term_labels("J4", ["+5V", "GND", "A", "B", "SH"])
term_labels("J5", ["3V3", "GND", "SI", "CLK", "AO", "L+", "L-", "SH"])
term_labels("J3", ["PUL", "DIR", "ENA", "GND", "+5V"])
term_labels("J6", ["SCAN", "F_S", "F_O", "WIFI", "GND"])
for ref, labs in (("J1", ["+24V", "GND"]), ("J2", ["+5V", "GND"])):
    for pad in fps[ref].Pads():
        p = pad.GetPosition(); silk(labs[int(pad.GetNumber()) - 1], 12.0, ToMM(p.y), 1.0, 90)
for ref, labs in (("JP1", ["INT", "5V", "EXT"]), ("JP2", ["3V3", "LAS", "5V"])):
    for pad in fps[ref].Pads():
        p = pad.GetPosition(); silk(labs[int(pad.GetNumber()) - 1], ToMM(p.x) + 3.6, ToMM(p.y), 0.9)
silk("RazorBoard v0.1", 40.0, 104.0, 2.0)
silk("RazorGauge controller - RazorBlade", 40.0, 107.5, 1.2)
silk("MASTER", MX + 12.7, MY + 20.0, 1.8, 90)
silk("SLAVE", SX + 12.7, MY + 20.0, 1.8, 90)
silk("TB6600: catodo comune (- a GND)", 128.5, 101.0, 1.0)
silk("calza dei cavi solo lato scheda", 92.0, 101.0, 1.0)
board.Save(OUT)
pcbnew.ExportSpecctraDSN(board, OUT.replace(".kicad_pcb", ".dsn"))
print("DSN esportato")
