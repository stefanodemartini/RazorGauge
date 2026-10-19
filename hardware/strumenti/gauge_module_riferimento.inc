// =====================================================================
// RazorGauge — sensore ottico a ombra (sostituisce il calibro centesimale)
// ---------------------------------------------------------------------
// Laser collimato + TSL1401 (128 px, 63.5 µm). Diametro = AREA dell'ombra
// (passo × Σ(1 − I_norm)), con ri-normalizzazione per frame sull'energia
// dell'impulso. L'acquisizione gira in un task FreeRTOS dedicato (core 0):
// il loop() non viene mai bloccato e legge un buffer mediano, esattamente
// come faceva con il calibro (readCaliperBufferedMedian).
//
// Comandi (Serial o WebSocket, stessi di handleCommand):
//   gauge_dark        acquisisce il frame al buio (laser spento)
//   gauge_ref         riferimento SENZA cavo, con auto-esposizione
//   gauge_cal <mm>    aggiunge un punto di calibrazione (spina di diametro noto)
//   gauge_calreset    cancella la calibrazione
//   gauge_exp <us>    esposizione manuale (poi rifare gauge_ref)
//   gauge_status      stato del sensore
//   gauge_profile     stampa su Serial il profilo normalizzato (Serial Plotter)
// Dark, riferimento, esposizione e calibrazione sono salvati in NVS e
// ricaricati all'avvio: gauge_dark + gauge_ref vanno rifatti solo dopo
// interventi meccanici/ottici.
// =====================================================================

static const int      G_NPIX       = 128;
static const float    G_PIXEL_MM   = 0.0635f;
static const int      G_MARGIN_PX  = 8;        // pixel oltre i bordi inclusi nell'area (frange)
static const float    G_EDGE_FIND  = 0.5f;     // soglia usata SOLO per localizzare l'ombra
static const float    G_SHADOW_MIN = 0.3f;     // minimo normalizzato sopra cui "nessun cavo"
static const int      G_ADC_LO = 2600, G_ADC_HI = 3300, G_ADC_SAT = 3900;
static const uint32_t G_EXP_MIN = 2, G_EXP_MAX = 20000;
static const int      G_MAX_CAL = 10;
#define GAUGE_FRAMES_PER_MEAS 8                 // frame mediati per ogni misura del task (~35 ms)
#define GAUGE_BUF_SIZE        7                 // misure nel buffer mediano (come CAL_BUF_SIZE)

static uint16_t gRaw[G_NPIX];
static float    gDark[G_NPIX], gRef[G_NPIX], gAcc[G_NPIX], gNorm[G_NPIX];
static bool     gHaveDark = false, gHaveRef = false;
static uint32_t gExposureUs = 20;
static float    gCalA = 1.0f, gCalB = 0.0f;
static float    gCalMeas[G_MAX_CAL], gCalTrue[G_MAX_CAL];
static int      gNCal = 0;
static Preferences gPrefs;

// --- dati condivisi task <-> loop ---
static portMUX_TYPE gMux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE gPulseMux = portMUX_INITIALIZER_UNLOCKED;   // solo per l'impulso laser
static float    gBuf[GAUGE_BUF_SIZE];
static int      gBufCount = 0, gBufIdx = 0;
static volatile float    gLastRawMm = 0.0f, gLastPosMm = 0.0f;
static volatile bool     gLastValid = false;
static volatile uint32_t gMeasCount = 0;

enum { GREQ_NONE = 0, GREQ_DARK, GREQ_REF, GREQ_CAL, GREQ_PROFILE };
static volatile int   gReq = GREQ_NONE;
static volatile float gReqArg = 0.0f;
static volatile bool  gReqDone = false;
static char           gReqMsg[320];
static int            gReqClient = -1;   // client WebSocket che ha chiesto (-1 = Serial)
static int            gCmdClient = -1;   // client dell'ultimo comando ricevuto

// ---------------------------------------------------------------- sensore
static void gReadFrame(uint16_t* buf) {
  digitalWrite(GAUGE_SI_PIN, HIGH);
  digitalWrite(GAUGE_CLK_PIN, HIGH);
  digitalWrite(GAUGE_SI_PIN, LOW);
  for (int i = 0; i < G_NPIX; i++) {
    delayMicroseconds(1);
    buf[i] = analogRead(GAUGE_AO_PIN);
    digitalWrite(GAUGE_CLK_PIN, LOW);
    digitalWrite(GAUGE_CLK_PIN, HIGH);
  }
  digitalWrite(GAUGE_CLK_PIN, LOW);   // 129° clock
  delayMicroseconds(20);              // t_qt prima del prossimo SI
}

static void gCapture(bool laser, uint16_t* buf) {
  gReadFrame(buf);                    // scarica il frame precedente, avvia l'integrazione
  if (laser) {
    if (gExposureUs <= 500) {         // impulso breve: niente interruzioni durante la posa
      portENTER_CRITICAL(&gPulseMux);
      digitalWrite(GAUGE_LASER_PIN, HIGH);
      delayMicroseconds(gExposureUs);
      digitalWrite(GAUGE_LASER_PIN, LOW);
      portEXIT_CRITICAL(&gPulseMux);
    } else {
      digitalWrite(GAUGE_LASER_PIN, HIGH);
      delayMicroseconds(gExposureUs);
      digitalWrite(GAUGE_LASER_PIN, LOW);
    }
  }
  gReadFrame(buf);
}

static void gAverage(bool laser, float* out, int n) {
  for (int i = 0; i < G_NPIX; i++) out[i] = 0;
  for (int k = 0; k < n; k++) {
    gCapture(laser, gRaw);
    for (int i = 0; i < G_NPIX; i++) out[i] += gRaw[i];
    vTaskDelay(1);                    // lascia respirare IDLE0 / WiFi (task watchdog)
  }
  for (int i = 0; i < G_NPIX; i++) out[i] /= n;
}

static float gPeak(const float* f) {
  float mx = 0;
  for (int i = 2; i < G_NPIX - 2; i++) mx = max(mx, f[i] - gDark[i]);
  return mx;
}

// Misura grezza (non calibrata), mm. false = nessun cavo / ombra fuori campo.
static bool gaugeMeasureRaw(int nAvg, float& diamMm, float& centerMm) {
  if (!gHaveDark || !gHaveRef) return false;
  gAverage(true, gAcc, nAvg);
  for (int i = 0; i < G_NPIX; i++) {
    float span = gRef[i] - gDark[i];
    gNorm[i] = (span > 50) ? (gAcc[i] - gDark[i]) / span : 1.0f;
  }
  int imin = 2;
  for (int i = 2; i < G_NPIX - 2; i++) if (gNorm[i] < gNorm[imin]) imin = i;
  if (gNorm[imin] > G_SHADOW_MIN) return false;
  int l = imin; while (l > 0 && gNorm[l] < G_EDGE_FIND) l--;
  int r = imin; while (r < G_NPIX - 1 && gNorm[r] < G_EDGE_FIND) r++;
  int L = l - G_MARGIN_PX, R = r + G_MARGIN_PX;
  if (L < 0 || R > G_NPIX - 1) return false;
  // correzione energia impulso: i pixel illuminati fuori finestra devono valere 1
  float sumK = 0; int nK = 0;
  for (int i = 2; i < G_NPIX - 2; i++) if (i < L || i > R) { sumK += gNorm[i]; nK++; }
  if (nK >= 10) {
    float k = sumK / nK;
    if (k > 0.5f && k < 1.5f) for (int i = L; i <= R; i++) gNorm[i] /= k;
  }
  float area = 0, moment = 0;
  for (int i = L; i <= R; i++) { float d = 1.0f - gNorm[i]; area += d; moment += d * i; }
  if (area <= 0) return false;
  diamMm   = area * G_PIXEL_MM;
  centerMm = (moment / area - (G_NPIX - 1) / 2.0f) * G_PIXEL_MM;
  return true;
}

// ---------------------------------------------------------------- NVS
static void gSaveRefs() {
  uint16_t tmp[G_NPIX];
  for (int i = 0; i < G_NPIX; i++) tmp[i] = (uint16_t)constrain(lroundf(gDark[i]), 0L, 65535L);
  gPrefs.putBytes("dark", tmp, sizeof(tmp));
  for (int i = 0; i < G_NPIX; i++) tmp[i] = (uint16_t)constrain(lroundf(gRef[i]), 0L, 65535L);
  gPrefs.putBytes("ref", tmp, sizeof(tmp));
  gPrefs.putUInt("exp", gExposureUs);
  gPrefs.putBool("hasDark", gHaveDark);
  gPrefs.putBool("hasRef", gHaveRef);
}

static void gSaveCal() {
  gPrefs.putFloat("calA", gCalA);
  gPrefs.putFloat("calB", gCalB);
  gPrefs.putInt("nCal", gNCal);
  gPrefs.putBytes("calM", gCalMeas, sizeof(gCalMeas));
  gPrefs.putBytes("calT", gCalTrue, sizeof(gCalTrue));
}

static void gLoadAll() {
  uint16_t tmp[G_NPIX];
  gExposureUs = gPrefs.getUInt("exp", 20);
  if (gPrefs.getBool("hasDark", false) && gPrefs.getBytes("dark", tmp, sizeof(tmp)) == sizeof(tmp)) {
    for (int i = 0; i < G_NPIX; i++) gDark[i] = tmp[i];
    gHaveDark = true;
  }
  if (gPrefs.getBool("hasRef", false) && gPrefs.getBytes("ref", tmp, sizeof(tmp)) == sizeof(tmp)) {
    for (int i = 0; i < G_NPIX; i++) gRef[i] = tmp[i];
    gHaveRef = true;
  }
  gCalA = gPrefs.getFloat("calA", 1.0f);
  gCalB = gPrefs.getFloat("calB", 0.0f);
  gNCal = gPrefs.getInt("nCal", 0);
  if (gNCal < 0 || gNCal > G_MAX_CAL) gNCal = 0;
  if (gNCal > 0) {
    gPrefs.getBytes("calM", gCalMeas, sizeof(gCalMeas));
    gPrefs.getBytes("calT", gCalTrue, sizeof(gCalTrue));
  }
}

static void gFitCal() {
  if (gNCal == 0) { gCalA = 1; gCalB = 0; }
  else if (gNCal == 1) { gCalA = 1; gCalB = gCalTrue[0] - gCalMeas[0]; }
  else {
    float sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (int i = 0; i < gNCal; i++) { sx += gCalMeas[i]; sy += gCalTrue[i]; sxx += gCalMeas[i] * gCalMeas[i]; sxy += gCalMeas[i] * gCalTrue[i]; }
    float den = gNCal * sxx - sx * sx;
    if (fabsf(den) < 1e-9f) { gCalA = 1; gCalB = (sy - sx) / gNCal; }
    else { gCalA = (gNCal * sxy - sx * sy) / den; gCalB = (sy - gCalA * sx) / gNCal; }
  }
  gSaveCal();
}

// ---------------------------------------------------------------- richieste (eseguite nel task)
static void gServeRequest(int req) {
  if (req == GREQ_DARK) {
    gAverage(false, gDark, 32);
    gHaveDark = true;
    float mx = 0; for (int i = 0; i < G_NPIX; i++) mx = max(mx, gDark[i]);
    gSaveRefs();
    snprintf(gReqMsg, sizeof(gReqMsg), "gauge_dark OK: max dark %.0f LSB%s", mx,
             mx > 500 ? " — ATTENZIONE luce ambiente alta (schermare / passabanda 650 nm)" : "");
  } else if (req == GREQ_REF) {
    if (!gHaveDark) { gAverage(false, gDark, 32); gHaveDark = true; }
    const char* warn = "";
    for (int it = 0; it < 25; it++) {
      gAverage(true, gRef, 4);
      float pk = gPeak(gRef), rawMax = 0;
      for (int i = 0; i < G_NPIX; i++) rawMax = max(rawMax, gRef[i]);
      if (rawMax >= G_ADC_SAT || pk > G_ADC_HI) {
        if (gExposureUs <= G_EXP_MIN) { warn = " — SATURO all'esposizione minima: aggiungere filtro ND"; break; }
        gExposureUs = max(G_EXP_MIN, (uint32_t)(gExposureUs * 0.6f));
      } else if (pk < G_ADC_LO) {
        if (gExposureUs >= G_EXP_MAX) { warn = " — segnale basso all'esposizione massima: ridurre ND / allineare"; break; }
        gExposureUs = min(G_EXP_MAX, (uint32_t)(gExposureUs * 1.4f) + 1);
      } else break;
    }
    gAverage(true, gRef, 32);
    gHaveRef = true;
    float pk = gPeak(gRef), mn = 1e9f;
    for (int i = 2; i < G_NPIX - 2; i++) mn = min(mn, gRef[i] - gDark[i]);
    gSaveRefs();
    portENTER_CRITICAL(&gMux); gBufCount = 0; gBufIdx = 0; portEXIT_CRITICAL(&gMux);
    snprintf(gReqMsg, sizeof(gReqMsg), "gauge_ref OK: esposizione %u us, picco %.0f, minimo %.0f LSB (uniformita %.0f%%)%s%s",
             (unsigned)gExposureUs, pk, mn, pk > 0 ? 100.0f * mn / pk : 0.0f,
             (mn < 0.3f * pk) ? " — bordi poco illuminati" : "", warn);
  } else if (req == GREQ_CAL) {
    float trueMm = gReqArg, sum = 0, d, c; int ok = 0;
    for (int k = 0; k < 8; k++) if (gaugeMeasureRaw(GAUGE_FRAMES_PER_MEAS, d, c)) { sum += d; ok++; }
    if (ok < 6) { snprintf(gReqMsg, sizeof(gReqMsg), "gauge_cal ERRORE: misura non valida (spina presente? riferimento fatto?)"); return; }
    if (gNCal >= G_MAX_CAL) { snprintf(gReqMsg, sizeof(gReqMsg), "gauge_cal ERRORE: massimo %d punti, usa gauge_calreset", G_MAX_CAL); return; }
    gCalMeas[gNCal] = sum / ok; gCalTrue[gNCal] = trueMm; gNCal++;
    gFitCal();
    int n = snprintf(gReqMsg, sizeof(gReqMsg), "gauge_cal OK: mm = %.6f * misura + %.4f (%d punti). Residui um:", gCalA, gCalB, gNCal);
    for (int i = 0; i < gNCal && n < (int)sizeof(gReqMsg) - 12; i++)
      n += snprintf(gReqMsg + n, sizeof(gReqMsg) - n, " %+.1f", 1000.0f * (gCalA * gCalMeas[i] + gCalB - gCalTrue[i]));
  } else if (req == GREQ_PROFILE) {
    if (!gHaveDark || !gHaveRef) { snprintf(gReqMsg, sizeof(gReqMsg), "gauge_profile: esegui prima gauge_dark e gauge_ref"); return; }
    gAverage(true, gAcc, 4);
    for (int i = 0; i < G_NPIX; i++) {
      float span = gRef[i] - gDark[i];
      Serial.println(span > 50 ? (gAcc[i] - gDark[i]) / span : 1.0f, 4);
    }
    snprintf(gReqMsg, sizeof(gReqMsg), "gauge_profile: 128 valori inviati su Serial");
  }
}

static void gaugeTask(void*) {
  for (;;) {
    int req = gReq;
    if (req != GREQ_NONE) {
      gServeRequest(req);
      gReq = GREQ_NONE;
      gReqDone = true;
      continue;
    }
    if (gHaveDark && gHaveRef) {
      float d = 0, c = 0;
      bool ok = gaugeMeasureRaw(GAUGE_FRAMES_PER_MEAS, d, c);
      portENTER_CRITICAL(&gMux);
      if (ok) {
        gBuf[gBufIdx % GAUGE_BUF_SIZE] = d;
        gBufIdx++;
        if (gBufCount < GAUGE_BUF_SIZE) gBufCount++;
      } else {
        gBufCount = 0;               // cavo assente: niente valori vecchi nel buffer
      }
      gLastValid = ok; gLastRawMm = ok ? d : 0.0f; gLastPosMm = ok ? c : 0.0f;
      gMeasCount++;
      portEXIT_CRITICAL(&gMux);
      vTaskDelay(1);
    } else {
      vTaskDelay(pdMS_TO_TICKS(50));
    }
  }
}

// ---------------------------------------------------------------- API usata dal resto del firmware
void gaugeSetup() {
  pinMode(GAUGE_SI_PIN, OUTPUT);
  pinMode(GAUGE_CLK_PIN, OUTPUT);
  pinMode(GAUGE_LASER_PIN, OUTPUT);
  digitalWrite(GAUGE_SI_PIN, LOW);
  digitalWrite(GAUGE_CLK_PIN, LOW);
  digitalWrite(GAUGE_LASER_PIN, LOW);
  analogReadResolution(12);
  analogSetPinAttenuation(GAUGE_AO_PIN, ADC_11db);
  gPrefs.begin("razorgauge", false);
  gLoadAll();
  for (int i = 0; i < 3; i++) gReadFrame(gRaw);
  xTaskCreatePinnedToCore(gaugeTask, "gauge", 6144, nullptr, 1, nullptr, 0);
  Serial.printf("RazorGauge: dark %s, riferimento %s, esposizione %u us, calibrazione %d punti\n",
                gHaveDark ? "OK" : "MANCANTE", gHaveRef ? "OK" : "MANCANTE", (unsigned)gExposureUs, gNCal);
  if (!gHaveDark || !gHaveRef) Serial.println("RazorGauge: senza cavo inviare gauge_dark e gauge_ref");
}

// Diametro calibrato (mediana del buffer). NAN se nessun cavo / sensore non pronto.
// Sostituisce readCaliperBufferedMedian(): istantanea, non blocca.
float gaugeReadDisplay() {
  float tmp[GAUGE_BUF_SIZE];
  int n;
  portENTER_CRITICAL(&gMux);
  n = gBufCount;
  for (int i = 0; i < n; i++) tmp[i] = gBuf[(gBufIdx - n + i + GAUGE_BUF_SIZE * 2) % GAUGE_BUF_SIZE];
  portEXIT_CRITICAL(&gMux);
  if (n == 0) return NAN;
  for (int i = 1; i < n; i++) { float key = tmp[i]; int j = i - 1; while (j >= 0 && tmp[j] > key) { tmp[j + 1] = tmp[j]; j--; } tmp[j + 1] = key; }
  return gCalA * tmp[n / 2] + gCalB;
}

// Risposta a un comando gauge: sempre su Serial, e al solo client WebSocket che l'ha inviato
// (un client che non manda comandi gauge_* — l'app WPF attuale — non riceve nulla di nuovo).
static void gaugeReply(int client, const char* msg) {
  Serial.println(msg);
  if (client >= 0) {
    String m = String(msg); m.replace("\\", "/"); m.replace("\"", "'");
    String json = "{\"type\":\"gauge\",\"msg\":\"" + m + "\"}";
    webSocket.sendTXT((uint8_t)client, json);
  }
}

static void gaugePost(int req, float arg) {
  if (gReq != GREQ_NONE) { gaugeReply(gCmdClient, "RazorGauge occupato: attendere la fine del comando precedente"); return; }
  gReqArg = arg; gReqClient = gCmdClient; gReqDone = false; gReq = req;
  gaugeReply(gCmdClient, "RazorGauge: comando in esecuzione...");
}

// Da chiamare a ogni giro di loop(): consegna i risultati dei comandi eseguiti dal task.
void gaugePollRequest() {
  if (!gReqDone) return;
  gReqDone = false;
  gaugeReply(gReqClient, gReqMsg);
}

// Gestione comandi gauge_*: true se il comando era suo.
bool gaugeHandleCommand(const String& cmd) {
  if (!cmd.startsWith("gauge_")) return false;
  if (cmd == "gauge_dark")        gaugePost(GREQ_DARK, 0);
  else if (cmd == "gauge_ref")    gaugePost(GREQ_REF, 0);
  else if (cmd == "gauge_profile") gaugePost(GREQ_PROFILE, 0);
  else if (cmd.startsWith("gauge_cal ")) {
    float mm = cmd.substring(10).toFloat();
    if (mm < 0.05f || mm > 8.0f) gaugeReply(gCmdClient, "gauge_cal: diametro non valido (0.05-8 mm)");
    else gaugePost(GREQ_CAL, mm);
  }
  else if (cmd == "gauge_calreset") {
    if (gReq != GREQ_NONE) { gaugeReply(gCmdClient, "RazorGauge occupato"); return true; }
    gNCal = 0; gFitCal();
    gaugeReply(gCmdClient, "gauge_calreset OK: calibrazione cancellata (mm = misura)");
  }
  else if (cmd.startsWith("gauge_exp ")) {
    gExposureUs = constrain((uint32_t)cmd.substring(10).toInt(), G_EXP_MIN, G_EXP_MAX);
    gPrefs.putUInt("exp", gExposureUs);
    char b[80]; snprintf(b, sizeof(b), "gauge_exp: %u us (rifare gauge_ref)", (unsigned)gExposureUs);
    gaugeReply(gCmdClient, b);
  }
  else if (cmd == "gauge_status") {
    char b[320];
    float disp = gaugeReadDisplay();
    snprintf(b, sizeof(b), "RazorGauge: dark %s, rif %s, esp %u us, cal %d punti (A=%.6f B=%.4f), misure %lu, ultima %s %.4f mm raw, pos %+.3f mm, display %.4f mm",
             gHaveDark ? "OK" : "NO", gHaveRef ? "OK" : "NO", (unsigned)gExposureUs, gNCal, gCalA, gCalB,
             (unsigned long)gMeasCount, gLastValid ? "valida" : "NON valida", (float)gLastRawMm, (float)gLastPosMm,
             isfinite(disp) ? disp : 0.0f);
    gaugeReply(gCmdClient, b);
  }
  else gaugeReply(gCmdClient, "gauge: comandi gauge_dark | gauge_ref | gauge_cal <mm> | gauge_calreset | gauge_exp <us> | gauge_status | gauge_profile");
  return true;
}
