# Genera libreria simboli/footprint del progetto e lo schema KiCad 7 (a etichette) da board_def.py
import uuid, re, os, math
from kiutils.symbol import SymbolLib
import board_def as BD

PRJ = "RazorBoard"
OUT = "/home/claude/board_smd/RazorBoard"
os.makedirs(OUT + "/RazorBoard.pretty", exist_ok=True)
U = lambda: str(uuid.uuid4())
KLIB = "/usr/share/kicad/symbols/"
F = '(effects (font (size 1.27 1.27)))'
FH = '(effects (font (size 1.27 1.27)) hide)'

# ----------------------------------------------------------- simboli custom dei moduli
def module_symbol(name, pinnames, power, fp, prefixed):
    n = len(pinnames); half = n // 2
    top = (half - 1) * 2.54 / 2
    h = top + 2.54
    nm = f"{PRJ}:{name}" if prefixed else name
    out = [f'(symbol "{nm}" (in_bom yes) (on_board yes)',
           f'(property "Reference" "A" (at 0 {h+1.27:.2f} 0) {F})',
           f'(property "Value" "{name}" (at 0 {-h-1.27:.2f} 0) {F})',
           f'(property "Footprint" "{fp}" (at 0 0 0) {FH})',
           f'(property "Datasheet" "" (at 0 0 0) {FH})',
           f'(symbol "{name}_0_1" (rectangle (start -12.7 {h:.2f}) (end 12.7 {-h:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))',
           f'(symbol "{name}_1_1"']
    for i, pn in enumerate(pinnames):
        num = i + 1
        if i < half: x, ang, y = -17.78, 0, top - i * 2.54
        else:        x, ang, y = 17.78, 180, top - (i - half) * 2.54
        typ = "power_in" if pn in power else "bidirectional"
        out.append(f'(pin {typ} line (at {x:.2f} {y:.2f} {ang}) (length 5.08) (name "{pn}" {F}) (number "{num}" {F}))')
    out.append('))')
    return "\n".join(out)

MODS = {
    "ESP32_DevKitV1_30": (BD.M_PINS, {"3V3", "GND", "VIN"}, "RazorBoard:ESP32_DevKitV1_30p_W25.4"),
}
with open(f"{OUT}/RazorBoard.kicad_sym", "w") as f:
    f.write('(kicad_symbol_lib (version 20220914) (generator gen_sch)\n')
    for k, (pn, pw, fp) in MODS.items(): f.write(module_symbol(k, pn, pw, fp, False) + "\n")
    f.write(')\n')

# ----------------------------------------------------------- footprint custom dei moduli
def module_fp(name, npins, body_w, body_l, usb_off, ant_len=0):
    half = npins // 2
    L = [f'(footprint "{name}" (version 20221018) (generator gen_sch) (layer "F.Cu")',
         f'  (descr "Zoccolo per modulo {name}: 2 file da {half} pin, passo 2.54, file a 25.4 mm. Pin 1 = lato USB, fila sinistra (vista dall alto)")',
         '  (attr through_hole)',
         f'  (fp_text reference "REF**" (at 12.7 -{usb_off+2:.2f}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
         f'  (fp_text value "{name}" (at 12.7 {(half-1)*2.54/2:.2f} 90) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))']
    for i in range(npins):
        x = 0 if i < half else 25.4
        y = (i if i < half else i - half) * 2.54
        shape = "rect" if i == 0 else "circle"
        L.append(f'  (pad "{i+1}" thru_hole {shape} (at {x:.2f} {y:.2f}) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    x0 = 12.7 - body_w / 2; y0 = -usb_off; x1 = 12.7 + body_w / 2; y1 = y0 + body_l
    L.append(f'  (fp_rect (start {x0:.2f} {y0:.2f}) (end {x1:.2f} {y1:.2f}) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
    L.append(f'  (fp_rect (start {x0:.2f} {y0:.2f}) (end {x1:.2f} {y1:.2f}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))')
    L.append(f'  (fp_text user "USB" (at 12.7 {y0+2.5:.2f}) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))')
    if ant_len:
        L.append(f'  (fp_rect (start {x0:.2f} {y1-ant_len:.2f}) (end {x1:.2f} {y1:.2f}) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS"))')
        L.append(f'  (fp_text user "ANTENNA - no rame" (at 12.7 {y1-ant_len/2:.2f}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    L.append(f'  (fp_rect (start {x0-0.5:.2f} {y0-0.5:.2f}) (end {x1+0.5:.2f} {y1+0.5:.2f}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))')
    L.append(')')
    open(f"{OUT}/RazorBoard.pretty/{name}.kicad_mod", "w").write("\n".join(L) + "\n")

# DevKit V1 30p: ~28 x 51.5 mm, pin 1 a ~6.4 mm dal bordo USB; antenna ~6 mm in fondo
module_fp("ESP32_DevKitV1_30p_W25.4", 30, 28.5, 52.0, 6.6, ant_len=6.0)

# ----------------------------------------------------------- estrazione simboli dalle librerie KiCad
_libtxt = {}
def raw_symbol(lib, name):
    if lib == PRJ:
        pn, pw, fp = MODS[name]; return module_symbol(name, pn, pw, fp, True)
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
        pn, pw, fp = MODS[name]; n = len(pn); half = n // 2; top = (half - 1) * 2.54 / 2
        for i in range(n):
            if i < half: res[str(i + 1)] = (1, -17.78, top - i * 2.54, 0)
            else: res[str(i + 1)] = (1, 17.78, top - (i - half) * 2.54, 180)
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

# --- impaginazione per blocchi impilati in colonne
blocks = {}
for c in BD.C: blocks.setdefault(c["block"], []).append(c)
COLS = [(20, ["Alimentazione 24 V -> 5 V", "Encoder LPD3806-600BM (NPN OC, 5 V)", "Uscite driver TB6600 (5 V, catodo comune)"], 4),
        (290, ["Master ESP32 (WROOM-32, 30 pin)", "Interfaccia RazorGauge (TSL1401 + laser)", "Pulsanti (a bordo + morsetti)"], 4),
        (570, ["Slave ESP32 (WROOM-32, 30 pin)", "UART master <-> slave", "Fori di fissaggio"], 4)]
DX, DY = 55.88, 15.24
def is_big(c, unit):
    sym = c["symbol"]
    if sym.startswith(PRJ) or "Screw_Terminal" in sym or "Conn_01x03" in sym or "74LS245" in sym or "TSR" in sym or "2N7000" in sym: return True
    if "74HC14" in sym and unit == 7: return True
    return False
def big_size(c):
    sym = c["symbol"]
    if "74LS245" in sym: return (50.8, 55.88)
    if "74HC14" in sym: return (30.48, 38.1)
    if "Screw_Terminal_01x08" in sym: return (40.64, 30.48)
    if "Screw_Terminal" in sym or "TSR" in sym or "2N7000" in sym: return (40.64, 22.86)
    return (40.64, 17.78)
for cx, names, cols in COLS:
    y = 30.0
    for bname in names:
        comps = blocks[bname]
        text(bname, cx, g(y))
        smalls, bigs = [], []
        for c in comps:
            lib, name = c["symbol"].split(":")
            for unit in units_of(lib, name):
                (bigs if is_big(c, unit) else smalls).append((c, unit))
        if any(c["symbol"].startswith(PRJ) for c, u in bigs):
            c, u = bigs[0]
            n = len(c["pins"]); hh = (n // 2) * 2.54
            place(c, 1, g(cx + 50.8), g(y + 12.7 + hh / 2 + 5.08), 0)
            y += hh + 35
            continue
        x0, y0 = g(cx + 22.86), g(y + 12.7)
        for k, (c, unit) in enumerate(smalls):
            col, row = k % cols, k // cols
            place(c, unit, g(x0 + col * DX), g(y0 + row * DY), c["rot"] or 0)
        yb = y0 + ((len(smalls) + cols - 1) // cols) * DY + 5.08
        xb, rowh = cx + 22.86, 0
        for c, unit in bigs:
            w, h = big_size(c)
            if xb + w > cx + 22.86 + cols * DX:
                xb = cx + 22.86; yb += rowh; rowh = 0
            place(c, unit, g(xb), g(yb + h / 2), 0)
            xb += w + 10.16; rowh = max(rowh, h + 7.62)
        y = yb + rowh + 15
    print("colonna", cx, "altezza", round(y))
# note di progetto sul foglio
notes = ["NOTE:",
         "- Encoder spostato da GPIO12/13 a GPIO32/33 (GPIO12 e pin di avvio): aggiornare ENCODER_DATA_PIN=32, ENCODER_CLOCK_PIN=33 nel master.",
         "- TB6600 a catodo comune: PUL/DIR/ENA alti = LED opto acceso. ENA alto = motore libero (pull-up R22 = motore libero all accensione).",
         "- Il motore e il TB6600 si alimentano direttamente dall alimentatore 24 V, non dalla scheda.",
         "- Slave = ESP32 DevKit V1 30p come il master: PUL/DIR/ENA su GPIO25/26/27, pulsanti su GPIO32/33/34, UART su GPIO16/17 (firmware slave 0.6.0).",
         "- D4/D5 impediscono che l USB di un modulo alimenti tutta la scheda.",
         "- Calza dei cavi schermati collegata a GND solo lato scheda."]
for i, s in enumerate(notes): text(s, 570, 300 + i * 5.08, size=1.8, bold=(i == 0))

lib_syms = "\n".join(raw_symbol(l, n) for (l, n) in libs_used.values())
sch = f'''(kicad_sch (version 20230121) (generator eeschema)
  (uuid {SHEET})
  (paper "A1")
  (title_block (title "RazorBoard SMD - scheda controller RazorGauge + motore") (date "2026-10-01") (rev "0.2") (company "RazorBlade")
    (comment 1 "Master e Slave: ESP32 DevKit V1 30 pin (WROOM-32), file a 25.4 mm")
    (comment 2 "Componenti a foro passante, saldatura manuale"))
  (lib_symbols
{lib_syms}
  )
{chr(10).join(items)}
  (sheet_instances (path "/" (page "1")))
)
'''
open(f"{OUT}/{PRJ}.kicad_sch", "w").write(sch)
open(f"{OUT}/sym-lib-table", "w").write('(sym_lib_table\n  (lib (name "RazorBoard")(type "KiCad")(uri "${KIPRJMOD}/RazorBoard.kicad_sym")(options "")(descr ""))\n)\n')
open(f"{OUT}/fp-lib-table", "w").write('(fp_lib_table\n  (lib (name "RazorBoard")(type "KiCad")(uri "${KIPRJMOD}/RazorBoard.pretty")(options "")(descr ""))\n)\n')
if not os.path.exists(f"{OUT}/{PRJ}.kicad_pro"):
    open(f"{OUT}/{PRJ}.kicad_pro", "w").write('{"meta": {"filename": "RazorBoard.kicad_pro", "version": 1}}\n')
print("schema scritto:", len(items), "elementi")
