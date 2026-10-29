# RazorGauge - scheda sensore TSL1401CL v1 (28/10/2026): definizione unica di componenti e collegamenti
# Scheda 24 x 18 mm, 2 strati, tutto SMD sul lato TOP, montaggio JLCPCB (TSL1401CL = C2802316, Extended, pre-ordine)
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
C = []
def add(ref, value, symbol, fp, pins, block, rot=None, mpn="", lcsc=""):
    C.append(dict(ref=ref, value=value, symbol=symbol, fp=fp, pins={str(k): v for k, v in pins.items()},
                  block=block, rot=rot, mpn=mpn, lcsc=lcsc))
R_LCSC = {"100": ("0603WAF1000T5E", "C22775"), "330": ("0603WAF3300T5E", "C23138"), "4.7k": ("0603WAF4701T5E", "C23162"),
          "10k": ("0603WAF1002T5E", "C25804"), "100k": ("0603WAF1003T5E", "C25803")}
C_LCSC = {"100nF": ("CC0603KRX7R9BB104 50V", "C14663", FP_C),
          "10uF": ("CL21A106KAYNNNE 25V", "C15850", "Capacitor_SMD:C_0805_2012Metric")}
def R(ref, val, a, b, block):
    m, l = R_LCSC[val]; add(ref, val, "Device:R", FP_R, {1: a, 2: b}, block, rot=90, mpn=m, lcsc=l)
def Cc(ref, val, a, b, block):
    m, l, fp = C_LCSC[val]; add(ref, val, "Device:C", fp, {1: a, 2: b}, block, rot=90, mpn=m, lcsc=l)

B = "Sensore TSL1401CL"
add("U1", "TSL1401CL", "RazorSensor:TSL1401CL", "RazorSensor:TSL1401CL_ams_CL",
    {1: "SI_S", 2: "CLK_S", 3: "AO_RAW", 4: "VDD", 5: None, 6: "GND", 7: "GND", 8: None}, B,
    mpn="ams TSL1401CL (128x1, package CL, MSL 5a da datasheet)", lcsc="C2802316")
Cc("C1", "100nF", "VDD", "GND", B)                 # datasheet: 0.1 uF il piu vicino possibile al pin VDD
Cc("C2", "10uF", "VDD", "GND", B)
R("R1", "100", "SI", "SI_S", B)                    # smorzamento sul cavo
R("R2", "100", "CLK", "CLK_S", B)
R("R3", "330", "AO_RAW", "GND", B)                 # carico dell'uscita (condizione di prova del datasheet: RL = 330)

B = "Buffer AO con offset (+0.15 V, guadagno ~0.96)"
add("U2", "LMV321", "Amplifier_Operational:LMV321", "Package_TO_SOT_SMD:SOT-23-5",
    {1: "AO_BUF", 2: "GND", 3: "VP", 4: "VN", 5: "VDD"}, B, mpn="TI LMV321IDBVR (rail-to-rail out, 1 MHz)", lcsc="C7972")
Cc("C4", "100nF", "VDD", "GND", B)
R("R4", "10k", "AO_RAW", "VP", B)                  # V+ = (AO*Rb' + Vref*Ra)/(Ra+Rb'), Ra = R4
R("R5", "100k", "VDD", "VREF", B)                  # partitore: Vref = 3.3*4.7/104.7 = 0.148 V, Rth 4.49k
R("R6", "4.7k", "VREF", "GND", B)
Cc("C3", "100nF", "VREF", "GND", B)
R("R7", "4.7k", "VREF", "VP", B)                   # Rb' = R7 + Rth = 9.19k
R("R8", "10k", "AO_BUF", "VN", B)                  # guadagno non invertente 2
R("R9", "10k", "VN", "GND", B)                     # -> Vout = 0.958*AO + 0.154 V
R("R10", "100", "AO_BUF", "AO", B)                 # isolamento verso cavo e filtro della RazorBoard

B = "Connettore verso RazorBoard J5"
add("J1", "GH 6p", "Connector_Generic:Conn_01x06", "Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal",
    {1: "VDD", 2: "GND", 3: "SI", 4: "CLK", 5: "AO", 6: "GND"}, B,
    mpn="JST SM06B-GHS-TB(LF)(SN) - cavo: 1 3V3 / 2 GND / 3 SI / 4 CLK / 5 AO / 6 calza (= J5 pin 1-5, 8)", lcsc="C133065")

def nets():
    n = {}
    for c in C:
        for p, net in c["pins"].items():
            if net: n.setdefault(net, []).append((c["ref"], p))
    return n
if __name__ == "__main__":
    for k, v in sorted(nets().items()): print(k, v)
