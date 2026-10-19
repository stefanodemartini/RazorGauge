/*
  RazorGauge - firmware di banco per ESP32 (classico, WROOM/DevKit)
  Misuratore diametro cavo a ombra laser
  Hiwonder CCD Module TSL1401 V1.0 (obiettivo, supporto e LED rimossi) + ESP32 classico
  Arduino core ESP32 2.x / 3.x — stessi pin del master, la scheda si può provare così e poi flashare col master

  COLLEGAMENTI
    Modulo VCC -> 3V3     (così AO non supera il range dell'ADC)
    Modulo GND -> GND
    Modulo SI  -> GPIO26
    Modulo CLK -> GPIO27
    Modulo AO  -> GPIO34  (ADC1_CH6, solo ingresso — non usare pin ADC2, in conflitto col WiFi)
    Laser      -> GPIO25 tramite NPN/MOSFET (il laser viene pulsato = controllo esposizione)
    NB: sull'ESP32 classico i GPIO 6-11 sono collegati alla flash: non usarli mai.

  PRINCIPIO
    - Il laser è acceso solo per EXPOSURE_US durante l'integrazione -> tempo di posa in µs.
    - Frame dark (laser spento) + frame ref (laser acceso, senza cavo) -> normalizzazione pixel per pixel.
    - Diametro = AREA dell'ombra: D = pitch * Σ(1 - norm) su una finestra attorno all'ombra.
      Con pixel da 63.5 µm e frange di Fresnel da ~40 µm, il metodo "a soglia" ha un errore
      sistematico di ~37 µm che cambia con la posizione del cavo; il metodo ad area è privo
      di bias e indipendente dalla posizione (verificato in simulazione Fresnel).

  COMANDI SERIALI (115200, terminatore newline)
    d          acquisisce dark (laser spento)
    r          acquisisce riferimento SENZA cavo, con auto-esposizione
    m          misura singola
    M          misura continua on/off
    p          dump del profilo normalizzato (per Serial Plotter)
    w          dump raw (per diagnosticare saturazione)
    e <us>     imposta esposizione manuale
    c <mm>     aggiunge punto di calibrazione con spina/cavo di diametro noto
    x          cancella calibrazione
    ?          aiuto
*/

#include <Arduino.h>
#include <Preferences.h>

// ---------------- Configurazione ----------------
const int PIN_SI    = 26;
const int PIN_CLK   = 27;
const int PIN_AO    = 34;
const int PIN_LASER = 25;

const int   NPIX       = 128;
const float PIXEL_MM   = 0.0635f;   // passo pixel TSL1401
const int   N_AVG      = 16;        // frame mediati per misura (rumore ∝ 1/√N)
const int   MARGIN_PX  = 8;         // pixel oltre i bordi inclusi nell'area (copre le frange)
const float EDGE_FIND  = 0.5f;      // soglia usata SOLO per localizzare l'ombra
const float SHADOW_MIN = 0.3f;      // se il minimo normalizzato è sopra, non c'è cavo
const int   ADC_TARGET_LO = 2600;   // auto-esposizione: picco (ref-dark) desiderato
const int   ADC_TARGET_HI = 3300;
const int   ADC_SAT       = 3900;
const uint32_t EXP_MIN_US = 2;
const uint32_t EXP_MAX_US = 20000;

// ---------------- Stato ----------------
uint16_t rawBuf[NPIX];
float dark[NPIX], ref[NPIX], acc[NPIX], norm_[NPIX];
bool haveDark = false, haveRef = false, continuous = false;
uint32_t exposureUs = 20;

// calibrazione: mm = calA * mm_misurati + calB
float calA = 1.0f, calB = 0.0f;
const int MAX_CAL = 10;
float calMeas[MAX_CAL], calTrue[MAX_CAL];
int nCal = 0;

Preferences prefs;

// ---------------- Sensore ----------------
// Un ciclo completo SI + 129 clock. Durante la lettura si leggono i 128 pixel
// integrati dal ciclo precedente; la nuova integrazione parte al 18° clock.
void readFrame(uint16_t *buf) {
  digitalWrite(PIN_SI, HIGH);
  digitalWrite(PIN_CLK, HIGH);
  digitalWrite(PIN_SI, LOW);
  for (int i = 0; i < NPIX; i++) {
    delayMicroseconds(1);                 // assestamento uscita AO
    buf[i] = analogRead(PIN_AO);
    digitalWrite(PIN_CLK, LOW);
    digitalWrite(PIN_CLK, HIGH);
  }
  digitalWrite(PIN_CLK, LOW);             // 129° clock chiude il ciclo
  delayMicroseconds(20);                  // t_qt: trasferimento carica prima del prossimo SI
}

// Frame con laser pulsato: flush -> impulso laser -> lettura
void captureFrame(bool laser, uint16_t *buf) {
  readFrame(buf);                         // scarica il frame precedente, avvia integrazione
  if (laser) {
    digitalWrite(PIN_LASER, HIGH);
    delayMicroseconds(exposureUs);
    digitalWrite(PIN_LASER, LOW);
  }
  readFrame(buf);                         // contiene la carica dell'impulso
}

void averageFrames(bool laser, float *out, int n) {
  for (int i = 0; i < NPIX; i++) out[i] = 0;
  for (int k = 0; k < n; k++) {
    captureFrame(laser, rawBuf);
    for (int i = 0; i < NPIX; i++) out[i] += rawBuf[i];
  }
  for (int i = 0; i < NPIX; i++) out[i] /= n;
}

// ---------------- Dark / Riferimento ----------------
void takeDark() {
  averageFrames(false, dark, 32);
  haveDark = true;
  float mx = 0; for (int i = 0; i < NPIX; i++) mx = max(mx, dark[i]);
  Serial.printf("Dark acquisito. Max dark = %.0f LSB\n", mx);
  if (mx > 500) Serial.println("ATTENZIONE: luce ambiente alta -> schermare o aggiungere passabanda 650 nm");
}

float peakSignal(const float *frame) {
  float mx = 0;
  for (int i = 2; i < NPIX - 2; i++) mx = max(mx, frame[i] - dark[i]);
  return mx;
}

void takeReference() {
  if (!haveDark) takeDark();
  Serial.println("Riferimento: togli il cavo. Auto-esposizione...");
  for (int it = 0; it < 25; it++) {
    averageFrames(true, ref, 4);
    float pk = peakSignal(ref);
    float rawMax = 0; for (int i = 0; i < NPIX; i++) rawMax = max(rawMax, ref[i]);
    if (rawMax >= ADC_SAT || pk > ADC_TARGET_HI) {
      if (exposureUs <= EXP_MIN_US) {
        Serial.println("SATURO anche all'esposizione minima -> aumentare il filtro ND");
        break;
      }
      exposureUs = max(EXP_MIN_US, (uint32_t)(exposureUs * 0.6f));
    } else if (pk < ADC_TARGET_LO) {
      if (exposureUs >= EXP_MAX_US) {
        Serial.println("Segnale basso anche all'esposizione massima -> ridurre il filtro ND");
        break;
      }
      exposureUs = min(EXP_MAX_US, (uint32_t)(exposureUs * 1.4f) + 1);
    } else break;
  }
  averageFrames(true, ref, 32);
  haveRef = true;
  prefs.putUInt("exp", exposureUs);
  float pk = peakSignal(ref), mn = 1e9;
  for (int i = 2; i < NPIX - 2; i++) mn = min(mn, ref[i] - dark[i]);
  Serial.printf("Riferimento OK. Esposizione %u us, picco %.0f, minimo %.0f LSB (uniformita %.0f%%)\n",
                exposureUs, pk, mn, 100.0f * mn / pk);
  if (mn < 0.3f * pk) Serial.println("ATTENZIONE: bordi del sensore poco illuminati (vignettatura/allineamento)");
}

// ---------------- Misura ----------------
// Ritorna false se non c'è cavo o l'ombra esce dal campo
bool measureRaw(float &diamMm, float &centerMm) {
  if (!haveDark || !haveRef) { Serial.println("Esegui prima 'd' e 'r'"); return false; }
  averageFrames(true, acc, N_AVG);

  for (int i = 0; i < NPIX; i++) {
    float span = ref[i] - dark[i];
    norm_[i] = (span > 50) ? (acc[i] - dark[i]) / span : 1.0f;
  }

  int imin = 2;
  for (int i = 2; i < NPIX - 2; i++) if (norm_[i] < norm_[imin]) imin = i;
  if (norm_[imin] > SHADOW_MIN) return false;                 // nessun cavo

  int l = imin; while (l > 0 && norm_[l] < EDGE_FIND) l--;
  int r = imin; while (r < NPIX - 1 && norm_[r] < EDGE_FIND) r++;
  int L = l - MARGIN_PX, R = r + MARGIN_PX;
  if (L < 0 || R > NPIX - 1) {
    Serial.println("Ombra troppo vicina al bordo del sensore -> centrare il cavo");
    return false;
  }

  // Correzione energia impulso: jitter di delayMicroseconds e deriva del laser
  // cambiano l'intensità di tutto il frame. I pixel illuminati fuori finestra
  // devono valere 1 -> si ricava il fattore k e si ri-normalizza.
  // Senza questa correzione ±3% di energia = ±30 µm di errore.
  float sumK = 0; int nK = 0;
  for (int i = 2; i < NPIX - 2; i++) if (i < L || i > R) { sumK += norm_[i]; nK++; }
  if (nK >= 10) {
    float k = sumK / nK;
    if (k > 0.5f && k < 1.5f) for (int i = L; i <= R; i++) norm_[i] /= k;
  }

  float area = 0, moment = 0;
  for (int i = L; i <= R; i++) {
    float d = 1.0f - norm_[i];
    area += d;
    moment += d * i;
  }
  diamMm   = area * PIXEL_MM;
  centerMm = (moment / area - (NPIX - 1) / 2.0f) * PIXEL_MM;   // 0 = centro sensore
  return true;
}

bool measure(float &diamMm, float &centerMm) {
  float raw;
  if (!measureRaw(raw, centerMm)) return false;
  diamMm = calA * raw + calB;
  return true;
}

// ---------------- Calibrazione ----------------
void fitCalibration() {
  if (nCal == 0) { calA = 1; calB = 0; }
  else if (nCal == 1) { calA = 1; calB = calTrue[0] - calMeas[0]; }
  else {
    float sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (int i = 0; i < nCal; i++) {
      sx += calMeas[i]; sy += calTrue[i];
      sxx += calMeas[i] * calMeas[i]; sxy += calMeas[i] * calTrue[i];
    }
    float den = nCal * sxx - sx * sx;
    if (fabsf(den) < 1e-9f) { calA = 1; calB = (sy - sx) / nCal; }
    else { calA = (nCal * sxy - sx * sy) / den; calB = (sy - calA * sx) / nCal; }
  }
  prefs.putFloat("calA", calA);
  prefs.putFloat("calB", calB);
  prefs.putInt("nCal", nCal);
  prefs.putBytes("calM", calMeas, sizeof(calMeas));
  prefs.putBytes("calT", calTrue, sizeof(calTrue));
  Serial.printf("Calibrazione: mm = %.6f * misura + %.4f  (%d punti)\n", calA, calB, nCal);
  for (int i = 0; i < nCal; i++)
    Serial.printf("  %.4f -> %.4f  residuo %+.1f um\n", calMeas[i], calTrue[i],
                  1000 * (calA * calMeas[i] + calB - calTrue[i]));
}

void addCalPoint(float trueMm) {
  if (nCal >= MAX_CAL) { Serial.println("Max punti raggiunto, usa 'x'"); return; }
  float sum = 0, raw, c; int ok = 0;
  for (int k = 0; k < 8; k++) if (measureRaw(raw, c)) { sum += raw; ok++; }
  if (ok < 6) { Serial.println("Misura non valida"); return; }
  calMeas[nCal] = sum / ok; calTrue[nCal] = trueMm; nCal++;
  fitCalibration();
}

// ---------------- Utility ----------------
void dumpNorm() {
  if (!haveDark || !haveRef) { Serial.println("Esegui prima 'd' e 'r'"); return; }
  averageFrames(true, acc, 4);
  for (int i = 0; i < NPIX; i++) {
    float span = ref[i] - dark[i];
    Serial.println(span > 50 ? (acc[i] - dark[i]) / span : 1.0f, 4);
  }
}

void dumpRaw() {
  captureFrame(true, rawBuf);
  for (int i = 0; i < NPIX; i++) Serial.println(rawBuf[i]);
}

void help() {
  Serial.println("d=dark  r=riferimento(no cavo)  m=misura  M=continua  p=profilo  w=raw");
  Serial.println("e <us>=esposizione  c <mm>=punto calibrazione  x=cancella cal  ?=aiuto");
}

void handleCommand(String s) {
  s.trim();
  if (s.length() == 0) return;
  char cmd = s.charAt(0);
  String arg = s.substring(1); arg.trim();
  float d, c;
  switch (cmd) {
    case 'd': takeDark(); break;
    case 'r': takeReference(); break;
    case 'm':
      if (measure(d, c)) Serial.printf("D = %.4f mm   pos = %+.3f mm\n", d, c);
      else Serial.println("Nessun cavo / misura non valida");
      break;
    case 'M': continuous = !continuous; Serial.println(continuous ? "Continua ON" : "Continua OFF"); break;
    case 'p': dumpNorm(); break;
    case 'w': dumpRaw(); break;
    case 'e': exposureUs = constrain((uint32_t)arg.toInt(), EXP_MIN_US, EXP_MAX_US);
              Serial.printf("Esposizione %u us (rifai 'r')\n", exposureUs); break;
    case 'c': addCalPoint(arg.toFloat()); break;
    case 'x': nCal = 0; fitCalibration(); break;
    default: help();
  }
}

// ---------------- Setup / Loop ----------------
void setup() {
  Serial.begin(115200);
  pinMode(PIN_SI, OUTPUT);
  pinMode(PIN_CLK, OUTPUT);
  pinMode(PIN_LASER, OUTPUT);
  digitalWrite(PIN_SI, LOW);
  digitalWrite(PIN_CLK, LOW);
  digitalWrite(PIN_LASER, LOW);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_AO, ADC_11db);   // ~0–3.1 V

  prefs.begin("gauge", false);
  exposureUs = prefs.getUInt("exp", 20);
  calA = prefs.getFloat("calA", 1.0f);
  calB = prefs.getFloat("calB", 0.0f);
  nCal = prefs.getInt("nCal", 0);
  if (nCal > 0) {
    prefs.getBytes("calM", calMeas, sizeof(calMeas));
    prefs.getBytes("calT", calTrue, sizeof(calTrue));
  }

  for (int i = 0; i < 3; i++) readFrame(rawBuf);   // pulizia iniziale del sensore
  delay(500);
  Serial.println("\nRazorGauge - TSL1401 + ESP32 (banco)");
  Serial.printf("Esposizione salvata %u us, calibrazione %d punti\n", exposureUs, nCal);
  help();
}

void loop() {
  static String line;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') { handleCommand(line); line = ""; }
    else line += ch;
  }

  if (continuous) {
    // mediana di 5 misure per scartare i picchi (vibrazioni, polvere)
    float v[5], c = 0; int n = 0;
    for (int k = 0; k < 5; k++) { float d; if (measure(d, c)) v[n++] = d; }
    if (n >= 3) {
      for (int i = 1; i < n; i++) for (int j = i; j > 0 && v[j] < v[j-1]; j--) { float t = v[j]; v[j] = v[j-1]; v[j-1] = t; }
      Serial.printf("D = %.4f mm   pos = %+.3f mm\n", v[n / 2], c);
    } else {
      Serial.println("---");
    }
  }
}
