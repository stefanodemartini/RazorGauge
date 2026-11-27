#!/usr/bin/env python3
"""Verifica elettrica della scheda RazorSensor (27/11/2026, dopo l'errore di piedinatura di U2 della v1).

Legge scheda_sensore/script/sens_def.py (collegamenti voluti), scheda_sensore/pinout_datasheet.json (piedinature dal
datasheet) e scheda_sensore/RazorSensor.kicad_pcb (rete di ogni pad). Controlli:
  a) ogni pad: numero -> funzione (datasheet) -> rete voluta (sens_def) == rete del pad nel PCB;
  b) operazionali: uscita chiusa sull'ingresso INVERTENTE con un percorso resistivo; nessun percorso OUT -> IN+ senza
     percorso verso IN-; ingressi non flottanti; alimentazioni su VDD/GND;
  c) nessuna rete con un solo pad; nessuna uscita su una rete di alimentazione;
  d) simulazione DC dalla netlist (calcolo nodale, operazionale con guadagno 1e5 limitato tra 0 e VDD): AO_RAW 0..2.0 V,
     confronto con Vout = 0.958*AO + 0.154 V (tolleranza 10 mV) e segno della reazione (dVdiff/dVout < 0).

Uso:
  python strumenti/verifica_elettrica_scheda.py                  # definizione attuale (rev 1.2) -> deve dare tutto OK
  python strumenti/verifica_elettrica_scheda.py --v1             # definizione v1 (TI LMV321IDBVR) -> deve dare ERRORE
  python strumenti/verifica_elettrica_scheda.py --non-regressione --out scheda_sensore/verifica_elettrica_<data>.txt
Codice di uscita != 0 se c'e' un errore (con --non-regressione: se la v1 NON da' errore o la rev 1.2 non e' tutta OK).
"""
import argparse, copy, importlib.util, io, json, os, re, shutil, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENS = os.path.join(ROOT, "scheda_sensore")
PCB = os.path.join(SENS, "RazorSensor.kicad_pcb")
SUPPLY = {"GND": 0.0, "VDD": 3.3}
SRC_NET, OBS_NET = "AO_RAW", "AO_BUF"          # ingresso (uscita del TSL1401CL) e uscita verso l'ADC
GAIN, OFFSET, TOL = 0.958, 0.154, 0.010
A_OL = 1e5

# ------------------------------------------------------------------ lettura dei dati
def load_sens_def():
    spec = importlib.util.spec_from_file_location("sens_def", os.path.join(SENS, "script", "sens_def.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def v1_definition(comps):
    """Definizione della v1 com'era: U2 TI LMV321IDBVR collegato per NUMERO 1 AO_BUF / 2 GND / 3 VP / 4 VN / 5 VDD."""
    comps = copy.deepcopy(comps)
    for c in comps:
        if c["ref"] == "U2":
            c.update(part="LMV321IDBVR", value="LMV321", lcsc="C7972",
                     pins={"1": "AO_BUF", "2": "GND", "3": "VP", "4": "VN", "5": "VDD"})
    return comps

def sexpr(text):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack, cur = [], []
    for t in tok:
        if t == "(": stack.append(cur); cur = []
        elif t == ")": node = cur; cur = stack.pop(); cur.append(node)
        else: cur.append(t[1:-1] if t.startswith('"') else t)
    return cur[0]

def pcb_pads(path):
    """-> {ref: {pad: net or None}}"""
    tree = sexpr(open(path, encoding="utf-8").read()); res = {}
    for fp in (n for n in tree if isinstance(n, list) and n and n[0] == "footprint"):
        ref = None
        for n in fp:
            if isinstance(n, list) and len(n) > 2 and ((n[0] == "fp_text" and n[1] == "reference") or
                                                      (n[0] == "property" and n[1] == "Reference")):
                ref = n[2]
        pads = {}
        for n in fp:
            if isinstance(n, list) and n and n[0] == "pad" and n[1] != "":
                net = next((x for x in n if isinstance(x, list) and x and x[0] == "net"), None)
                pads[n[1]] = (net[-1] if net else None) or None
        if ref: res[ref] = pads
    return res

# ------------------------------------------------------------------ controlli
class Report:
    def __init__(self): self.out = io.StringIO(); self.errors = 0
    def line(self, s=""): self.out.write(s + "\n")
    def ok(self, s): self.line(f"  OK      {s}")
    def err(self, s): self.errors += 1; self.line(f"  ERRORE  {s}")

def verify(comps, pinout, pads, label):
    R = Report(); R.line(f"=== {label}")
    parts = dict(pinout["parts"], **{k: v for k, v in pinout["incompatible_with_pcb_v1"].items() if not k.startswith("_")})

    # a) pad -> funzione -> rete voluta == rete del PCB
    R.line("a) pad -> funzione (datasheet) -> rete voluta (sens_def) == rete del PCB")
    for c in comps:
        ref = c["ref"]; pp = pads.get(ref)
        if pp is None: R.err(f"{ref}: footprint assente nel PCB"); continue
        po = parts.get(c.get("part", "")) if c.get("part") else None
        for num in sorted(set(pp) | set(c["pins"]), key=lambda x: (len(x), x)):
            want, got = c["pins"].get(num), pp.get(num)
            fn = f" {po['pins'].get(num, '?')}" if po else ""
            if po and num not in po["pins"]: R.err(f"{ref} pad {num}: non esiste nel datasheet di {c['part']}"); continue
            if want == got:
                if po: R.ok(f"{ref} pad {num}{fn:5s}: rete {want or '(NC)'}  [{c['part']}]")
            else:
                R.err(f"{ref} pad {num}{fn}: sens_def {want} ma PCB {got}")
    n_other = sum(len(c["pins"]) for c in comps if not c.get("part"))
    R.line(f"  (controllati anche {n_other} pad di R, C, J1 per numero)")

    # rete -> pad dal PCB (verita' fisica)
    nets = {}
    for ref, pp in pads.items():
        for num, net in pp.items():
            if net: nets.setdefault(net, []).append((ref, num))
    res = [(c["pins"].get("1"), c["pins"].get("2"), c["ref"], float(_ohm(c["value"])))
           for c in comps if c["symbol"] == "Device:R"]

    # b) operazionali
    R.line("b) operazionali: reazione, ingressi, alimentazioni")
    opamps = [c for c in comps if c.get("part") and parts[c["part"]].get("type") == "opamp"]
    for c in opamps:
        po = parts[c["part"]]; fnet = {po["pins"][n]: pads[c["ref"]].get(n) for n in po["pins"]}
        o, ip, im = fnet["OUT"], fnet["IN+"], fnet["IN-"]
        R.line(f"  {c['ref']} {c['part']}: OUT={o}  IN+={ip}  IN-={im}  V+={fnet['V+']}  V-={fnet['V-']}")
        (R.ok if fnet["V+"] == "VDD" else R.err)(f"{c['ref']} V+ su {fnet['V+']} (atteso VDD)")
        (R.ok if fnet["V-"] == "GND" else R.err)(f"{c['ref']} V- su {fnet['V-']} (atteso GND)")
        p_inv, p_non = _rpath(res, o, im), _rpath(res, o, ip)
        if p_inv: R.ok(f"{c['ref']} uscita chiusa sull'ingresso invertente: {' -> '.join(p_inv)}")
        else: R.err(f"{c['ref']} nessun percorso resistivo OUT ({o}) -> IN- ({im}): manca la reazione negativa")
        if p_non and not p_inv: R.err(f"{c['ref']} percorso OUT ({o}) -> IN+ ({ip}) senza percorso verso IN-: REAZIONE POSITIVA ({' -> '.join(p_non)})")
        elif p_non: R.line(f"  nota    {c['ref']} anche percorso OUT -> IN+ ({' -> '.join(p_non)}): decide la simulazione d)")
        for nm, n in (("IN+", ip), ("IN-", im)):
            drv = _rpath(res, n, None, targets=set(SUPPLY) | {SRC_NET, o})
            (R.ok if drv else R.err)(f"{c['ref']} {nm} ({n}) " + ("riferito in DC: " + " -> ".join(drv) if drv else "FLOTTANTE"))

    # c) reti con un solo pad, uscite su alimentazioni
    R.line("c) reti")
    singles = [n for n, v in nets.items() if len(v) < 2]
    if singles: [R.err(f"rete {n} con un solo pad: {nets[n]}") for n in singles]
    else: R.ok(f"{len(nets)} reti, nessuna con un solo pad")
    for c in opamps:
        o = pads[c["ref"]].get(next(n for n, f in parts[c["part"]]["pins"].items() if f == "OUT"))
        (R.err if o in SUPPLY else R.ok)(f"{c['ref']} uscita su {o}" + (" = ALIMENTAZIONE" if o in SUPPLY else " (non alimentazione)"))

    # d) simulazione DC
    R.line("d) simulazione DC (calcolo nodale, A = 1e5, uscita limitata 0..VDD)"
           + ("" if shutil.which("ngspice") else "; ngspice non installato"))
    for c in opamps:
        po = parts[c["part"]]; fnet = {po["pins"][n]: pads[c["ref"]].get(n) for n in po["pins"]}
        R.line(f"  {c['ref']}: AO_RAW [V] | dVdiff/dVout | {OBS_NET} [V] | atteso [V] | scarto [mV]")
        worst, signs = 0.0, set()
        for k in range(21):
            ao = 0.1 * k
            vo, b, obs = _simulate(res, fnet, ao)
            signs.add("neg" if b < 0 else "POS")
            exp = GAIN * ao + OFFSET; dev = (obs - exp) * 1000; worst = max(worst, abs(dev))
            R.line(f"     {ao:4.1f}    | {b:+8.4f}     | {obs:7.4f}  | {exp:7.4f}  | {dev:+8.1f}")
        if signs == {"neg"}: R.ok(f"{c['ref']} reazione negativa (dVdiff/dVout < 0) su tutta la gamma")
        else: R.err(f"{c['ref']} reazione POSITIVA (dVdiff/dVout > 0): uscita bloccata su un'alimentazione")
        (R.ok if worst <= TOL * 1000 else R.err)(f"{c['ref']} {OBS_NET} = 0.958*AO + 0.154 V entro 10 mV (scarto massimo {worst:.1f} mV)")
    R.line(f"ESITO {label}: " + ("TUTTO OK" if R.errors == 0 else f"ERRORE ({R.errors})"))
    return R

def _ohm(v):
    v = v.lower().replace("r", ""); mul = 1
    if v.endswith("k"): mul, v = 1e3, v[:-1]
    if v.endswith("m"): mul, v = 1e6, v[:-1]
    return float(v) * mul

def _rpath(res, a, b, targets=None):
    """Percorso fra reti attraverso resistori, senza passare per le alimentazioni (che possono solo essere la meta)."""
    if a is None: return None
    goal = targets if targets is not None else {b}
    if a in goal and targets is not None and a != b: return [a]
    prev, todo = {a: None}, [a]
    while todo:
        n = todo.pop(0)
        if n in goal and n != a: break
        if n in SUPPLY and n != a: continue
        for x, y, ref, _ in res:
            for p, q in ((x, y), (y, x)):
                if p == n and q and q not in prev: prev[q] = (n, ref); todo.append(q)
    hit = next((g for g in goal if g in prev and g != a), None)
    if hit is None: return None
    path, n = [hit], hit
    while prev[n]: n, ref = prev[n]; path[:0] = [n, ref]
    return path

def _solve(res, fixed):
    """Tensioni dei nodi raggiungibili dai nodi fissati attraverso resistori."""
    known = set(fixed); nodes = set()
    todo = list(known)
    while todo:
        n = todo.pop()
        for x, y, _, _ in res:
            for p, q in ((x, y), (y, x)):
                if p == n and q and q not in known and q not in nodes: nodes.add(q); todo.append(q)
    nodes = sorted(nodes); ix = {n: i for i, n in enumerate(nodes)}
    G = np.zeros((len(nodes), len(nodes))); I = np.zeros(len(nodes))
    for x, y, _, r in res:
        g = 1.0 / r
        for p, q in ((x, y), (y, x)):
            if p in ix:
                G[ix[p], ix[p]] += g
                if q in ix: G[ix[p], ix[q]] -= g
                elif q in fixed: I[ix[p]] += g * fixed[q]
    V = dict(fixed)
    if nodes: V.update(zip(nodes, np.linalg.solve(G, I)))
    return V

def _simulate(res, fnet, ao):
    """Uscita dell'operazionale come sorgente: vdiff = a + b*Vout; poi anello chiuso con A = 1e5, limitato 0..VDD."""
    o, ip, im = fnet["OUT"], fnet["IN+"], fnet["IN-"]
    def vd(vout):
        V = _solve(res, dict(SUPPLY, **{SRC_NET: ao, o: vout}))
        return V[ip] - V[im], V
    d0, _ = vd(0.0); d1, _ = vd(1.0)
    a, b = d0, d1 - d0
    if b < 0:
        vout = min(max(A_OL * a / (1 - A_OL * b), 0.0), SUPPLY["VDD"])
    else:   # reazione positiva: stati stabili solo sulle alimentazioni (si sceglie quello raggiunto partendo da 0 V)
        vout = SUPPLY["VDD"] if a > 0 else 0.0
    _, V = vd(vout)
    return vout, b, V.get(OBS_NET, float("nan"))

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", action="store_true", help="verifica la definizione v1 (TI LMV321IDBVR): deve dare ERRORE")
    ap.add_argument("--non-regressione", action="store_true", help="v1 deve dare ERRORE e la definizione attuale tutto OK")
    ap.add_argument("--out", help="scrive anche l'esito su questo file")
    a = ap.parse_args()
    sd = load_sens_def(); pinout = json.load(open(os.path.join(SENS, "pinout_datasheet.json"), encoding="utf-8"))
    pads = pcb_pads(PCB)
    head = (f"Verifica elettrica RazorSensor - {__import__('datetime').date.today():%d/%m/%Y}\n"
            f"PCB: scheda_sensore/RazorSensor.kicad_pcb  definizione: scheda_sensore/script/sens_def.py  "
            f"piedinature: scheda_sensore/pinout_datasheet.json\n")
    if a.non_regressione:
        r1 = verify(v1_definition(sd.C), pinout, pads, "v1 (U2 = TI LMV321IDBVR, per numero) - atteso ERRORE")
        r2 = verify(sd.C, pinout, pads, "rev 1.2 (U2 = MCP6001T-I/OT, per nome di pin) - atteso TUTTO OK")
        ok = r1.errors > 0 and r2.errors == 0
        text = head + "\n" + r1.out.getvalue() + "\n" + r2.out.getvalue() + \
            f"\nTEST DI NON REGRESSIONE: {'SUPERATO' if ok else 'FALLITO'} (v1 {'ERRORE' if r1.errors else 'OK'}, rev 1.2 {'OK' if not r2.errors else 'ERRORE'})\n"
        code = 0 if ok else 1
    else:
        r = verify(v1_definition(sd.C) if a.v1 else sd.C, pinout, pads, "v1 (TI LMV321IDBVR)" if a.v1 else "definizione attuale")
        text, code = head + "\n" + r.out.getvalue(), (1 if r.errors else 0)
    sys.stdout.write(text)
    if a.out: open(a.out, "w", encoding="utf-8").write(text)
    sys.exit(code)

if __name__ == "__main__":
    main()
