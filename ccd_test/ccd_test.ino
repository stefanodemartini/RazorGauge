/*
  RazorGauge - prova del solo sensore CCD (senza laser)
  Hiwonder CCD Module TSL1401 V1.0 + ESP32 classico (DevKit V1 30p)
  Serve a verificare che il modulo risponda prima di montarlo nella torre.
  Stessi pin di gauge_esp32 e del master: il cablaggio resta valido dopo.

  COLLEGAMENTI
    Modulo VCC -> 3V3     (NON 5V: AO supererebbe il range dell'ADC)
    Modulo GND -> GND
    Modulo SI  -> GPIO26
    Modulo CLK -> GPIO27
    Modulo AO  -> GPIO34
    GPIO25 (laser) non serve qui.

  Il tempo d'integrazione si regola da software: con la luce della stanza
  servono millisecondi, non i µs dell'impulso laser.

  COMANDI SERIALI (115200, terminatore newline)
    g          profilo ASCII continuo on/off (5 frame/s)
    s          un frame: profilo ASCII + statistiche
    w          dump dei 128 valori raw (per Serial Plotter)
    t <us>     tempo d'integrazione (200 .. 200000 us)
    a          test automatico: linearità segnale/tempo e uniformità
    ?          aiuto
*/

#include <Arduino.h>

const int PIN_SI  = 26;
const int PIN_CLK = 27;
const int PIN_AO  = 34;

const int NPIX = 128;
const int ADC_SAT = 4000;

uint16_t buf[NPIX];
uint32_t integUs = 5000;
uint32_t tIntStart = 0, tIntEnd = 0;   // integrazione effettiva misurata
bool continuous = false;

// Un ciclo SI + 129 clock: legge i 128 pixel integrati dal ciclo precedente.
// La nuova integrazione parte al 18° clock e finisce col prossimo SI.
void readFrame(uint16_t *b) {
  tIntEnd = micros();
  digitalWrite(PIN_SI, HIGH);
  digitalWrite(PIN_CLK, HIGH);
  digitalWrite(PIN_SI, LOW);
  for (int i = 0; i < NPIX; i++) {
    delayMicroseconds(1);
    b[i] = analogRead(PIN_AO);
    digitalWrite(PIN_CLK, LOW);
    digitalWrite(PIN_CLK, HIGH);
    if (i == 17) tIntStart = micros();
  }
  digitalWrite(PIN_CLK, LOW);
  delayMicroseconds(20);
}

// Scarica il sensore, aspetta, legge: ritorna l'integrazione effettiva in µs
uint32_t capture(uint16_t *b, uint32_t us) {
  readFrame(b);
  uint32_t start = tIntStart;              // il secondo readFrame lo sovrascrive
  uint32_t t0 = micros();
  while (micros() - t0 < us) {}
  readFrame(b);
  return tIntEnd - start;
}

struct Stats { int mn, mx, imn, imx; float mean; int nSat; };
Stats stats(const uint16_t *b);   // prototipo esplicito: quello generato da Arduino finirebbe prima della struct

Stats stats(const uint16_t *b) {
  Stats s = {4096, -1, 0, 0, 0, 0};
  for (int i = 0; i < NPIX; i++) {
    if (b[i] < s.mn) { s.mn = b[i]; s.imn = i; }
    if (b[i] > s.mx) { s.mx = b[i]; s.imx = i; }
    if (b[i] >= ADC_SAT) s.nSat++;
    s.mean += b[i];
  }
  s.mean /= NPIX;
  return s;
}

// 64 caratteri, 2 pixel ciascuno, scala assoluta 0..4095
void asciiProfile(const uint16_t *b) {
  static const char lv[] = " .:-=+*#%@";
  char line[NPIX / 2 + 3];
  line[0] = '|';
  for (int i = 0; i < NPIX / 2; i++) {
    int v = (b[2 * i] + b[2 * i + 1]) / 2;
    line[i + 1] = lv[constrain(v * 10 / 4096, 0, 9)];
  }
  line[NPIX / 2 + 1] = '|';
  line[NPIX / 2 + 2] = 0;
  Serial.print(line);
}

void showFrame() {
  uint32_t eff = capture(buf, integUs);
  Stats s = stats(buf);
  asciiProfile(buf);
  Serial.printf("  min %4d@%3d  max %4d@%3d  media %6.1f  int %lu us%s\n",
                s.mn, s.imn, s.mx, s.imx, s.mean, (unsigned long)eff,
                s.nSat ? "  SATURO" : "");
}

void dumpRaw() {
  capture(buf, integUs);
  for (int i = 0; i < NPIX; i++) Serial.println(buf[i]);
}

// Il segnale deve crescere col tempo d'integrazione (circa lineare finché non satura).
// Un sensore morto o un AO scollegato dà una media piatta.
void autoTest() {
  Serial.println("Test: tieni il sensore sotto luce costante, senza muoverlo.");
  delay(1000);
  const uint32_t T[] = {500, 1000, 2000, 5000, 10000, 20000, 50000};
  float prev = -1;
  bool monotone = true;
  for (uint32_t t : T) {
    float acc = 0; uint32_t eff = 0;
    for (int k = 0; k < 4; k++) { eff = capture(buf, t); acc += stats(buf).mean; }
    acc /= 4;
    Stats s = stats(buf);
    Serial.printf("  int %6lu us  media %6.1f  min %4d  max %4d%s\n",
                  (unsigned long)eff, acc, s.mn, s.mx, s.nSat ? "  (saturo)" : "");
    if (prev >= 0 && acc < prev - 20 && !s.nSat) monotone = false;
    prev = acc;
  }
  Serial.println(monotone ? "Segnale crescente col tempo: OK"
                          : "ATTENZIONE: il segnale non cresce col tempo -> controlla SI/CLK/AO");

  capture(buf, integUs);
  Stats s = stats(buf);
  if (s.mx - s.mn < 30)
    Serial.println("ATTENZIONE: profilo piatto. Coprine metà con un cartoncino e ripeti 's'.");
  if (s.mx < 100)
    Serial.println("ATTENZIONE: segnale quasi nullo -> più luce, più integrazione, o AO non collegato");
}

void help() {
  Serial.println("g=profilo continuo  s=un frame  w=raw per plotter  t <us>=integrazione  a=test  ?=aiuto");
  Serial.printf("Integrazione attuale %lu us\n", (unsigned long)integUs);
}

void handleCommand(String s) {
  s.trim();
  if (s.length() == 0) return;
  char cmd = s.charAt(0);
  String arg = s.substring(1); arg.trim();
  switch (cmd) {
    case 'g': continuous = !continuous; break;
    case 's': showFrame(); break;
    case 'w': dumpRaw(); break;
    case 't': integUs = constrain((uint32_t)arg.toInt(), 200UL, 200000UL);
              Serial.printf("Integrazione %lu us\n", (unsigned long)integUs); break;
    case 'a': continuous = false; autoTest(); break;
    default: help();
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_SI, OUTPUT);
  pinMode(PIN_CLK, OUTPUT);
  digitalWrite(PIN_SI, LOW);
  digitalWrite(PIN_CLK, LOW);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_AO, ADC_11db);   // ~0–3.1 V

  for (int i = 0; i < 3; i++) readFrame(buf);  // pulizia iniziale
  delay(500);
  Serial.println("\nRazorGauge - prova sensore TSL1401 (senza laser)");
  help();
}

void loop() {
  static String line;
  static uint32_t lastCharMs = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    lastCharMs = millis();
    if (ch == '\n' || ch == '\r') { handleCommand(line); line = ""; }
    else line += ch;
  }
  // Anche senza terminatore (Serial Monitor su "No Line Ending"): esegue dopo 100 ms di silenzio
  if (line.length() && millis() - lastCharMs > 100) { handleCommand(line); line = ""; }
  if (continuous) { showFrame(); delay(200); }
}
