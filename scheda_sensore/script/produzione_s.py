# Scheda sensore TSL1401CL: file di produzione JLCPCB (Gerber+foratura zip, BOM, CPL) + BOM completa
import csv, os, subprocess, zipfile, collections, sys, pcbnew
from pcbnew import ToMM
sys.path.insert(0, "/home/claude/sens"); import sens_def as BD
PRJ = "/home/claude/sens/RazorSensor"; OUT = PRJ + "/produzione"; PCB = PRJ + "/RazorSensor.kicad_pcb"
os.makedirs(OUT + "/gerber", exist_ok=True)
for f in os.listdir(OUT + "/gerber"): os.remove(OUT + "/gerber/" + f)
env = dict(os.environ, HOME="/tmp/kh")
layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "--no-x2", "-o", OUT + "/gerber/", PCB], check=True, env=env, capture_output=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", "-o", OUT + "/gerber/", PCB], check=True, env=env, capture_output=True)
with zipfile.ZipFile(OUT + "/RazorSensor_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT + "/gerber")): z.write(OUT + "/gerber/" + f, f)
board = pcbnew.LoadBoard(PCB); fp = {f.GetReference(): f for f in board.GetFootprints()}
# correzioni di rotazione note per i modelli JLCPCB (da verificare comunque nell'anteprima del montaggio)
ROT_FIX = {"SOT-23-5": 180, "JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal": 180, "TSL1401CL_ams_CL": 0}
groups = collections.OrderedDict()
for c in sorted(BD.C, key=lambda c: (c["lcsc"], c["ref"])):
    groups.setdefault((c["value"], c["fp"].split(":")[1], c["lcsc"]), []).append(c["ref"])
key = lambda r: (r[0], int(''.join(ch for ch in r if ch.isdigit())))
with open(OUT + "/RazorSensor_BOM_JLCPCB.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, foot, lcsc), refs in groups.items(): w.writerow([val, ",".join(sorted(refs, key=key)), foot, lcsc])
with open(OUT + "/RazorSensor_CPL_JLCPCB.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for c in sorted(BD.C, key=lambda c: key(c["ref"])):
        m = fp[c["ref"]]; p = m.GetPosition(); x, y = ToMM(p.x), ToMM(p.y); name = c["fp"].split(":")[1]
        if c["ref"] == "U1":     # origine del footprint = centro della linea di pixel; JLCPCB vuole il centro del package (+0.305 in Y locale)
            import math; a = math.radians(m.GetOrientationDegrees()); x += 0.305 * math.sin(a); y += 0.305 * math.cos(a)
        rot = (m.GetOrientationDegrees() + ROT_FIX.get(name, 0)) % 360
        w.writerow([c["ref"], f"{x:.3f}mm", f"{-y:.3f}mm", "Top", f"{rot:.0f}"])
with open(PRJ + "/RazorSensor_BOM.csv", "w", newline="") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["Rif", "Valore", "Footprint", "Codice / note", "LCSC"])
    for c in BD.C: w.writerow([c["ref"], c["value"], c["fp"].split(":")[1], c["mpn"], c["lcsc"]])
print(len(BD.C), "componenti SMT in", len(groups), "righe BOM")
