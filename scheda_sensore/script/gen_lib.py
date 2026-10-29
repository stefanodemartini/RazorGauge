# Simbolo e footprint del TSL1401CL (datasheet TAOS136 fig. 9 e 10)
import os
OUT = "/home/claude/sens/RazorSensor"; os.makedirs(OUT + "/RazorSensor.pretty", exist_ok=True)
F = '(effects (font (size 1.27 1.27)))'; FH = '(effects (font (size 1.27 1.27)) hide)'
PINS = [("SI", "input"), ("CLK", "input"), ("AO", "output"), ("VDD", "power_in"),
        ("NC", "no_connect"), ("GND", "power_in"), ("GND", "power_in"), ("NC", "no_connect")]
def symbol(prefixed=False):
    nm = "RazorSensor:TSL1401CL" if prefixed else "TSL1401CL"
    L = [f'(symbol "{nm}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
         f'(property "Reference" "U" (at 0 8.89 0) {F})', f'(property "Value" "TSL1401CL" (at 0 -8.89 0) {F})',
         f'(property "Footprint" "RazorSensor:TSL1401CL_ams_CL" (at 0 0 0) {FH})', f'(property "Datasheet" "TAOS136" (at 0 0 0) {FH})',
         '(symbol "TSL1401CL_0_1" (rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background))))',
         '(symbol "TSL1401CL_1_1"']
    for i, (n, t) in enumerate(PINS):
        k = i + 1
        if k <= 4: x, y, a = -12.7, 3.81 - (k - 1) * 2.54, 0
        else: x, y, a = 12.7, -3.81 + (k - 5) * 2.54, 180
        L.append(f'(pin {t} line (at {x} {y:.2f} {a}) (length 5.08) (name "{n}" {F}) (number "{k}" {F}))')
    L.append('))'); return "\n".join(L)
PIN_XY = {k: ((-12.7, 3.81 - (k - 1) * 2.54, 0) if k <= 4 else (12.7, -3.81 + (k - 5) * 2.54, 180)) for k in range(1, 9)}
open(OUT + "/RazorSensor.kicad_sym", "w").write('(kicad_symbol_lib (version 20220914) (generator gen_lib)\n' + symbol() + '\n)\n')

# --- footprint. ORIGINE = CENTRO DELLA LINEA DI PIXEL (fig. 10: linea 0.305 dal centro del package verso i pin 5-8;
#     lungo il package la linea e' centrata entro ~0.05). Package 9.4 x 3.0 x 1.2. Contatti a passo 2.5 (7.5 tra i centri estremi),
#     a filo dei lati lunghi. Piazzole da fig. 9: 0.8 (lungo il package) x 1.3, spazio 0.8 tra le file -> centri a +/-1.05 dal centro;
#     pin 1 piu lunga (1.4) verso l'esterno. Vista dall'alto: pin 1 in basso a sinistra, 1-4 in basso, 5-8 in alto (da destra).
OFF = 0.305
L = ['(footprint "TSL1401CL_ams_CL" (version 20221018) (generator gen_lib) (layer "F.Cu")',
     '  (descr "ams TSL1401CL, package CL 9.4 x 3.0 x 1.2 mm, 8 contatti passo 2.5. Origine = centro della linea di pixel (0.305 dal centro del package verso i pin 5-8). Pixel 1 dal lato del pin 1.")',
     '  (attr smd)',
     '  (fp_text reference "REF**" (at 0 -2.6) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.12))))',
     '  (fp_text value "TSL1401CL" (at 0 3.2) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))']
for k in range(1, 9):
    if k <= 4: x, y = -3.75 + (k - 1) * 2.5, 1.05 + OFF
    else: x, y = 3.75 - (k - 5) * 2.5, -1.05 + OFF
    if k == 1:
        L.append(f'  (pad "1" smd rect (at {x - 0.3:.3f} {y:.3f}) (size 1.4 1.3) (layers "F.Cu" "F.Paste" "F.Mask"))')
    else:
        L.append(f'  (pad "{k}" smd rect (at {x:.3f} {y:.3f}) (size 0.8 1.3) (layers "F.Cu" "F.Paste" "F.Mask"))')
y0, y1 = -1.5 + OFF, 1.5 + OFF
L.append(f'  (fp_rect (start -4.7 {y0:.3f}) (end 4.7 {y1:.3f}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))')
L.append(f'  (fp_line (start -4.032 0) (end 4.032 0) (stroke (width 0.05) (type default)) (layer "F.Fab"))')      # linea di pixel 8.064
L.append(f'  (fp_circle (center -5.4 {y1:.3f}) (end -5.2 {y1:.3f}) (stroke (width 0.12) (type default)) (fill solid) (layer "F.SilkS"))')   # pin 1
L.append(f'  (fp_rect (start -5.25 {y0-0.5:.3f}) (end 5.0 {y1+0.5:.3f}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))')
L.append(')')
open(OUT + "/RazorSensor.pretty/TSL1401CL_ams_CL.kicad_mod", "w").write("\n".join(L) + "\n")
open(OUT + "/sym-lib-table", "w").write('(sym_lib_table\n  (lib (name "RazorSensor")(type "KiCad")(uri "${KIPRJMOD}/RazorSensor.kicad_sym")(options "")(descr ""))\n)\n')
open(OUT + "/fp-lib-table", "w").write('(fp_lib_table\n  (lib (name "RazorSensor")(type "KiCad")(uri "${KIPRJMOD}/RazorSensor.pretty")(options "")(descr ""))\n)\n')
print("libreria ok")
