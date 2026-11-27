# RazorGauge - scheda sensore TSL1401CL v1 (28/10/2026): definizione unica di componenti e collegamenti
# Scheda 24 x 18 mm, 2 strati, tutto SMD sul lato TOP, montaggio JLCPCB (TSL1401CL = C2802316, Extended, pre-ordine)
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
C = []
def add(ref, value, symbol, fp, pins, block, rot=None, mpn="", lcsc="", part=""):
    C.append(dict(ref=ref, value=value, symbol=symbol, fp=fp, pins={str(k): v for k, v in pins.items()},
                  block=block, rot=rot, mpn=mpn, lcsc=lcsc, part=part))

# 27/11/2026 (errore U2 della v1, vedi ANALISI_ERRORE_U2.md): i circuiti integrati si collegano per NOME di funzione.
# I numeri dei pin vengono SOLO da ../pinout_datasheet.json (preso dal datasheet del codice esatto, con pagina).
# Errore bloccante se un nome non esiste nel datasheet o se un pin resta senza rete senza essere dichiarato NC.
import json as _json, os as _os
PINOUT_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "pinout_datasheet.json")
with open(PINOUT_FILE, encoding="utf-8") as _f:
    PINOUT = _json.load(_f)
def pinout(part):
    if part in PINOUT["parts"]: return PINOUT["parts"][part]
    if part in PINOUT["incompatible_with_pcb_v1"]: return PINOUT["incompatible_with_pcb_v1"][part]
    raise SystemExit(f"ERRORE: {part} non e' in pinout_datasheet.json: aggiungilo dal datasheet prima di usarlo")
def ic(ref, value, symbol, fp, part, conn, block, nc=(), mpn=None):
    """conn: {funzione: rete}; una funzione su piu' pin (es. GND del TSL1401CL) collega tutti i suoi pin.
    nc: funzioni lasciate scollegate di proposito (es. 'NC')."""
    po = pinout(part); byfn = {}
    for num, fn in po["pins"].items(): byfn.setdefault(fn, []).append(num)
    pins = {}
    for fn, net in conn.items():
        if fn not in byfn: raise SystemExit(f"ERRORE {ref}: funzione '{fn}' assente nel datasheet di {part} {sorted(byfn)}")
        for num in byfn[fn]: pins[num] = net
    for fn in nc:
        if fn not in byfn: raise SystemExit(f"ERRORE {ref}: funzione NC '{fn}' assente nel datasheet di {part}")
        for num in byfn[fn]: pins[num] = None
    free = sorted(set(po["pins"]) - set(pins), key=int)
    if free: raise SystemExit(f"ERRORE {ref} ({part}): pin {free} ({[po['pins'][n] for n in free]}) senza rete e non dichiarati NC")
    add(ref, value, symbol, fp, {int(k): v for k, v in sorted(pins.items(), key=lambda kv: int(kv[0]))}, block,
        mpn=mpn or f"{po['manufacturer']} {po['mpn']}", lcsc=po.get("lcsc", ""), part=part)
R_LCSC = {"100": ("0603WAF1000T5E", "C22775"), "330": ("0603WAF3300T5E", "C23138"), "4.7k": ("0603WAF4701T5E", "C23162"),
          "10k": ("0603WAF1002T5E", "C25804"), "100k": ("0603WAF1003T5E", "C25803")}
C_LCSC = {"100nF": ("CC0603KRX7R9BB104 50V", "C14663", FP_C),
          "10uF": ("CL21A106KAYNNNE 25V", "C15850", "Capacitor_SMD:C_0805_2012Metric")}
def R(ref, val, a, b, block):
    m, l = R_LCSC[val]; add(ref, val, "Device:R", FP_R, {1: a, 2: b}, block, rot=90, mpn=m, lcsc=l)
def Cc(ref, val, a, b, block):
    m, l, fp = C_LCSC[val]; add(ref, val, "Device:C", fp, {1: a, 2: b}, block, rot=90, mpn=m, lcsc=l)

B = "Sensore TSL1401CL"
ic("U1", "TSL1401CL", "RazorSensor:TSL1401CL", "RazorSensor:TSL1401CL_ams_CL", "TSL1401CL",
   {"SI": "SI_S", "CLK": "CLK_S", "AO": "AO_RAW", "VDD": "VDD", "GND": "GND"}, B, nc=("NC",),
   mpn="ams TSL1401CL (128x1, package CL, MSL 5a da datasheet)")
Cc("C1", "100nF", "VDD", "GND", B)                 # datasheet: 0.1 uF il piu vicino possibile al pin VDD
Cc("C2", "10uF", "VDD", "GND", B)
R("R1", "100", "SI", "SI_S", B)                    # smorzamento sul cavo
R("R2", "100", "CLK", "CLK_S", B)
R("R3", "330", "AO_RAW", "GND", B)                 # carico dell'uscita (condizione di prova del datasheet: RL = 330)

B = "Buffer AO con offset (+0.15 V, guadagno ~0.96)"
# rev 1.2 (27/11/2026): U2 = Microchip MCP6001T-I/OT (1 OUT / 2 V- / 3 IN+ / 4 IN- / 5 V+, DS20001733L tab. 3-1).
# La v1 aveva il TI LMV321IDBVR collegato per numero con una piedinatura presa a memoria -> reazione positiva.
# Netlist risultante identica al PCB v1: 1 AO_BUF, 2 GND, 3 VP, 4 VN, 5 VDD.
ic("U2", "MCP6001", "Amplifier_Operational:MCP6001-OT", "Package_TO_SOT_SMD:SOT-23-5", "MCP6001T-I/OT",
   {"OUT": "AO_BUF", "V-": "GND", "IN+": "VP", "IN-": "VN", "V+": "VDD"}, B,
   mpn="Microchip MCP6001T-I/OT (rail-to-rail in/out, 1 MHz, 0.6 V/us) - NON LMV321/MCP6001R/MCP6001U")
Cc("C4", "100nF", "VDD", "GND", B)
R("R4", "10k", "AO_RAW", "VP", B)                  # V+ = (AO*Rb' + Vref*Ra)/(Ra+Rb'), Ra = R4
R("R5", "100k", "VDD", "VREF", B)                  # partitore: Vref = 3.3*4.7/104.7 = 0.148 V, Rth 4.49k
R("R6", "4.7k", "VREF", "GND", B)
Cc("C3", "100nF", "VREF", "GND", B)
R("R7", "4.7k", "VREF", "VP", B)                   # Rb' = R7 + Rth = 9.19k
R("R8", "10k", "AO_BUF", "VN", B)                  # guadagno non invertente 2
R("R9", "10k", "VN", "GND", B)                     # -> Vout = 0.958*AO + 0.154 V
R("R10", "100", "AO_BUF", "AO", B)                 # isolamento verso cavo e filtro della RazorBoard

B = "Cavo verso RazorBoard J5 (saldato)"
# 31/10/2026 (Stefano): niente connettore, il cavo si salda su 5 piazzole passanti (passo 2 mm, foro 0.8). La calza del cavo
# schermato va SOLO a J5-8 sulla RazorBoard (lato sensore isolata, niente anello di massa). J1 non e' montato da JLCPCB.
add("J1", "Cavo 5 fili", "Connector_Generic:Conn_01x05", "Connector_PinHeader_2.00mm:PinHeader_1x05_P2.00mm_Vertical",
    {1: "VDD", 2: "GND", 3: "SI", 4: "CLK", 5: "AO"}, B,
    mpn="piazzole per saldare il cavo: 1 3V3 / 2 GND / 3 SI / 4 CLK / 5 AO (= J5 pin 1-5; calza solo su J5-8) - NON MONTARE", lcsc="")

def nets():
    n = {}
    for c in C:
        for p, net in c["pins"].items():
            if net: n.setdefault(net, []).append((c["ref"], p))
    return n
if __name__ == "__main__":
    for k, v in sorted(nets().items()): print(k, v)
