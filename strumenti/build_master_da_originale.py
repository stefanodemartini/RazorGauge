L=open('master_orig.ino').read().split('\n')
def cut(a,b):
    for i in range(a-1,b): L[i]=None
assert L[571].strip().startswith('server.on("/", []() {') and L[1942].strip()=='});'
cut(572,1943)
assert 'Caliper ISR' in L[291] and L[324].strip()=='}'
cut(292,325)
assert L[2133].startswith('// ---') and L[2224].strip()=='}' and 'readCaliperBufferedMedian' in L[2210]
cut(2134,2225)
assert 'Caliper ISR state' in L[167]
cut(168,175)
assert 'Rolling caliper buffer' in L[188] and 'calRollingIdx' in L[193]
cut(189,194)
assert L[2032].startswith('float readCaliperDisplay')
cut(2033,2037)
src='\n'.join(x for x in L if x is not None)
rep=[
('#define FIRMWARE_VERSION "0.4.22"','#define FIRMWARE_VERSION "0.5.0"'),
('#define FIRMWARE_DATE "2026-05-29"','#define FIRMWARE_DATE "2026-09-30"'),
('+ hardware PCNT encoder (ISR-immune)"','+ hardware PCNT encoder (ISR-immune) + RazorGauge optical shadow gauge (replaces caliper) + web UI removed (WPF app via WebSocket)"'),
('#include "driver/pcnt.h"  // ESP32 hardware pulse counter — immune to ISR interference',
 '#include <Preferences.h>\n#include "driver/pcnt.h"  // ESP32 hardware pulse counter — immune to ISR interference'),
('''#define CALIPER_DATA_PIN 27
#define CALIPER_CLOCK_PIN 26
''','''// RazorGauge (TSL1401 + laser) — riusa i pin del vecchio calibro + 2 pin nuovi
#define GAUGE_SI_PIN    26   // ex CALIPER_CLOCK_PIN
#define GAUGE_CLK_PIN   27   // ex CALIPER_DATA_PIN
#define GAUGE_AO_PIN    34   // ADC1_CH6, solo ingresso. NON usare pin ADC2 (conflitto con il WiFi)
#define GAUGE_LASER_PIN 25   // comando laser via NPN/MOSFET
// Distanza (cm) tra la ruota dell'encoder e il punto di misura.
// Con il calibro era 2.0 cm ("encoder wheel is 20 mm behind caliper"): MISURARE e aggiornare per RazorGauge.
#define MEAS_OFFSET_CM  2.0f
'''),
('float caliperZeroOffset = 0.0;','float caliperZeroOffset = 0.0;   // offset additivo (nome storico, EEPROM addr 0) — applicato anche a RazorGauge'),
('float displayZeroValue = 0.0;','float displayZeroValue = 0.0;    // con RazorGauge resta 0 (lo zero ottico è intrinseco)'),
('WebSocketsServer webSocket(81);','WebSocketsServer webSocket(81);\n\n#include "gauge_module.inc"'),
('''void readCaliper();
void pumpCaliper();
float readCaliperBufferedMedian();
float readCaliperAverage(int samples = 3);
float readCaliperMedian(int samples = 5);
float readCaliperDisplay();
''',''),
('''  calRollingCount = 0;
  calRollingIdx   = 0;
''',''),
('  newPoint->diameter = roundf(diameter * 100.0f) / 100.0f;  // clamp to caliper precision: 0.01 mm',
 '  newPoint->diameter = roundf(diameter * 100.0f) / 100.0f;  // 0.01 mm: stesso formato di prima verso l\'app WPF'),
('        float finalCm = (float)getEncoderValue() / getActivePpc() - 2.0f;','        float finalCm = (float)getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM;'),
('        int currentCm = (int)(getEncoderValue() / getActivePpc()) - 2;','        int currentCm = (int)floorf(getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM);'),
('      float finalCm = (float)getEncoderValue() / getActivePpc() - 2.0f;','      float finalCm = (float)getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM;'),
('  float currentCm = (float)getEncoderValue() / getActivePpc() - 2.0f;  // encoder-based actual position','  float currentCm = (float)getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM;  // encoder-based actual position'),
('  // Send GOTOPOS to slave. Add the +2 cm encoder offset (encoder wheel is 20 mm behind caliper).','  // Send GOTOPOS to slave. Add the encoder offset (encoder wheel is MEAS_OFFSET_CM behind the measuring point).'),
('String(targetEncoderCm + 2.0f, 2)','String(targetEncoderCm + MEAS_OFFSET_CM, 2)'),
('''  pinMode(CALIPER_CLOCK_PIN, INPUT);
  pinMode(CALIPER_DATA_PIN, INPUT);
''',''),
('''  attachInterrupt(digitalPinToInterrupt(CALIPER_CLOCK_PIN), onCaliperChange, CHANGE);
''','''  gaugeSetup();  // RazorGauge: pin, ADC, NVS, task di acquisizione su core 0
'''),
('setEncoderValue((long)ceilf(2.0f * getActivePpc()));','setEncoderValue((long)ceilf(MEAS_OFFSET_CM * getActivePpc()));'),
('    float cm  = (float)enc / getActivePpc() - 2.0f;','    float cm  = (float)enc / getActivePpc() - MEAS_OFFSET_CM;'),
('''  server.on("/export", HTTP_GET''','''  // UI web rimossa (sostituita dall'app WPF). Restano solo gli endpoint dati /export e /encoder,
  // che non fanno parte dell'interfaccia ma potrebbero essere usati da strumenti esterni.
  server.on("/export", HTTP_GET'''),
('''      String cmd = String((char*)payload);
      if (cmd == "getparams") {''','''      String cmd = String((char*)payload);
      gCmdClient = num;  // per le risposte dei comandi gauge_* (solo a chi li invia)
      if (cmd == "getparams") {'''),
('''        handleCommand(cmd);
      }
    } else if (type == WStype_CONNECTED) {''','''        handleCommand(cmd);
      }
      gCmdClient = -1;
    } else if (type == WStype_CONNECTED) {'''),
('''  Serial.println("Sistema pronto - CALIBRO FISSO");
  Serial.println("cm,diametro_compensato,display_calibro");''','''  Serial.println("Sistema pronto - RazorGauge (misura ottica a ombra)");
  Serial.println("cm,diametro_compensato,display_gauge");'''),
('  pumpCaliper();       // keep rolling buffer fresh — non-blocking, must run every iteration','  gaugePollRequest();  // consegna i risultati dei comandi gauge_* (l\'acquisizione gira nel suo task)'),
('  int currentCm = (int)(encSnap / getActivePpc()) - 2;','  int currentCm = (int)floorf(encSnap / getActivePpc() - MEAS_OFFSET_CM);'),
('    float displayValue = readCaliperBufferedMedian();','    float displayValue = gaugeReadDisplay();   // mediana del buffer RazorGauge, calibrata; NAN = nessun cavo'),
('    float floatCm = (float)encSnap / getActivePpc() - 2.0f;','    float floatCm = (float)encSnap / getActivePpc() - MEAS_OFFSET_CM;'),
('    float cm = (float)enc / getActivePpc() - 2.0f;','    float cm = (float)enc / getActivePpc() - MEAS_OFFSET_CM;'),
('''    // Set encoder so caliper position reads 0: display = encoder/activePpc - 2 = 0
    // → encoder must be ceil(2 * activePpc) so integer division gives exactly 2''','''    // Set encoder so the measuring-point position reads 0: encoder/activePpc - MEAS_OFFSET_CM = 0'''),
('''void handleCommand(String cmd) {
''','''void handleCommand(String cmd) {
  if (gaugeHandleCommand(cmd)) return;   // comandi gauge_* (RazorGauge)

'''),
('''    Serial.println("  setdisplayzero      - Imposta display corrente come zero");
    Serial.println("  readraw             - Mostra lettura grezza del calibro");''','''    Serial.println("  setdisplayzero      - (RazorGauge) non necessario: azzera lo zero display a 0");
    Serial.println("  readraw             - Mostra la lettura attuale di RazorGauge");'''),
('''    Serial.println("  motor scan|stop|fast_s|fast_o|status");''','''    Serial.println("  motor scan|stop|fast_s|fast_o|status");
    Serial.println("  gauge_dark | gauge_ref | gauge_cal <mm> | gauge_calreset | gauge_exp <us> | gauge_status | gauge_profile");'''),
('''  if (cmd == "readraw") {
    float display = readCaliperDisplay();
    Serial.print("Display calibro: ");
    Serial.println(display, 2);
    return;
  }''','''  if (cmd == "readraw") {
    float display = gaugeReadDisplay();
    Serial.print("Display RazorGauge: ");
    if (isfinite(display)) Serial.println(display, 4); else Serial.println("nessun cavo / sensore non pronto");
    return;
  }'''),
('''void setDisplayZero() {
  displayZeroValue = readCaliperDisplay();
  Serial.print("Zero display impostato a: ");''','''void setDisplayZero() {
  // Con il calibro serviva a registrare la lettura a ganasce chiuse. Con RazorGauge lo zero è
  // intrinseco (nessuna ombra = 0 mm): il comando resta accettato per compatibilità con l'app
  // WPF e riporta lo zero display a 0. Le correzioni fini si fanno con gauge_cal / setoffset.
  displayZeroValue = 0.0f;
  Serial.print("Zero display (RazorGauge) impostato a: ");'''),
]
for a,b in rep:
    assert src.count(a)>=1, 'MISSING: '+a[:70]
    src=src.replace(a,b)
open('master.ino','w').write(src)
for pat in ['caliper','Caliper','CALIPER','2.0f','calRolling','readCaliper','- 2']:
    for i,l in enumerate(src.split('\n'),1):
        if pat in l: print(pat, i, l.strip()[:120])
print(len(src.split('\n')),'lines')
