# RazorBoard SMD v0.2 — definizione unica di componenti e collegamenti (sorgente per schema e PCB)
# Ogni componente: ref, value, symbol (lib:nome), footprint, pins {numero_pin: net}, block, opzioni grafiche
FP_R   = "Resistor_SMD:R_0603_1608Metric"
FP_C   = "Capacitor_SMD:C_0603_1608Metric"
FP_LED = "LED_SMD:LED_0603_1608Metric"
FP_D41 = "Diode_SMD:D_SOD-123"
FP_D35 = "Diode_SMD:D_SOD-123"
FP_SW  = "Button_Switch_THT:SW_PUSH_6mm"
FP_JP3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
def TB(n): return f"TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-{n}-5.08_1x{n:02d}_P5.08mm_Horizontal"

C = []
# lcsc = codice JLCPCB/LCSC (montaggio in fabbrica); "" = THT saldato a mano
def add(ref, value, symbol, fp, pins, block, rot=None, unit_pins=None, mpn="", lcsc=""):
    C.append(dict(ref=ref, value=value, symbol=symbol, fp=fp, pins={str(k): v for k, v in pins.items()},
                  block=block, rot=rot, mpn=mpn, lcsc=lcsc))
R_LCSC = {"0": ("0603WAF0000T5E", "C21189"), "100": ("0603WAF1000T5E", "C22775"), "470": ("0603WAF4700T5E", "C23179"),
          "1k": ("0603WAF1001T5E", "C21190"), "4.7k": ("0603WAF4701T5E", "C23162"), "10k": ("0603WAF1002T5E", "C25804"),
          "100k": ("0603WAF1003T5E", "C25803")}
C_LCSC = {"100nF": ("CC0603KRX7R9BB104 50V", "C14663", FP_C), "10nF": ("0603B103K500NT 50V", "C57112", FP_C),
          "1nF": ("CL10B102KB8NNNC 50V", "C1588", FP_C),
          "10uF 50V": ("CL31A106KBHNNNE", "C13585", "Capacitor_SMD:C_1206_3216Metric"),
          "22uF 25V": ("CL21A226MAQNNNE", "C45783", "Capacitor_SMD:C_0805_2012Metric"),
          "10uF 25V": ("CL21A106KAYNNNE", "C15850", "Capacitor_SMD:C_0805_2012Metric")}
LED_LCSC = {"verde": ("KT-0603G", "C12624"), "giallo": ("KT-0603Y", "C2287"),   # ex C72043 / C72038 (scorte basse JLCPCB)
            "rosso": ("KT-0603R", "C2286")}

def R(ref, val, a, b, block, mpn=""):
    m, l = R_LCSC[val]; add(ref, val, "Device:R", FP_R, {1: a, 2: b}, block, rot=90, mpn=m, lcsc=l)
def Cc(ref, val, a, b, block):
    m, l, fp = C_LCSC[val]; add(ref, val, "Device:C", fp, {1: a, 2: b}, block, rot=90, mpn=m, lcsc=l)
CP = lambda ref, val, p, n, block, fp=None: Cc(ref, val, p, "GND" if n == "GND" else n, block)   # elettrolitici -> MLCC
def LED(ref, val, a, k, block):
    m, l = LED_LCSC[val.split()[1]]; add(ref, val, "Device:LED", FP_LED, {1: k, 2: a}, block, mpn=m, lcsc=l)

# ------------------------------------------------------------------ ALIMENTAZIONE
B = "Alimentazione 24 V -> 5 V"
add("J1", "24V IN", "Connector:Screw_Terminal_01x02", TB(2), {1: "+24V_IN", 2: "GND"}, B)
add("F1", "PTC 0.5A 30V", "Device:Polyfuse", "Fuse:Fuse_1812_4532Metric",
    {1: "+24V_IN", 2: "+24V_F"}, B, rot=90, mpn="SMD1812P050TF/30 (hold 0.5A, trip 1A)", lcsc="C12559")
add("D1", "SS34", "Device:D_Schottky", "Diode_SMD:D_SMA", {1: "+24V", 2: "+24V_F"}, B, mpn="SS34 3A 40V", lcsc="C8678")
add("D2", "SMBJ33CA", "Device:D_TVS", "Diode_SMD:D_SMB", {1: "+24V", 2: "GND"}, B, mpn="SMBJ33CA", lcsc="C492017")
Cc("C1", "10uF 50V", "+24V", "GND", B)
Cc("C2", "100nF", "+24V", "GND", B)
add("U1", "TSR 2-2450", "Regulator_Switching:TSR_1-2450", "Converter_DCDC:Converter_DCDC_TRACO_TSR-1_THT",
    {1: "+24V", 2: "GND", 3: "+5V_BUCK"}, B, mpn="Traco TSR 2-2450 (5V 2A)")
Cc("C3", "10uF 25V", "+5V_BUCK", "GND", B)
add("J2", "5V EXT", "Connector:Screw_Terminal_01x02", TB(2), {1: "+5V_EXT", 2: "GND"}, B)
add("JP1", "SEL 5V", "Connector_Generic:Conn_01x03", FP_JP3, {1: "+5V_BUCK", 2: "+5V", 3: "+5V_EXT"}, B,
    mpn="Header 3 pin + jumper (1-2 = convertitore interno, 2-3 = 5V esterno)")
Cc("C4", "10uF 25V", "+5V", "GND", B)
Cc("C17", "10uF 25V", "+5V", "GND", B)
Cc("C5", "100nF", "+5V", "GND", B)
R("R1", "1k", "+5V", "LED_PWR", B)
LED("D3", "PWR verde", "LED_PWR", "GND", B)
add("D4", "B5819W", "Device:D_Schottky", FP_D41, {1: "M_VIN", 2: "+5V"}, B, mpn="B5819W SL (blocca ritorno da USB master)", lcsc="C8598")
add("D5", "B5819W", "Device:D_Schottky", FP_D41, {1: "S_VIN", 2: "+5V"}, B, mpn="B5819W SL (blocca ritorno da USB slave)", lcsc="C8598")

# ------------------------------------------------------------------ MODULI ESP32
M_PINS = ["3V3","GND","D15","D2","D4","RX2","TX2","D5","D18","D19","D21","RX0","TX0","D22","D23",
          "VIN","GND","D13","D12","D14","D27","D26","D25","D33","D32","D35","D34","VN","VP","EN"]
S_PINS = ["GND","GND","IO19","IO20","IO21","IO47","IO48","IO45","IO0","IO35","IO36","IO37","IO38","IO39","IO40","IO41","IO42","IO2","IO1","RX","TX","GND",
          "GND","5V","IO14","IO13","IO12","IO11","IO10","IO9","IO46","IO3","IO8","IO18","IO17","IO16","IO15","IO7","IO6","IO5","IO4","RST","3V3","3V3"]
m = {i + 1: None for i in range(30)}
m.update({1: "+3V3_M", 2: "GND", 6: "M_RX16", 7: "M_TX17", 16: "M_VIN", 17: "GND", 20: "M_WIFI_RST",
          21: "G_CLK_M", 22: "G_SI_M", 23: "G_LASER_M", 24: "ENC_B_3V", 25: "ENC_A_3V", 27: "G_AO_M"})
add("A1", "MASTER ESP32 DevKit V1 30p", "RazorBoard:ESP32_DevKitV1_30", "RazorBoard:ESP32_DevKitV1_30p_W25.4",
    m, "Master ESP32 (WROOM-32, 30 pin)", mpn="2x zoccolo femmina 1x15 passo 2.54, file a 25.4 mm")
s = {i + 1: None for i in range(30)}
s.update({1: "+3V3_S", 2: "GND", 6: "S_RX16", 7: "S_TX17", 16: "S_VIN", 17: "GND",
          23: "S_PUL", 22: "S_DIR", 21: "S_ENA", 25: "S_BTN_SCAN", 24: "S_BTN_FS", 27: "S_BTN_FO"})
add("A2", "SLAVE ESP32 DevKit V1 30p", "RazorBoard:ESP32_DevKitV1_30", "RazorBoard:ESP32_DevKitV1_30p_W25.4",
    s, "Slave ESP32 (WROOM-32, 30 pin)", mpn="2x zoccolo femmina 1x15 passo 2.54, file a 25.4 mm")

# ------------------------------------------------------------------ UART master <-> slave
B = "UART master <-> slave"
R("R10", "470", "M_TX17", "S_RX16", B)
R("R11", "470", "S_TX17", "M_RX16", B)
add("J7", "UART DEBUG", "Connector_Generic:Conn_01x03", FP_JP3, {1: "GND", 2: "M_TX17", 3: "S_TX17"}, B)

# ------------------------------------------------------------------ ENCODER LPD3806 (NPN open collector)
B = "Encoder LPD3806-600BM (NPN OC, 5 V)"
add("J4", "ENCODER", "Connector:Screw_Terminal_01x05", TB(5),
    {1: "+5V", 2: "GND", 3: "ENC_A_IN", 4: "ENC_B_IN", 5: "GND"}, B, mpn="rosso +5V, nero GND, verde A, bianco B, calza GND")
R("R30", "4.7k", "+3V3_M", "ENC_A_IN", B)
R("R31", "4.7k", "+3V3_M", "ENC_B_IN", B)
R("R32", "1k", "ENC_A_IN", "ENC_A_F", B)
R("R33", "1k", "ENC_B_IN", "ENC_B_F", B)
Cc("C7", "10nF", "ENC_A_F", "GND", B)
Cc("C8", "10nF", "ENC_B_F", "GND", B)
add("U3", "74HC14", "74xx:74HC14", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    {1: "ENC_A_F", 2: "ENC_A_N", 3: "ENC_A_N", 4: "ENC_A_3V", 5: "ENC_B_F", 6: "ENC_B_N",
     9: "ENC_B_N", 8: "ENC_B_3V", 11: "GND", 10: None, 13: "GND", 12: None, 14: "+3V3_M", 7: "GND"}, B,
    mpn="74HC14D,653 (a 3.3V, doppia inversione)", lcsc="C5605")
Cc("C9", "100nF", "+3V3_M", "GND", B)

# ------------------------------------------------------------------ DRIVER TB6600 (catodo comune)
B = "Uscite driver TB6600 (5 V, catodo comune)"
R("R20", "10k", "S_PUL", "GND", B)
R("R21", "10k", "S_DIR", "GND", B)
R("R22", "10k", "+3V3_S", "S_ENA", B)
add("U4", "74HCT245", "74xx:74LS245", "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm",
    {1: "+5V", 19: "GND", 20: "+5V", 10: "GND", 2: "S_PUL", 3: "S_DIR", 4: "S_ENA", 5: "GND", 6: "GND", 7: "GND", 8: "GND", 9: "GND",
     18: "PUL_5V", 17: "DIR_5V", 16: "ENA_5V", 15: None, 14: None, 13: None, 12: None, 11: None}, B,
    mpn="74HCT245D,653 (ingressi TTL, uscite 5V)", lcsc="C5979")
Cc("C6", "100nF", "+5V", "GND", B)
R("R23", "100", "PUL_5V", "TB_PUL", B)
R("R24", "100", "DIR_5V", "TB_DIR", B)
R("R25", "100", "ENA_5V", "TB_ENA", B)
R("R26", "1k", "PUL_5V", "LED_PUL", B); LED("D6", "PUL giallo", "LED_PUL", "GND", B)
R("R27", "1k", "DIR_5V", "LED_DIR", B); LED("D7", "DIR giallo", "LED_DIR", "GND", B)
R("R28", "1k", "ENA_5V", "LED_ENA", B); LED("D8", "ENA rosso", "LED_ENA", "GND", B)
add("J3", "TB6600", "Connector:Screw_Terminal_01x05", TB(5),
    {1: "TB_PUL", 2: "TB_DIR", 3: "TB_ENA", 4: "GND", 5: "+5V"}, B,
    mpn="PUL->PUL+, DIR->DIR+, ENA->ENA+, GND->PUL-/DIR-/ENA-, +5V solo per anodo comune")

# ------------------------------------------------------------------ RAZORGAUGE (TSL1401 + laser)
B = "Interfaccia RazorGauge (TSL1401 + laser)"
add("J5", "RAZORGAUGE", "Connector:Screw_Terminal_01x08", TB(8),
    {1: "+3V3_M", 2: "GND", 3: "G_SI", 4: "G_CLK", 5: "G_AO", 6: "LASER_P", 7: "LASER_N", 8: "GND"}, B,
    mpn="cavo schermato max 50 cm, calza al pin 8")
R("R40", "100", "G_SI_M", "G_SI", B)
R("R41", "100", "G_CLK_M", "G_CLK", B)
R("R42", "100", "G_AO", "G_AO_M", B)
Cc("C10", "1nF", "G_AO_M", "GND", B)
add("D9", "1N4148W", "Device:D", FP_D35, {1: "+3V3_M", 2: "G_AO_M"}, B, mpn="1N4148W", lcsc="C81598")
add("D10", "1N4148W", "Device:D", FP_D35, {1: "G_AO_M", 2: "GND"}, B, mpn="1N4148W", lcsc="C81598")
Cc("C11", "10uF 25V", "+3V3_M", "GND", B)
Cc("C12", "100nF", "+3V3_M", "GND", B)
add("JP2", "SEL LASER", "Connector_Generic:Conn_01x03", FP_JP3, {1: "+3V3_M", 2: "LASER_SEL", 3: "+5V"}, B,
    mpn="Header 3 pin + jumper (1-2 = laser a 3.3V, 2-3 = laser a 5V)")
R("R43", "0", "LASER_SEL", "LASER_P", B)
add("Q1", "2N7002", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23",
    {1: "LASER_G", 2: "GND", 3: "LASER_N"}, B, mpn="2N7002 (60V 115mA)", lcsc="C8545")
R("R44", "100", "G_LASER_M", "LASER_G", B)
R("R45", "100k", "LASER_G", "GND", B)

# ------------------------------------------------------------------ PULSANTI
B = "Pulsanti (a bordo + morsetti)"
for i, (sw, n, rpu, rs, cc, net, dom) in enumerate([
        ("SW1", "SCAN", "R52", "R53", "C14", "S_BTN_SCAN", "+3V3_S"),
        ("SW2", "FAST_S", "R54", "R55", "C15", "S_BTN_FS", "+3V3_S"),
        ("SW3", "FAST_O", "R56", "R57", "C16", "S_BTN_FO", "+3V3_S"),
        ("SW4", "WIFI_RST", "R50", "R51", "C13", "M_WIFI_RST", "+3V3_M")]):
    node = "BTN_" + n
    add(sw, n, "Switch:SW_Push", FP_SW, {1: node, 2: "GND"}, B)
    R(rpu, "10k", dom, node, B)
    R(rs, "1k", node, net, B)
    Cc(cc, "100nF", net, "GND", B)
add("J6", "PULSANTI", "Connector:Screw_Terminal_01x05", TB(5),
    {1: "BTN_SCAN", 2: "BTN_FAST_S", 3: "BTN_FAST_O", 4: "BTN_WIFI_RST", 5: "GND"}, B)

# ------------------------------------------------------------------ MECCANICA
B = "Fori di fissaggio"
for i in range(1, 5):
    add(f"H{i}", "M3", "Mechanical:MountingHole_Pad", "MountingHole:MountingHole_3.2mm_M3_Pad", {1: "GND"}, B)

def nets():
    n = {}
    for c in C:
        for p, net in c["pins"].items():
            if net: n.setdefault(net, []).append((c["ref"], p))
    return n

if __name__ == "__main__":
    N = nets()
    print(len(C), "componenti,", len(N), "net")
    for k, v in sorted(N.items()):
        if len(v) < 2: print("NET CON UN SOLO PIN:", k, v)
    refs = [c["ref"] for c in C]; assert len(refs) == len(set(refs)), "ref duplicati"
