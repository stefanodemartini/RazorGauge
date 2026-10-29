# Schema KiCad 7 (a etichette) della scheda sensore, da sens_def.py
import uuid, os, math, sys
from kiutils.symbol import SymbolLib
sys.argv=[sys.argv[0]]
import sens_def as BD
import importlib.util
spec=importlib.util.spec_from_file_location("GL","/home/claude/sens/gen_lib.py"); GL=importlib.util.module_from_spec(spec); spec.loader.exec_module(GL)
PRJ = "RazorSensor"; OUT = "/home/claude/sens/RazorSensor"
U = lambda: str(uuid.uuid4())
KLIB = "/usr/share/kicad/symbols/"
F = '(effects (font (size 1.27 1.27)))'
FH = '(effects (font (size 1.27 1.27)) hide)'
_libtxt = {}
def raw_symbol(lib, name):
    if lib == PRJ:
        return GL.symbol(True)
    if lib not in _libtxt: _libtxt[lib] = open(KLIB + lib + ".kicad_sym").read()
    t = _libtxt[lib]
    i = t.index(f'(symbol "{name}"')
    d = 0
    for j in range(i, len(t)):
        if t[j] == '(': d += 1
        elif t[j] == ')':
            d -= 1
            if d == 0: break
    s = t[i:j + 1]
    return s.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)

_pins = {}
def sym_pins(lib, name):
    """-> {pin_number: (unit, x, y, angle)}  (unit 0 = comune)"""
    key = (lib, name)
    if key in _pins: return _pins[key]
    res = {}
    if lib == PRJ:
        for k, (x, y, a) in GL.PIN_XY.items(): res[str(k)] = (1, x, y, a)
    else:
        sl = SymbolLib.from_file(KLIB + lib + ".kicad_sym")
        s = [x for x in sl.symbols if x.entryName == name][0]
        for u in s.units:
            for p in u.pins: res[p.number] = (u.unitId, p.position.X, p.position.Y, p.position.angle or 0)
    _pins[key] = res
    return res

def units_of(lib, name):
    us = sorted(set(v[0] for v in sym_pins(lib, name).values()))
    return [u for u in us if u != 0] or [1]

# ----------------------------------------------------------- costruzione schema
SHEET = U()
items, libs_used = [], {}
def g(v): return round(round(v / 1.27) * 1.27, 2)

def place(comp, unit, X, Y, rot):
    lib, name = comp["symbol"].split(":")
    libs_used[comp["symbol"]] = (lib, name)
    pins = sym_pins(lib, name)
    up = {k: v for k, v in pins.items() if v[0] in (0, unit)}
    th = math.radians(rot)
    ys = [Y - (px * math.sin(th) + py * math.cos(th)) for (u, px, py, ang) in up.values()]
    if len(pins) > 2 and not rot:
        ytop, ybot = g(min(ys) - 3.81), g(max(ys) + 3.81)
    else:
        ytop, ybot = g(Y - 3.81), g(Y + 3.81)
    allpins = " ".join(f'(pin "{k}" (uuid {U()}))' for k in pins)
    items.append(
        f'(symbol (lib_id "{comp["symbol"]}") (at {X} {Y} {rot}) (unit {unit}) (in_bom yes) (on_board yes) (dnp no) (uuid {U()})\n'
        f'  (property "Reference" "{comp["ref"]}" (at {X} {ytop} {rot}) {F})\n'
        f'  (property "Value" "{comp["value"]}" (at {X} {ybot} {rot}) {F})\n'
        f'  (property "Footprint" "{comp["fp"]}" (at {X} {Y} 0) {FH})\n'
        f'  (property "Datasheet" "~" (at {X} {Y} 0) {FH})\n'
        f'  (property "MPN" "{comp["mpn"]}" (at {X} {Y} 0) {FH})\n'
        f'  (property "LCSC" "{comp.get("lcsc", "")}" (at {X} {Y} 0) {FH})\n'
        f'  {allpins}\n'
        f'  (instances (project "{PRJ}" (path "/{SHEET}" (reference "{comp["ref"]}") (unit {unit})))))')
    for num, (u, px, py, ang) in up.items():
        rx = px * math.cos(th) - py * math.sin(th); ry = px * math.sin(th) + py * math.cos(th)
        ex, ey = g(X + rx), g(Y - ry)
        a = (ang + rot) % 360
        dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(round(a)) % 360]
        net = comp["pins"].get(num)
        if net is None:
            items.append(f'(no_connect (at {ex} {ey}) (uuid {U()}))'); continue
        lx, ly = g(ex + dx * 2.54), g(ey + dy * 2.54)
        items.append(f'(wire (pts (xy {ex} {ey}) (xy {lx} {ly})) (stroke (width 0) (type default)) (uuid {U()}))')
        la = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[(dx, dy)]
        just = "right" if la in (180, 270) else "left"
        items.append(f'(label "{net}" (at {lx} {ly} {la}) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {U()}))')

def text(s, x, y, size=2.54, bold=True):
    b = " bold" if bold else ""
    items.append(f'(text "{s}" (at {x} {y} 0) (effects (font (size {size} {size}){b}) (justify left bottom)) (uuid {U()}))')
byref = {c["ref"]: c for c in BD.C}
text("Sensore TSL1401CL", 20.32, 25.4)
place(byref["U1"], 1, 50.8, 50.8, 0)
place(byref["J1"], 1, 50.8, 101.6, 0)
text("Connettore verso RazorBoard J5 (cavo schermato, calza su pin 6)", 20.32, 83.82, 1.8)
text("Buffer AO con offset: Vout = 0.958*AO + 0.154 V", 139.7, 25.4)
place(byref["U2"], 1, 165.1, 50.8, 0)
grid = ["C1", "C2", "R1", "R2", "R3", "C4", "R4", "R5", "R6", "C3", "R7", "R8", "R9", "R10"]
for k, r in enumerate(grid):
    col, row = k % 5, k // 5
    place(byref[r], 1, 114.3 + col * 30.48, 88.9 + row * 17.78, 90)
notes = ["NOTE:",
 "- Alimentazione 3.3 V dal pin 1 di J5 della RazorBoard (regolatore del modulo master).",
 "- U2 sposta lo zero di +0.15 V: l ADC dell ESP32 non vede sotto ~70 mV; l offset lo toglie il frame di buio.",
 "- Origine del footprint U1 = centro della linea di pixel (0.305 mm dal centro del package). Pixel 1 = lato pin 1 = verso il fronte.",
 "- TSL1401CL: MSL 5a (datasheet) -> cottura prima del reflow, niente solventi aggressivi sulla finestra.",
 "- Fori di fissaggio della scheda: DA DEFINIRE (verifiche in corso)."]
for i, s in enumerate(notes): text(s, 20.32, 140 + i * 5.08, size=1.6, bold=(i == 0))
lib_syms = "\n".join(raw_symbol(l, n) for (l, n) in libs_used.values())
sch = f"""(kicad_sch (version 20230121) (generator eeschema)
  (uuid {SHEET})
  (paper "A4")
  (title_block (title "RazorGauge - scheda sensore TSL1401CL") (date "2026-10-29") (rev "1.0 bozza") (company "RazorBlade")
    (comment 1 "24 x 18 mm, 2 strati, SMD lato TOP, montaggio JLCPCB"))
  (lib_symbols
{lib_syms}
  )
{chr(10).join(items)}
  (sheet_instances (path "/" (page "1")))
)
"""
open(f"{OUT}/{PRJ}.kicad_sch", "w").write(sch)
if not os.path.exists(f"{OUT}/{PRJ}.kicad_pro"):
    open(f"{OUT}/{PRJ}.kicad_pro", "w").write('{"meta": {"filename": "RazorSensor.kicad_pro", "version": 1}}\n')
print("schema scritto:", len(items), "elementi")
