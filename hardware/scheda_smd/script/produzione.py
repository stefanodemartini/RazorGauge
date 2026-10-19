# RazorBoard SMD: file di produzione per JLCPCB (Gerber + foratura zip, BOM, CPL) + BOM completa
import csv, os, subprocess, zipfile, collections, pcbnew
from pcbnew import ToMM
import board_def as BD

PRJ = "/home/claude/board_smd/RazorBoard"
OUT = PRJ + "/produzione"
os.makedirs(OUT + "/gerber", exist_ok=True)
PCB = PRJ + "/RazorBoard.kicad_pcb"
env = dict(os.environ, HOME="/tmp/kh")

# --- Gerber + foratura
layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask",
                "--no-x2", "-o", OUT + "/gerber/", PCB], check=True, env=env, capture_output=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
                "--generate-map", "--map-format", "gerberx2", "-o", OUT + "/gerber/", PCB], check=True, env=env, capture_output=True)
with zipfile.ZipFile(OUT + "/RazorBoard_SMD_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT + "/gerber")):
        z.write(OUT + "/gerber/" + f, f)

# --- BOM e CPL per il montaggio (solo componenti con codice LCSC, tutti sul lato TOP)
board = pcbnew.LoadBoard(PCB)
fp = {f.GetReference(): f for f in board.GetFootprints()}
smd = [c for c in BD.C if c.get("lcsc")]
groups = collections.OrderedDict()
for c in sorted(smd, key=lambda c: (c["lcsc"], c["ref"])):
    val = ("LED " + c["value"].split()[-1]) if c["symbol"] == "Device:LED" else c["value"]
    groups.setdefault((val, c["fp"].split(":")[1], c["lcsc"]), []).append(c["ref"])
with open(OUT + "/RazorBoard_SMD_BOM_JLCPCB.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, foot, lcsc), refs in groups.items():
        w.writerow([val, ",".join(sorted(refs, key=lambda r: (r[0], int(''.join(ch for ch in r if ch.isdigit()))))), foot, lcsc])
with open(OUT + "/RazorBoard_SMD_CPL_JLCPCB.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for c in smd:
        m = fp[c["ref"]]; p = m.GetPosition()
        w.writerow([c["ref"], f"{ToMM(p.x):.3f}mm", f"{-ToMM(p.y):.3f}mm", "Top", f"{m.GetOrientationDegrees() % 360:.0f}"])

# --- BOM completa (fabbrica + saldatura a mano)
with open(PRJ + "/RazorBoard_SMD_BOM.csv", "w", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Rif", "Valore", "Footprint", "Codice / note", "LCSC", "Montaggio"])
    for c in BD.C:
        w.writerow([c["ref"], c["value"], c["fp"].split(":")[1], c["mpn"], c.get("lcsc", ""),
                    "fabbrica (SMT)" if c.get("lcsc") else "a mano (THT)"])
print(len(smd), "componenti SMT in", len(groups), "righe BOM;", len(BD.C) - len(smd), "a mano")
