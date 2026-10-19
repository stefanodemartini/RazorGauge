static const int      G_NPIX       = 128;
static const float    G_PIXEL_MM   = 0.0635f;
static const int      G_MARGIN_PX  = 8;        // pixel oltre i bordi inclusi nell'area (frange di diffrazione)
static const float    G_EDGE_FIND  = 0.5f;     // soglia usata SOLO per localizzare l'ombra (e per il diametro "a soglia" di controllo)
static const float    G_SHADOW_MIN = 0.3f;     // minimo normalizzato sopra cui "nessun cavo"
// ADC in mV calibrati (analogReadMilliVolts, curva di fabbrica dell'eFuse). A 11 dB l'ADC dell'ESP32 e lineare
// circa tra 150 e 2450 mV: il picco del riferimento si porta tra G_MV_LO e G_MV_HI, sopra G_MV_SAT e fuori scala.
static const int      G_MV_LO = 1700, G_MV_HI = 2300, G_MV_SAT = 2450;
static const int      G_OVERSAMPLE = 2;        // letture ADC per pixel (media): rumore ADC / sqrt(2)
static const float    G_SPAN_MIN   = 40.0f;    // mV: pixel con (rif - buio) piu piccolo sono considerati non illuminati
static const uint32_t G_EXP_MIN = 2, G_EXP_MAX = 20000;
static const int      G_MAX_CAL = 10;
#define GAUGE_FRAMES_PER_MEAS 8                 // frame mediati per ogni misura del task
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

// --- diagnostica dell'ultima misura (per /gauge e la pagina /diag) ---
struct GaugeDiag {
  bool     ok;
  char     why[28];        // motivo se non valida
  float    diam;           // mm, area (non calibrato)
  float    diamEdge;       // mm, distanza tra i fronti al 50% (solo controllo)
  float    center;         // mm, posizione del centro dell'ombra rispetto al centro del sensore
  float    k;              // energia dell'impulso rispetto al riferimento (1 = come al gauge_ref)
  float    flat;           // %, scarto RMS dei pixel illuminati fuori ombra dopo la correzione k (uniformita/deriva)
  float    peak;           // mV, picco (segnale - buio)
  int      sat;            // pixel sopra G_MV_SAT
  int      L, R;           // finestra di integrazione (pixel)
  uint32_t n;              // numero misura
  uint16_t raw[G_NPIX];    // mV medi del frame
  int16_t  norm[G_NPIX];   // normalizzato x1000
};
static GaugeDiag gDiag;
static GaugeDiag gDiagTmp;

enum { GREQ_NONE = 0, GREQ_DARK, GREQ_REF, GREQ_CAL, GREQ_PROFILE, GREQ_STAT };
static volatile int   gReq = GREQ_NONE;
static volatile float gReqArg = 0.0f;
static volatile bool  gReqDone = false;
static char           gReqMsg[360];
static int            gReqClient = -1;   // client WebSocket che ha chiesto (-1 = Serial / pagina /diag)
static int            gCmdClient = -1;   // client dell'ultimo comando ricevuto
static char           gLastMsg[360] = "";  // ultima risposta (mostrata dalla pagina /diag)

// ---------------------------------------------------------------- sensore
static inline uint16_t gAdcMv() {
  uint32_t s = 0;
  for (int k = 0; k < G_OVERSAMPLE; k++) s += analogReadMilliVolts(GAUGE_AO_PIN);
  return (uint16_t)(s / G_OVERSAMPLE);
}

// Lettura del frame: 128 pixel in mV calibrati.
static void gReadFrame(uint16_t* buf) {
  digitalWrite(GAUGE_SI_PIN, HIGH);
  digitalWrite(GAUGE_CLK_PIN, HIGH);
  digitalWrite(GAUGE_SI_PIN, LOW);
  for (int i = 0; i < G_NPIX; i++) {
    delayMicroseconds(1);
    buf[i] = gAdcMv();
    digitalWrite(GAUGE_CLK_PIN, LOW);
    digitalWrite(GAUGE_CLK_PIN, HIGH);
  }
  digitalWrite(GAUGE_CLK_PIN, LOW);   // 129° clock
  delayMicroseconds(20);              // t_qt prima del prossimo SI
}

// Scarico veloce SENZA lettura: azzera i pixel e fa partire l'integrazione (dal 18° clock).
// Prima si leggeva anche questo frame: ~3 ms di luce ambiente in piu nella posa, ora ~30 µs.
static void gClockOut() {
  digitalWrite(GAUGE_SI_PIN, HIGH);
  digitalWrite(GAUGE_CLK_PIN, HIGH);
  digitalWrite(GAUGE_SI_PIN, LOW);
  for (int i = 0; i < G_NPIX; i++) {
    digitalWrite(GAUGE_CLK_PIN, LOW);
    digitalWrite(GAUGE_CLK_PIN, HIGH);
  }
  digitalWrite(GAUGE_CLK_PIN, LOW);
  delayMicroseconds(20);
}

static void gCapture(bool laser, uint16_t* buf) {
  gClockOut();                        // scarica il frame precedente, avvia l'integrazione
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
  } else {
    delayMicroseconds(gExposureUs);   // buio con la stessa posa del laser
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

static bool gFail(const char* why) {
  strncpy(gDiagTmp.why, why, sizeof(gDiagTmp.why) - 1); gDiagTmp.why[sizeof(gDiagTmp.why) - 1] = 0;
  gDiagTmp.ok = false;
  return false;
}

// Misura grezza (non calibrata), mm. false = nessun cavo / ombra fuori campo. Riempie gDiagTmp.
static bool gaugeMeasureRaw(int nAvg, float& diamMm, float& centerMm) {
  gDiagTmp.ok = false; gDiagTmp.why[0] = 0; gDiagTmp.diam = gDiagTmp.diamEdge = gDiagTmp.center = 0;
  gDiagTmp.k = 0; gDiagTmp.flat = 0; gDiagTmp.L = gDiagTmp.R = -1;
  if (!gHaveDark || !gHaveRef) return gFail("manca buio/riferimento");
  gAverage(true, gAcc, nAvg);
  int sat = 0;
  for (int i = 0; i < G_NPIX; i++) {
    gDiagTmp.raw[i] = (uint16_t)constrain(lroundf(gAcc[i]), 0L, 65535L);
    if (gAcc[i] >= G_MV_SAT) sat++;
    float span = gRef[i] - gDark[i];
    gNorm[i] = (span > G_SPAN_MIN) ? (gAcc[i] - gDark[i]) / span : 1.0f;
  }
  gDiagTmp.sat = sat;
  gDiagTmp.peak = gPeak(gAcc);
  int imin = 2;
  for (int i = 2; i < G_NPIX - 2; i++) if (gNorm[i] < gNorm[imin]) imin = i;
  bool shadow = gNorm[imin] <= G_SHADOW_MIN;
  int l = imin, r = imin, L = 0, R = -1;
  if (shadow) {
    while (l > 0 && gNorm[l] < G_EDGE_FIND) l--;
    while (r < G_NPIX - 1 && gNorm[r] < G_EDGE_FIND) r++;
    L = l - G_MARGIN_PX; R = r + G_MARGIN_PX;
  }
  // correzione energia impulso: i pixel illuminati fuori finestra devono valere 1
  float sumK = 0; int nK = 0;
  for (int i = 2; i < G_NPIX - 2; i++) if (!shadow || i < L || i > R) { sumK += gNorm[i]; nK++; }
  float k = (nK > 0) ? sumK / nK : 1.0f;
  gDiagTmp.k = k;
  if (nK >= 10 && k > 0.5f && k < 1.5f) {
    float s2 = 0;
    for (int i = 2; i < G_NPIX - 2; i++) if (!shadow || i < L || i > R) { float e = gNorm[i] / k - 1.0f; s2 += e * e; }
    gDiagTmp.flat = 100.0f * sqrtf(s2 / nK);
  }
  for (int i = 0; i < G_NPIX; i++) gDiagTmp.norm[i] = (int16_t)constrain(lroundf(1000.0f * gNorm[i] / (k > 0.5f && k < 1.5f ? k : 1.0f)), -32000L, 32000L);
  if (!shadow) return gFail("nessun cavo");
  if (L < 0 || R > G_NPIX - 1) return gFail("ombra al bordo del sensore");
  if (nK < 10) return gFail("troppo pochi pixel illuminati");
  if (k > 0.5f && k < 1.5f) for (int i = L; i <= R; i++) gNorm[i] /= k;
  else return gFail("energia laser anomala");
  float area = 0, moment = 0;
  for (int i = L; i <= R; i++) { float d = 1.0f - gNorm[i]; area += d; moment += d * i; }
  if (area <= 0) return gFail("area nulla");
  diamMm   = area * G_PIXEL_MM;
  centerMm = (moment / area - (G_NPIX - 1) / 2.0f) * G_PIXEL_MM;
  // diametro di controllo: fronti al 50% interpolati (sensibile alle frange, serve solo come confronto)
  float xl = l + (G_EDGE_FIND - gNorm[l]) / (gNorm[l + 1] - gNorm[l] + 1e-6f);
  float xr = r - 1 + (gNorm[r - 1] - G_EDGE_FIND) / (gNorm[r - 1] - gNorm[r] + 1e-6f);
  gDiagTmp.diamEdge = (xr - xl) * G_PIXEL_MM;
  gDiagTmp.diam = diamMm; gDiagTmp.center = centerMm; gDiagTmp.L = L; gDiagTmp.R = R;
  gDiagTmp.ok = true;
  return true;
}

static void gPublishDiag() {
  gDiagTmp.n = gMeasCount;
  portENTER_CRITICAL(&gMux);
  memcpy(&gDiag, &gDiagTmp, sizeof(GaugeDiag));
  portEXIT_CRITICAL(&gMux);
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
  gPrefs.putUChar("unit", 1);         // 1 = mV (firmware >= 0.6.0); i dati salvati dalle versioni precedenti erano in LSB
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
  bool mv = gPrefs.getUChar("unit", 0) == 1;   // buio e riferimento salvati in LSB da un firmware vecchio: da rifare
  if (mv && gPrefs.getBool("hasDark", false) && gPrefs.getBytes("dark", tmp, sizeof(tmp)) == sizeof(tmp)) {
    for (int i = 0; i < G_NPIX; i++) gDark[i] = tmp[i];
    gHaveDark = true;
  }
  if (mv && gPrefs.getBool("hasRef", false) && gPrefs.getBytes("ref", tmp, sizeof(tmp)) == sizeof(tmp)) {
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
    snprintf(gReqMsg, sizeof(gReqMsg), "gauge_dark OK: buio massimo %.0f mV%s", mx,
             mx > 400 ? " — ATTENZIONE luce ambiente alta (schermare / passabanda 650 nm)" : "");
  } else if (req == GREQ_REF) {
    if (!gHaveDark) { gAverage(false, gDark, 32); gHaveDark = true; }
    const char* warn = "";
    for (int it = 0; it < 25; it++) {
      gAverage(true, gRef, 4);
      float pk = gPeak(gRef), rawMax = 0;
      for (int i = 0; i < G_NPIX; i++) rawMax = max(rawMax, gRef[i]);
      if (rawMax >= G_MV_SAT || pk > G_MV_HI) {
        if (gExposureUs <= G_EXP_MIN) { warn = " — SATURO all'esposizione minima: aggiungere filtro ND"; break; }
        gExposureUs = max(G_EXP_MIN, (uint32_t)(gExposureUs * 0.6f));
      } else if (pk < G_MV_LO) {
        if (gExposureUs >= G_EXP_MAX) { warn = " — segnale basso all'esposizione massima: ridurre ND / allineare"; break; }
        gExposureUs = min(G_EXP_MAX, (uint32_t)(gExposureUs * 1.4f) + 1);
      } else break;
    }
    gAverage(false, gDark, 32);        // buio rifatto alla posa definitiva (la posa cambia anche il buio)
    gAverage(true, gRef, 32);
    gHaveRef = true;
    float pk = gPeak(gRef), mn = 1e9f;
    for (int i = 2; i < G_NPIX - 2; i++) mn = min(mn, gRef[i] - gDark[i]);
    gSaveRefs();
    portENTER_CRITICAL(&gMux); gBufCount = 0; gBufIdx = 0; portEXIT_CRITICAL(&gMux);
    snprintf(gReqMsg, sizeof(gReqMsg), "gauge_ref OK: esposizione %u us, picco %.0f mV, minimo %.0f mV (uniformita %.0f%%)%s%s",
             (unsigned)gExposureUs, pk, mn, pk > 0 ? 100.0f * mn / pk : 0.0f,
             (mn < 0.3f * pk) ? " — bordi poco illuminati" : "", warn);
  } else if (req == GREQ_CAL) {
    float trueMm = gReqArg, sum = 0, d, c; int ok = 0;
    for (int k = 0; k < 16; k++) if (gaugeMeasureRaw(GAUGE_FRAMES_PER_MEAS, d, c)) { sum += d; ok++; }
    gPublishDiag();
    if (ok < 12) { snprintf(gReqMsg, sizeof(gReqMsg), "gauge_cal ERRORE: misura non valida (spina presente? riferimento fatto?)"); return; }
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
      Serial.println(span > G_SPAN_MIN ? (gAcc[i] - gDark[i]) / span : 1.0f, 4);
    }
    snprintf(gReqMsg, sizeof(gReqMsg), "gauge_profile: 128 valori inviati su Serial (anche grafico in /diag)");
  } else if (req == GREQ_STAT) {
    // Ripetibilita: N misure consecutive (oggetto fermo). Welford per media e deviazione standard.
    int N = constrain((int)gReqArg, 10, 2000), ok = 0;
    double m = 0, s = 0, mc = 0, sc = 0, me = 0, mf = 0; float mn = 1e9f, mx = -1e9f;
    uint32_t t0 = millis();
    for (int i = 0; i < N; i++) {
      float d, c;
      if (gaugeMeasureRaw(GAUGE_FRAMES_PER_MEAS, d, c)) {
        float v = gCalA * d + gCalB; ok++;
        double dl = v - m; m += dl / ok; s += dl * (v - m);
        double dc = c - mc; mc += dc / ok; sc += dc * (c - mc);
        me += (gCalA * gDiagTmp.diamEdge + gCalB - me) / ok; mf += (gDiagTmp.flat - mf) / ok;
        mn = min(mn, v); mx = max(mx, v);
      }
      if ((i & 15) == 0) gPublishDiag();
    }
    gPublishDiag();
    if (ok < 2) { snprintf(gReqMsg, sizeof(gReqMsg), "gauge_stat ERRORE: %d misure valide su %d (cavo/spina presente?)", ok, N); return; }
    snprintf(gReqMsg, sizeof(gReqMsg),
             "gauge_stat %d/%d in %.1f s: media %.4f mm, dev.std %.2f um, min %.4f, max %.4f (escursione %.1f um); "
             "fronti 50%% %.4f mm; centro %+.3f mm (dev %.1f um); uniformita fuori ombra %.2f%%",
             ok, N, (millis() - t0) / 1000.0f, m, 1000.0 * sqrt(s / (ok - 1)), mn, mx, 1000.0f * (mx - mn),
             me, mc, 1000.0 * sqrt(sc / (ok - 1)), mf);
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
      gPublishDiag();
      vTaskDelay(1);
    } else {
      // senza buio/riferimento: frame grezzo ogni 200 ms, solo per la pagina /diag (allineamento del laser)
      gAverage(true, gAcc, 1);
      for (int i = 0; i < G_NPIX; i++) { gDiagTmp.raw[i] = (uint16_t)constrain(lroundf(gAcc[i]), 0L, 65535L); gDiagTmp.norm[i] = 0; }
      gDiagTmp.peak = 0; gDiagTmp.sat = 0;
      for (int i = 0; i < G_NPIX; i++) { gDiagTmp.peak = max(gDiagTmp.peak, gAcc[i]); if (gAcc[i] >= G_MV_SAT) gDiagTmp.sat++; }
      gFail("manca buio/riferimento");
      gPublishDiag();
      vTaskDelay(pdMS_TO_TICKS(200));
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
  memset(&gDiag, 0, sizeof(gDiag)); memset(&gDiagTmp, 0, sizeof(gDiagTmp));
  for (int i = 0; i < 3; i++) gReadFrame(gRaw);
  xTaskCreatePinnedToCore(gaugeTask, "gauge", 6144, nullptr, 1, nullptr, 0);
  Serial.printf("RazorGauge: dark %s, riferimento %s, esposizione %u us, calibrazione %d punti\n",
                gHaveDark ? "OK" : "MANCANTE", gHaveRef ? "OK" : "MANCANTE", (unsigned)gExposureUs, gNCal);
  if (!gHaveDark || !gHaveRef) Serial.println("RazorGauge: senza cavo inviare gauge_dark e gauge_ref (o dalla pagina http://<ip>/diag)");
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

// Risposta a un comando gauge: sempre su Serial e nella pagina /diag, e al solo client WebSocket che l'ha inviato
// (un client che non manda comandi gauge_* — l'app WPF attuale — non riceve nulla di nuovo).
static void gaugeReply(int client, const char* msg) {
  Serial.println(msg);
  strncpy(gLastMsg, msg, sizeof(gLastMsg) - 1); gLastMsg[sizeof(gLastMsg) - 1] = 0;
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
  else if (cmd == "gauge_stat" || cmd.startsWith("gauge_stat ")) {
    int n = cmd.length() > 11 ? cmd.substring(11).toInt() : 200;
    gaugePost(GREQ_STAT, (float)(n > 0 ? n : 200));
  }
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
    char b[360];
    float disp = gaugeReadDisplay();
    snprintf(b, sizeof(b), "RazorGauge: dark %s, rif %s, esp %u us, cal %d punti (A=%.6f B=%.4f), misure %lu, ultima %s %.4f mm raw, pos %+.3f mm, display %.4f mm, k %.3f, uniformita %.2f%%, picco %.0f mV, saturi %d",
             gHaveDark ? "OK" : "NO", gHaveRef ? "OK" : "NO", (unsigned)gExposureUs, gNCal, gCalA, gCalB,
             (unsigned long)gMeasCount, gLastValid ? "valida" : "NON valida", (float)gLastRawMm, (float)gLastPosMm,
             isfinite(disp) ? disp : 0.0f, gDiag.k, gDiag.flat, gDiag.peak, gDiag.sat);
    gaugeReply(gCmdClient, b);
  }
  else gaugeReply(gCmdClient, "gauge: comandi gauge_dark | gauge_ref | gauge_cal <mm> | gauge_calreset | gauge_exp <us> | gauge_stat [n] | gauge_status | gauge_profile");
  return true;
}

// ---------------------------------------------------------------- pagina di servizio /diag e dati /gauge
// Solo per collaudo e allineamento dal browser (telefono/PC sulla stessa rete): non tocca il protocollo dell'app WPF.
static void gaugeHttpJson() {
  GaugeDiag d;
  portENTER_CRITICAL(&gMux);
  memcpy(&d, &gDiag, sizeof(GaugeDiag));
  portEXIT_CRITICAL(&gMux);
  float disp = gaugeReadDisplay();
  String j; j.reserve(4200);
  char b[420];
  String msg = String(gLastMsg); msg.replace("\\", "/"); msg.replace("\"", "'");
  snprintf(b, sizeof(b),
           "{\"fw\":\"%s\",\"n\":%lu,\"ok\":%s,\"why\":\"%s\",\"diam\":%.4f,\"cal\":%.4f,\"disp\":%.4f,\"edge\":%.4f,\"center\":%.4f,"
           "\"k\":%.4f,\"flat\":%.3f,\"peak\":%.0f,\"sat\":%d,\"L\":%d,\"R\":%d,\"exp\":%u,\"dark\":%s,\"ref\":%s,\"ncal\":%d,"
           "\"calA\":%.6f,\"calB\":%.5f,\"busy\":%s,\"msg\":\"",
           FIRMWARE_VERSION, (unsigned long)d.n, d.ok ? "true" : "false", d.why, d.diam, d.ok ? gCalA * d.diam + gCalB : 0.0f,
           isfinite(disp) ? disp : 0.0f, d.ok ? gCalA * d.diamEdge + gCalB : 0.0f, d.center, d.k, d.flat, d.peak, d.sat, d.L, d.R,
           (unsigned)gExposureUs, gHaveDark ? "true" : "false", gHaveRef ? "true" : "false", gNCal, gCalA, gCalB,
           gReq != GREQ_NONE ? "true" : "false");
  j += b; j += msg; j += "\",\"raw\":[";
  for (int i = 0; i < G_NPIX; i++) { j += d.raw[i]; if (i < G_NPIX - 1) j += ','; }
  j += "],\"norm\":[";
  for (int i = 0; i < G_NPIX; i++) { j += d.norm[i]; if (i < G_NPIX - 1) j += ','; }
  j += "],\"refmv\":[";
  for (int i = 0; i < G_NPIX; i++) { j += (int)lroundf(gRef[i]); if (i < G_NPIX - 1) j += ','; }
  j += "],\"darkmv\":[";
  for (int i = 0; i < G_NPIX; i++) { j += (int)lroundf(gDark[i]); if (i < G_NPIX - 1) j += ','; }
  j += "]}";
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", j);
}

static const char GAUGE_DIAG_HTML[] PROGMEM = R"HTML(<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RazorGauge diag</title>
<style>body{font:14px system-ui,sans-serif;margin:0;padding:12px;background:#f3f4f6;color:#111}
h1{font-size:17px;margin:0 0 8px}canvas{width:100%;height:300px;background:#fff;border:1px solid #ccc;border-radius:6px}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:6px;margin:8px 0}
.c{background:#fff;border:1px solid #ddd;border-radius:6px;padding:6px 8px}.c b{display:block;font-size:18px}
.c span{color:#666;font-size:12px}button,input{font:14px system-ui;padding:6px 10px;margin:2px}
#msg{background:#fff;border:1px solid #ddd;border-radius:6px;padding:8px;min-height:20px;white-space:pre-wrap}
.bad{color:#b00}.okc{color:#070}.lg span{margin-right:12px;font-size:12px}</style></head><body>
<h1>RazorGauge &mdash; diagnostica <span id="fw"></span></h1>
<canvas id="cv" width="1024" height="300"></canvas>
<div class="lg"><span style="color:#2563eb">&#9632; segnale mV</span><span style="color:#999">&#9632; riferimento mV</span><span style="color:#000">&#9632; buio mV</span><span style="color:#dc2626">&#9632; normalizzato (0&ndash;1)</span><span style="color:#16a34a">&#9632; finestra</span></div>
<div class="g">
<div class="c"><span>Diametro calibrato</span><b id="cal">-</b></div>
<div class="c"><span>Display (mediana 7)</span><b id="disp">-</b></div>
<div class="c"><span>Ripetibilita (ultime 100)</span><b id="rep">-</b></div>
<div class="c"><span>Fronti 50% (controllo)</span><b id="edge">-</b></div>
<div class="c"><span>Centro ombra</span><b id="ctr">-</b></div>
<div class="c"><span>Energia k / uniformita</span><b id="kf">-</b></div>
<div class="c"><span>Picco / saturi / posa</span><b id="pk">-</b></div>
<div class="c"><span>Stato</span><b id="st">-</b></div>
</div>
<div><button onclick="cmd('gauge_dark')">Buio (laser spento, senza cavo)</button>
<button onclick="cmd('gauge_ref')">Riferimento (senza cavo)</button>
<input id="mm" size="6" placeholder="mm spina"><button onclick="cmd('gauge_cal '+v('mm'))">Calibra con spina</button>
<button onclick="cmd('gauge_calreset')">Azzera calibrazione</button>
<input id="ns" size="5" value="200"><button onclick="cmd('gauge_stat '+v('ns'))">Statistica N misure</button>
<button onclick="cmd('gauge_status')">Stato</button>
<button onclick="hist=[]">Azzera ripetibilita</button></div>
<div id="msg"></div>
<script>
var hist=[],cv=document.getElementById('cv'),cx=cv.getContext('2d');function v(i){return document.getElementById(i).value}
function cmd(c){fetch('/gauge/cmd?c='+encodeURIComponent(c)).then(function(){setTimeout(poll,300)})}
function line(a,s,col,mx){cx.strokeStyle=col;cx.lineWidth=2;cx.beginPath();for(var i=0;i<a.length;i++){var x=i*cv.width/127,y=cv.height-6-(a[i]*s/mx)*(cv.height-12);if(i)cx.lineTo(x,y);else cx.moveTo(x,y)}cx.stroke()}
function draw(d){cx.clearRect(0,0,cv.width,cv.height);var mx=2600;
if(d.L>=0){cx.fillStyle='rgba(22,163,74,.12)';cx.fillRect(d.L*cv.width/127,0,(d.R-d.L)*cv.width/127,cv.height)}
cx.strokeStyle='#eee';for(var g=0;g<=2500;g+=500){var y=cv.height-6-g/mx*(cv.height-12);cx.beginPath();cx.moveTo(0,y);cx.lineTo(cv.width,y);cx.stroke()}
if(d.ref)line(d.refmv,1,'#999',mx);if(d.dark)line(d.darkmv,1,'#000',mx);line(d.raw,1,'#2563eb',mx);
if(d.ref){var n=d.norm.map(function(x){return x/1000});line(n,1,'#dc2626',1.1)}}
function f(x,n){return (x==null||isNaN(x))?'-':x.toFixed(n)}
function poll(){fetch('/gauge').then(function(r){return r.json()}).then(function(d){
document.getElementById('fw').textContent='fw '+d.fw;draw(d);
if(d.ok){hist.push(d.cal);if(hist.length>100)hist.shift()}
var m=0,s=0;hist.forEach(function(x){m+=x});m/=hist.length||1;hist.forEach(function(x){s+=(x-m)*(x-m)});s=hist.length>1?Math.sqrt(s/(hist.length-1)):0;
document.getElementById('cal').textContent=d.ok?f(d.cal,4)+' mm':'-';
document.getElementById('disp').textContent=d.disp>0?f(d.disp,4)+' mm':'-';
document.getElementById('rep').textContent=hist.length>1?'±'+f(s*1000,1)+' µm (n '+hist.length+')':'-';
document.getElementById('edge').textContent=d.ok?f(d.edge,4)+' mm':'-';
document.getElementById('ctr').textContent=d.ok?f(d.center,3)+' mm':'-';
document.getElementById('kf').textContent=f(d.k,3)+' / '+f(d.flat,2)+'%';
document.getElementById('pk').textContent=f(d.peak,0)+' mV / '+d.sat+' / '+d.exp+' µs';
var st=document.getElementById('st');st.textContent=d.busy?'comando in corso...':(d.ok?'misura valida':d.why);st.className=d.ok?'okc':'bad';
document.getElementById('msg').textContent=d.msg+(d.ncal?'\ncalibrazione: '+d.ncal+' punti, A '+f(d.calA,6)+' B '+f(d.calB,5):'');
}).catch(function(){}).then(function(){setTimeout(poll,400)})}
poll();
</script></body></html>)HTML";

void gaugeHttpSetup() {
  server.on("/diag", HTTP_GET, []() { server.send(200, "text/html", String(GAUGE_DIAG_HTML)); });
  server.on("/gauge", HTTP_GET, []() { gaugeHttpJson(); });
  server.on("/gauge/cmd", HTTP_GET, []() {
    String c = server.arg("c");
    gCmdClient = -1;                    // risposta su Serial e nella pagina
    if (!gaugeHandleCommand(c)) { server.send(400, "text/plain", "comando non gauge_*"); return; }
    server.send(200, "text/plain", "ok");
  });
}
