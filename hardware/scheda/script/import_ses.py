# Importa le piste di una sessione Freerouting (.ses) in un .kicad_pcb, senza GUI
import re, sys, pcbnew
from pcbnew import FromMM as MM

pcb_path, ses_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(pcb_path)
t = open(ses_path).read()

def tokenize(s):
    return re.findall(r'"[^"]*"|\(|\)|[^\s()]+', s)
def parse(tokens):
    stack = [[]]
    for tk in tokens:
        if tk == '(': stack.append([])
        elif tk == ')':
            x = stack.pop(); stack[-1].append(x)
        else: stack[-1].append(tk.strip('"'))
    return stack[0][0]
tree = parse(tokenize(t))
def find(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key: yield c

res = 10.0  # um/unit default
routes = next(find(tree, 'routes'))
for r in find(routes, 'resolution'):
    unit, val = r[1], float(r[2])
    res = {'um': 1e-3, 'mm': 1.0, 'mil': 0.0254, 'inch': 25.4}[unit] / val   # mm per unita
netout = next(find(routes, 'network_out'))
LAYER = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
# rimuovi piste esistenti
for tr in list(board.GetTracks()): board.Remove(tr)
nt = nv = 0
for net in find(netout, 'net'):
    name = net[1]
    ni = board.FindNet(name)
    if ni is None: print("net sconosciuta", name); continue
    for w in find(net, 'wire'):
        for path in find(w, 'path'):
            layer, width = path[1], float(path[2]) * res
            pts = [float(v) * res for v in path[3:]]
            xy = [(pts[i], -pts[i + 1]) for i in range(0, len(pts) - 1, 2)]
            for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); tr.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
                tr.SetWidth(MM(width)); tr.SetLayer(LAYER[layer]); tr.SetNet(ni); board.Add(tr); nt += 1
    for v in find(net, 'via'):
        m = re.search(r'_(\d+):(\d+)_um', v[1])
        dia, drill = (int(m.group(1)) / 1000, int(m.group(2)) / 1000) if m else (0.9, 0.45)
        x, y = float(v[2]) * res, -float(v[3]) * res
        via = pcbnew.PCB_VIA(board); via.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        via.SetWidth(MM(dia)); via.SetDrill(MM(drill)); via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(ni); board.Add(via); nv += 1
board.Save(pcb_path)
print(f"importati {nt} segmenti e {nv} via")
