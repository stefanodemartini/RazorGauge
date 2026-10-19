
#include <WiFi.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <EEPROM.h>
#include <WiFiManager.h>
#include <HardwareSerial.h>
#include <Preferences.h>
#include "driver/pcnt.h"  // ESP32 hardware pulse counter — immune to ISR interference

// ===============================
// FW
// ===============================
// Major: il laser sostituisce il calibro. Non e un passo avanti sulla linea 0.4.x col calibro, e
// un ramo diverso - principio di misura diverso, hardware diverso, build non intercambiabili. La
// numerazione in fila (0.6.0 accanto a 0.4.22) suggeriva il contrario, cioe "piu nuova quindi da
// usare", mentre quella che gira e la 0.4.22-RB2. 0.x = era calibro, 1.x = era laser.
// -alpha: scritta, compila, non ancora provata sul banco.
#define FIRMWARE_VERSION "1.0.0-alpha"
#define FIRMWARE_DATE "2026-10-10"
#define FIRMWARE_FEATURES "WiFi Manager + EMA + 0.01mm + UART Motor + Scan timer + Autostop + RicezioneON/OFF + GOTOPOS + Caliper timeout + Atomic encoder + Watchdog fixes + Scan state sync on connect + GOTOPOS chart overlay + encoder init fix + non-blocking caliper buffer + GOTOPOS overshoot safety guard + mirrored profile chart + hardware PCNT encoder (ISR-immune) + RazorGauge optical shadow gauge (replaces caliper) + web UI removed (WPF app via WebSocket) + goto_status completed broadcast fix + USE_RAZORBOARD pin switch + RazorGauge 0.6: ADC in mV calibrati + oversampling + posa del buio = posa laser + scarico veloce + indici di qualita + gauge_stat + pagina /diag + GOTOPOS corretto con PPC calibrato"

// -----------------------------
// 1 = cablaggio sulla scheda RazorBoard (encoder su GPIO32/33, condizionato da 74HC14)
// 0 = cablaggio attuale volante (encoder su GPIO12/13). GPIO12 e un pin di avvio: con la scheda si evita.
#define USE_RAZORBOARD 1   // 1 = master montato sulla RazorBoard (encoder su GPIO32/33); 0 = vecchio cablaggio (GPIO12/13)
#if USE_RAZORBOARD
#define ENCODER_DATA_PIN 32
#define ENCODER_CLOCK_PIN 33
#else
#define ENCODER_DATA_PIN 12
#define ENCODER_CLOCK_PIN 13
#endif
// RazorGauge (TSL1401 + laser) — riusa i pin del vecchio calibro + 2 pin nuovi
#define GAUGE_SI_PIN    26   // ex CALIPER_CLOCK_PIN
#define GAUGE_CLK_PIN   27   // ex CALIPER_DATA_PIN
#define GAUGE_AO_PIN    34   // ADC1_CH6, solo ingresso. NON usare pin ADC2 (conflitto con il WiFi)
#define GAUGE_LASER_PIN 25   // comando laser via NPN/MOSFET
// Distanza (cm), lungo la linea, tra l'asse della ruota encoder (punto di contatto linea-ruota) e il punto di misura.
// Calibro centesimale: 20.0 mm. RazorGauge integrato nel FlylineProfiler (pezzo unico, 7/10/2026):
// asse ruota Z 49.55, linea di pixel del TSL1401 / asse laser Z 21.55  ->  28.00 mm (da CAD, cifra tonda dal 8/10/2026).
// Stesso verso di prima: il punto di misura sta dalla stessa parte della ruota in cui stava il calibro, 8.0 mm piu lontano.
#define MEAS_OFFSET_CM  2.800f
#define WIFI_RESET_PIN 14
// ── Encoder calibration ────────────────────────────────────────────────────
// Change ENCODER_PPR and WHEEL_CIRC_MM to match your hardware.
// PULSES_PER_CM is then derived automatically — never set it directly.
//
//   ENCODER_PPR   : pulses per revolution, from encoder datasheet.
//   WHEEL_CIRC_MM : wheel circumference in mm. Measure by wrapping a piece of
//                   string around the wheel once, then measuring the string.
//                   Do NOT calculate from the diameter unless you are sure it
//                   is the rolling diameter (not the outer or bore diameter).
//
// Hardware PCNT counting mode: PCNT_UNIT_0 counts only A-phase edges where
// B=0. This is 1× decoding → effective counts = 1× PPR per revolution.
// The hardware counter is immune to caliper ISR interference.
//
// Formula:  PULSES_PER_CM = (ENCODER_PPR × 10) / WHEEL_CIRC_MM
//   e.g.  PPR=600, circ=190 mm  →  6000/190 = 31.578 pulses/cm
//         PPR=600, circ=200 mm  →  6000/200 = 30 pulses/cm
// ──────────────────────────────────────────────────────────────────────────
#define ENCODER_PPR     600   // encoder datasheet value
#define WHEEL_CIRC_MM   200   // physical wheel circumference in mm
#define PULSES_PER_CM   ((ENCODER_PPR * 10.0f) / WHEEL_CIRC_MM)   // float: 6000/200 = 30.0
#define EEPROM_SIZE 512
#define EEPROM_ADDR_CALIB_PPC 4   // float (4 bytes) — calibrated pulses/cm; 0 = use formula

float lineDiameter = 0.0;
bool scanEnabled = false;
bool oldScanState = false;  // Per salvare stato scansione durante GOTOPOS

// FW-14: removed dead #define ALPHA 0.05 (actual EMA uses hardcoded 0.1f)

float smoothedDiameter = 0.0;
bool filterInitialized = false;
// EMA smoothing removed from firmware — app handles smoothing client-side

static const int MOTOR_UART_RX_PIN = 16;
static const int MOTOR_UART_TX_PIN = 17;
HardwareSerial SerialMotor(2);

String motorMode = "UNKNOWN";
String motorDir = "UNKNOWN";
unsigned long motorLastSeenMs = 0;

static char motorRxLine[48];
static size_t motorRxLen = 0;
static String motorTxPending;
static bool motorTxHasPending = false;

static unsigned long encoderLastMoveMs = 0;
static long encoderLastValueForWatchdog = 0;
static bool encoderWatchdogStopSent = false;

static unsigned long lastMotorPollMs = 0;
static const unsigned long MOTOR_POLL_INTERVAL_MS = 2000;
static const unsigned long MOTOR_STALE_MS = 4000;

// Parametri per GOTOPOS
const uint32_t MOTOR_FAST_HZ = 12000;

// Closed-loop scan speed control (compensates for spool diameter growth)
// Target 2 cm/s: motor runs smoothly at ~1500 Hz (low speed cogging causes caliper noise)
const float    TARGET_SCAN_SPEED_CMS = 2.0f;   // target linear speed during scan (cm/s)
const uint32_t SCAN_HZ_INIT = 1500;            // initial estimate (calibrated: 1500 Hz ≈ 2 cm/s)
const uint32_t SCAN_HZ_MIN  = 800;             // never go below ~1 cm/s — avoids cogging zone
const uint32_t SCAN_HZ_MAX  = 4000;            // headroom for spool growth compensation
uint32_t currentScanHz = SCAN_HZ_INIT;
bool isGoToActive = false;
float goToTargetCm = 0;
bool goToFwd = true;                  // direction of current GOTOPOS move (saved for overshoot guard)
unsigned long lastGoToStatusCheck = 0;
bool goToEncoderReached = false;  // set when encoder reaches target; used to send completed:true
static unsigned long lastPosSentMs = 0;  // throttle POS:<steps> updates to slave

struct DataPoint {
  int cm;         // corrected actual position (encoder-diameter compensated), cm
  int encoderCm;  // raw encoder position (used by GOTOPOS for slave command lookup)
  float diameter;
  float rawDisplay;
  DataPoint* next;
};

DataPoint* firstDataPoint = nullptr;
DataPoint* lastDataPoint = nullptr;
int totalDataPoints = 0;

// ── PCNT hardware encoder ──────────────────────────────────────────────────
// The ESP32 PCNT peripheral counts quadrature pulses in hardware, completely
// unaffected by caliper ISR activity that caused software-ISR miscounts.
#define PCNT_ENC_UNIT PCNT_UNIT_0
#define PCNT_H_LIM  30000  // ~1000 cm per overflow at PPC=30
#define PCNT_L_LIM -30000
static volatile long pcntAccum = 0;  // 32-bit overflow accumulator

static long getEncoderValue() {
  // Re-read until accumulator is stable across the PCNT snapshot
  long acc, acc2;
  int16_t cnt;
  do {
    acc = pcntAccum;
    pcnt_get_counter_value(PCNT_ENC_UNIT, &cnt);
    acc2 = pcntAccum;
  } while (acc != acc2);
  return acc + cnt;
}

static void setEncoderValue(long v) {
  pcnt_counter_pause(PCNT_ENC_UNIT);
  pcnt_counter_clear(PCNT_ENC_UNIT);
  pcntAccum = v;
  pcnt_counter_resume(PCNT_ENC_UNIT);
}

static void IRAM_ATTR pcntOverflowISR(void* arg) {
  uint32_t status;
  pcnt_get_event_status(PCNT_ENC_UNIT, &status);
  if (status & PCNT_EVT_H_LIM) pcntAccum += PCNT_H_LIM;
  if (status & PCNT_EVT_L_LIM) pcntAccum += PCNT_L_LIM;
}

static void setupPCNT() {
  pcnt_config_t cfg = {};
  cfg.pulse_gpio_num = ENCODER_DATA_PIN;   // A phase
  cfg.ctrl_gpio_num  = ENCODER_CLOCK_PIN;  // B phase (direction control)
  cfg.lctrl_mode = PCNT_MODE_KEEP;         // B=0: count normally
  cfg.hctrl_mode = PCNT_MODE_DISABLE;      // B=1: do not count (1x decoding)
  cfg.neg_mode   = PCNT_COUNT_INC;         // A falling + B=0 → forward (+)
  cfg.pos_mode   = PCNT_COUNT_DEC;         // A rising  + B=0 → reverse (-)
  cfg.counter_h_lim = PCNT_H_LIM;
  cfg.counter_l_lim = PCNT_L_LIM;
  cfg.unit    = PCNT_ENC_UNIT;
  cfg.channel = PCNT_CHANNEL_0;
  pcnt_unit_config(&cfg);
  pcnt_counter_pause(PCNT_ENC_UNIT);
  pcnt_counter_clear(PCNT_ENC_UNIT);
  pcnt_event_enable(PCNT_ENC_UNIT, PCNT_EVT_H_LIM);
  pcnt_event_enable(PCNT_ENC_UNIT, PCNT_EVT_L_LIM);
  pcnt_isr_service_install(0);
  pcnt_isr_handler_add(PCNT_ENC_UNIT, pcntOverflowISR, nullptr);
  pcnt_counter_resume(PCNT_ENC_UNIT);
}

// Runtime-calibrated PPC: set once via 'calibrate:<cm>' command, stored in EEPROM.
// When 0 (or invalid), getActivePpc() returns the formula value (PULSES_PER_CM).
static float calibratedPpc = 0.0f;
static long  calStartEncoder = 0;  // encoder snapshot at last resetpos — baseline for calibration


float caliperZeroOffset = 0.0;   // offset additivo (nome storico, EEPROM addr 0) — applicato anche a RazorGauge
float displayZeroValue = 0.0;    // con RazorGauge resta 0 (lo zero ottico è intrinseco)
int lastCm = -1;

// Encoder-diameter position correction accumulator.
// Each encoder-cm tick advances actualPositionCm by (C_eff/20) where
// C_eff = 20 - π × d_mm/10  (larger line diameter → smaller effective circumference → less actual travel).
float actualPositionCm = 0.0f;

// Encoder-based cm target kept for the GOTOPOS overshoot guard (raw encoder units).
float goToTargetEncoderCm = 0.0f;


unsigned long lastSpeedTime = 0;
long lastSpeedEncoder = 0;
float currentSpeed = 0.0;

WiFiManager wifiManager;
WebServer server(80);
WebSocketsServer webSocket(81);

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
//   gauge_stat [n]    ripetibilita: n misure consecutive (default 200) -> media, dev.std, min/max
// Pagina di servizio: http://<ip-del-master>/diag (grafico dei 128 pixel, indici di qualita, pulsanti).
// Dark, riferimento, esposizione e calibrazione sono salvati in NVS e
// ricaricati all'avvio: gauge_dark + gauge_ref vanno rifatti solo dopo
// interventi meccanici/ottici.
// =====================================================================

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

// Forward declarations
void handleCommand(String cmd);
void sendParamsToClients();
void calculateSpeed();
void addDataPoint(int cm, int encoderCm, float diameter, float rawDisplay);
void clearAllData();
int getTotalDataPoints();
void setDisplayZero();
void motorQueueTx(const String& lineNoNewline);
void motorPumpTx();
void motorPumpRx();
void motorPollIfNeeded();
void motorHandleStatusLine(const char* line);
void goToPosition(float targetCm);
void checkGoToStatus();

// Returns the active pulses-per-cm value: calibrated (from EEPROM) if valid, formula otherwise.
inline float getActivePpc() {
  return (calibratedPpc >= 5.0f && calibratedPpc <= 500.0f) ? calibratedPpc : (float)PULSES_PER_CM;
}

// -----------------------------
void addDataPoint(int cm, int encoderCm, float diameter, float rawDisplay) {
  DataPoint* newPoint = new DataPoint();
  if (!newPoint) { Serial.println("[OOM] DataPoint alloc failed"); return; }  // FW-11
  newPoint->cm = cm;
  newPoint->encoderCm = encoderCm;
  newPoint->diameter = roundf(diameter * 100.0f) / 100.0f;  // 0.01 mm: stesso formato di prima verso l'app WPF
  newPoint->rawDisplay = rawDisplay;
  newPoint->next = nullptr;

  if (firstDataPoint == nullptr) {
    firstDataPoint = newPoint;
    lastDataPoint = newPoint;
  } else {
    DataPoint* current = firstDataPoint;
    DataPoint* prev = nullptr;
    while (current != nullptr) {
      if (current->cm == cm) {
        current->diameter = newPoint->diameter;  // FW-04: use EMA-smoothed value, not raw
        current->rawDisplay = rawDisplay;
        delete newPoint;
        return;
      }
      if (current->cm > cm) {
        newPoint->next = current;
        if (prev == nullptr) firstDataPoint = newPoint;
        else prev->next = newPoint;
        totalDataPoints++;
        return;
      }
      prev = current;
      current = current->next;
    }
    lastDataPoint->next = newPoint;
    lastDataPoint = newPoint;
  }
  totalDataPoints++;
}

void clearAllData() {
  DataPoint* current = firstDataPoint;
  while (current != nullptr) {
    DataPoint* next = current->next;
    delete current;
    current = next;
  }
  firstDataPoint = nullptr;
  lastDataPoint = nullptr;
  totalDataPoints = 0;
  filterInitialized = false;
  smoothedDiameter = 0.0;
  actualPositionCm = 0.0f;
}

int getTotalDataPoints() {
  return totalDataPoints;
}



void motorQueueTx(const String& lineNoNewline) {
    // Drop low-priority messages if a real command is already waiting
    if (motorTxHasPending && lineNoNewline == "STATUS?") return;
    if (motorTxHasPending && lineNoNewline.startsWith("POS:")) return;
    if (motorTxHasPending && lineNoNewline.startsWith("SETHZ:")) return;  // speed trim — next one will get through
    motorTxPending = lineNoNewline + "\n";
    motorTxHasPending = true;
}

void motorPumpTx() {
  if (!motorTxHasPending) return;
  int freeBytes = SerialMotor.availableForWrite();
  if (freeBytes >= (int)motorTxPending.length()) {
    SerialMotor.print(motorTxPending);
    motorTxHasPending = false;
  }
}

void motorHandleStatusLine(const char* line) {
  if (strncmp(line, "STATUS:", 7) != 0) return;
  
  const char* p = line + 7;
  const char* colon = strchr(p, ':');
  if (!colon) return;
  
  String newMode = String(p).substring(0, colon - p);
  motorMode = newMode;

  // FW-12: parse direction field only (stop before the next colon that carries remaining steps)
  const char* dirStart = colon + 1;
  const char* colon2 = strchr(dirStart, ':');
  if (colon2) {
    motorDir = String(dirStart).substring(0, colon2 - dirStart);
  } else {
    motorDir = String(dirStart);
  }

  // Gestione GOTOPOS
  if (motorMode == "GOTOPOS") {
    isGoToActive = true;
    if (colon2) {
      int remaining = atoi(colon2 + 1);
      if (remaining == 0) {
        // FW-03: slave sent STATUS:GOTOPOS:DIR:0 before calling stopMotion() → confirmed arrival
        isGoToActive = false;
        scanEnabled = oldScanState;
        oldScanState = false;
        Serial.println("GOTOPOS completato!");
        // FW-13: broadcast restored scan state so clients stay in sync
        String scanJson = "{\"type\":\"scan_enabled\",\"value\":" + String(scanEnabled ? "true" : "false") + "}";
        webSocket.broadcastTXT(scanJson);
        float finalCm = (float)getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM;
        String json = "{\"type\":\"goto_status\",\"active\":false,\"completed\":true,\"final_cm\":" + String(finalCm, 1) + "}";
        webSocket.broadcastTXT(json);   // FIX 0.5.1: prima il messaggio veniva costruito ma mai inviato
        goToEncoderReached = false;
      } else {
        // Invia stato di avanzamento al client
        int currentCm = (int)floorf(getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM);
        int remainingCm = (int)(remaining / getActivePpc());
        String json = "{\"type\":\"goto_progress\",\"remaining_cm\":" + String(remainingCm) + 
                     ",\"current_cm\":" + String(currentCm) + ",\"target_cm\":" + String(goToTargetCm) + "}";
        webSocket.broadcastTXT(json);
      }
    }
  } else if (motorMode == "STOP") {
    if (isGoToActive) {
      isGoToActive = false;
      scanEnabled = oldScanState;
      oldScanState = false;
      // FW-13: broadcast restored scan state
      String scanJson = "{\"type\":\"scan_enabled\",\"value\":" + String(scanEnabled ? "true" : "false") + "}";
      webSocket.broadcastTXT(scanJson);
      // Use goToEncoderReached so encoder-based stops report completed:true
      float finalCm = (float)getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM;
      String json = "{\"type\":\"goto_status\",\"active\":false,\"completed\":" +
                    String(goToEncoderReached ? "true" : "false") + ",\"final_cm\":" + String(finalCm, 1) + ",\"reason\":\"stopped\"}";
      webSocket.broadcastTXT(json);
      goToEncoderReached = false;
    }
  }
  
  motorLastSeenMs = millis();
  String json = "{\"type\":\"motor\",\"mode\":\"" + motorMode + "\",\"dir\":\"" + motorDir + "\"}";
  webSocket.broadcastTXT(json);
}

void motorPumpRx() {
  while (SerialMotor.available() > 0) {
    char c = (char)SerialMotor.read();
    if (c == '\r') continue;
    if (c == '\n') {
      motorRxLine[motorRxLen] = '\0';
      if (motorRxLen > 0) motorHandleStatusLine(motorRxLine);
      motorRxLen = 0;
      continue;
    }
    if (motorRxLen < sizeof(motorRxLine) - 1) motorRxLine[motorRxLen++] = c;
    else motorRxLen = 0;
  }
}

void motorPollIfNeeded() {
  unsigned long now = millis();
  bool stale = (motorLastSeenMs == 0) || (now - motorLastSeenMs > MOTOR_STALE_MS);
  if (stale && (now - lastMotorPollMs > MOTOR_POLL_INTERVAL_MS)) {
    motorQueueTx("STATUS?");
    lastMotorPollMs = now;
    String json = "{\"type\":\"motor\",\"mode\":\"OFFLINE\",\"dir\":\"--\"}";
    webSocket.broadcastTXT(json);
  }
}

void checkGoToStatus() {
  if (!isGoToActive) return;
  
  unsigned long now = millis();
  if (now - lastGoToStatusCheck > 500) {  // Ogni 500ms
    lastGoToStatusCheck = now;
    motorQueueTx("STATUS?");
  }
}

// ----------------------------- GOTOPOS Function -----------------------------
void goToPosition(float targetCm) {
  if (isGoToActive) return;  // FW-08: prevent re-entrant call from WebSocket corrupting oldScanState
  if (targetCm < 0) {
    Serial.println("ERRORE: Target non valido");
    return;
  }

  float currentCm = (float)getEncoderValue() / getActivePpc() - MEAS_OFFSET_CM;  // encoder-based actual position
  
  // Se già a target
  if (abs(targetCm - currentCm) < 0.1) {
    Serial.println("Già alla posizione target");
    return;
  }

  // Salva stato scansione e sospendi
  oldScanState = scanEnabled;
  scanEnabled = false;
  // Notify all clients that scan is suspended (symmetric with restore broadcast on completion)
  webSocket.broadcastTXT("{\"type\":\"scan_enabled\",\"value\":false}");
  
  // Determina la direzione
  bool direction = (targetCm > currentCm);
  
  // Look up encoder-based position for the target actual-cm.
  // Scan data stores both: cm (actual, corrected) and encoderCm (raw encoder ticks / PULSES_PER_CM).
  // Default fallback: treat targetCm as encoder cm (works when no data or first use).
  float targetEncoderCm = targetCm;
  if (firstDataPoint != nullptr) {
    DataPoint* best = firstDataPoint;
    float bestDiff = abs((float)best->cm - targetCm);
    for (DataPoint* p = firstDataPoint->next; p != nullptr; p = p->next) {
      float diff = abs((float)p->cm - targetCm);
      if (diff < bestDiff) {
        bestDiff = diff;
        best = p;
      }
    }
    targetEncoderCm = (float)best->encoderCm;
    Serial.print("GOTOPOS lookup: actual ");
    Serial.print(targetCm, 1);
    Serial.print(" cm → encoder ");
    Serial.print(targetEncoderCm, 1);
    Serial.println(" cm");
  }

  // goToTargetEncoderCm is used by the overshoot guard (floatCm is encoder-based)
  goToTargetEncoderCm = targetEncoderCm;

  // Send GOTOPOS to slave. Add the encoder offset (encoder wheel is MEAS_OFFSET_CM behind the measuring point).
  long encNow = getEncoderValue();
  // 0.6.0: lo slave converte i cm ricevuti in impulsi con il valore NOMINALE (PULSES_PER_CM = 30) e li confronta con gli
  // impulsi reali dell'encoder che gli mandiamo: con un PPC calibrato diverso da 30 si fermava nel punto sbagliato.
  // Si inviano quindi "cm nominali" = impulsi di destinazione / 30 (identico a prima quando PPC = 30). Slave invariato.
  float slaveCm = (targetEncoderCm + MEAS_OFFSET_CM) * getActivePpc() / PULSES_PER_CM;
  String cmd = "GOTOPOS:" + String(slaveCm, 3) + ":" + String(MOTOR_FAST_HZ) + ":" + String(encNow) + ":" + (direction ? "F" : "B");
  motorQueueTx(cmd);
  
  goToTargetCm = targetCm;
  goToFwd = direction;
  isGoToActive = true;
  goToEncoderReached = false;
  lastGoToStatusCheck = 0;
  lastPosSentMs = 0;  // send first POS update immediately
  
  Serial.print("GOTOPOS avviato verso ");
  Serial.print(targetCm, 2);
  Serial.print(" cm (posizione attuale: ");
  Serial.print(currentCm, 2);
  Serial.println(" cm)");
  
  // Notifica il client web
  String json = "{\"type\":\"goto_status\",\"active\":true,\"target\":" + String(targetCm, 2) + 
                ",\"current\":" + String(currentCm, 2) + "}";
  webSocket.broadcastTXT(json);
}

// -----------------------------
void setup() {
  Serial.begin(115200);
  EEPROM.begin(EEPROM_SIZE);

  SerialMotor.begin(115200, SERIAL_8N1, MOTOR_UART_RX_PIN, MOTOR_UART_TX_PIN);
  motorQueueTx("STATUS?");

  pinMode(ENCODER_DATA_PIN, INPUT_PULLUP);
  pinMode(ENCODER_CLOCK_PIN, INPUT_PULLUP);

  setupPCNT();  // Hardware pulse counter for encoder — replaces software ISR
  gaugeSetup();  // RazorGauge: pin, ADC, NVS, task di acquisizione su core 0

  EEPROM.get(0, caliperZeroOffset);
  if (isnan(caliperZeroOffset)) caliperZeroOffset = 0.0;

  EEPROM.get(EEPROM_ADDR_CALIB_PPC, calibratedPpc);
  if (isnan(calibratedPpc) || calibratedPpc < 5.0f || calibratedPpc > 500.0f) calibratedPpc = 0.0f;
  // Align encoder init value to calibrated PPC so display starts at 0 cm
  setEncoderValue((long)ceilf(MEAS_OFFSET_CM * getActivePpc()));
  calStartEncoder = getEncoderValue();
  Serial.print("PPC attivo: ");
  Serial.println(getActivePpc(), 4);
  Serial.print("PCNT encoder HW attivo (ticks iniziali): ");
  Serial.println(getEncoderValue());

  lastSpeedTime = millis();
  lastSpeedEncoder = getEncoderValue();

  Serial.println("\n=== WiFi Manager v2.3.0 ===");
  pinMode(WIFI_RESET_PIN, INPUT_PULLUP);
  if (digitalRead(WIFI_RESET_PIN) == LOW) {
    Serial.println("Reset WiFi!");
    wifiManager.resetSettings();
    delay(1000);
  }
  wifiManager.setConfigPortalTimeout(180);
  wifiManager.setAPCallback([](WiFiManager* m) {
    Serial.println("AP: " + String(m->getConfigPortalSSID()));
    Serial.println("Pwd: 12345678 | IP: 192.168.4.1");
  });
  if (!wifiManager.autoConnect("DiametroLinea_Setup", "12345678")) {
    Serial.println("Timeout!");
    delay(3000);
    ESP.restart();
  }
  Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());


  // UI web rimossa (sostituita dall'app WPF). Restano solo gli endpoint dati /export e /encoder,
  // che non fanno parte dell'interfaccia ma potrebbero essere usati da strumenti esterni.
  server.on("/export", HTTP_GET, []() {
    server.setContentLength(CONTENT_LENGTH_UNKNOWN);
    server.sendHeader("Content-Disposition", "attachment; filename=diametrolinea.csv");
    server.sendHeader("Cache-Control", "no-store");
    server.send(200, "text/csv", "");
    server.sendContent("Lunghezza cm,Diametro mm\r\n");
    char line[64];
    int n = 0;
    for (DataPoint* cur = firstDataPoint; cur != nullptr; cur = cur->next) {
      snprintf(line, sizeof(line), "%d,%.2f\r\n", cur->cm, cur->diameter);
      server.sendContent(line);
      if ((++n % 50) == 0) delay(1);
      else delay(0);
    }
  });

  server.on("/encoder", HTTP_GET, []() {
    long enc = getEncoderValue();
    float cm  = (float)enc / getActivePpc() - MEAS_OFFSET_CM;
    int16_t hwCount = 0;
    pcnt_get_counter_value(PCNT_ENC_UNIT, &hwCount);
    String json = "{\"ticks\":" + String(enc) +
                  ",\"pcntAccum\":" + String(pcntAccum) +
                  ",\"hwCounter\":" + String(hwCount) +
                  ",\"ppc\":" + String(getActivePpc(), 4) +
                  ",\"cm\":" + String(cm, 2) +
                  ",\"scanEnabled\":" + String(scanEnabled ? "true" : "false") +
                  ",\"totalPoints\":" + String(getTotalDataPoints()) + "}";
    server.send(200, "application/json", json);
  });

  gaugeHttpSetup();   // RazorGauge: /diag (pagina di servizio) e /gauge (dati JSON) — non toccano l'app WPF
  server.begin();

  webSocket.begin();
  webSocket.onEvent([](uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
    if (type == WStype_TEXT) {
      String cmd = String((char*)payload);
      gCmdClient = num;  // per le risposte dei comandi gauge_* (solo a chi li invia)
      if (cmd == "getparams") {
        String json = "{\"type\":\"params\",\"displayZero\":" + String(displayZeroValue, 2) + ",\"offset\":" + String(caliperZeroOffset, 2) + ",\"ppc\":" + String(getActivePpc(), 4) + ",\"ppcCalibrated\":" + String((calibratedPpc >= 5.0f && calibratedPpc <= 500.0f) ? "true" : "false") + "}";
        webSocket.sendTXT(num, json);
      } else {
        handleCommand(cmd);
      }
      gCmdClient = -1;
    } else if (type == WStype_CONNECTED) {
      String json = "{\"type\":\"params\",\"displayZero\":" + String(displayZeroValue, 2) + ",\"offset\":" + String(caliperZeroOffset, 2) + ",\"ppc\":" + String(getActivePpc(), 4) + ",\"ppcCalibrated\":" + String((calibratedPpc >= 5.0f && calibratedPpc <= 500.0f) ? "true" : "false") + "}";
      webSocket.sendTXT(num, json);
      String scanJson = "{\"type\":\"scan_enabled\",\"value\":" + String(scanEnabled ? "true" : "false") + "}";
      webSocket.sendTXT(num, scanJson);
    }
  });

  Serial.println("Sistema pronto - RazorGauge (misura ottica a ombra)");
  Serial.println("cm,diametro_compensato,display_gauge");
}

// -----------------------------
void calculateSpeed() {
  unsigned long currentTime = millis();
  if (currentTime - lastSpeedTime >= 1000) {
    int encoderDiff = getEncoderValue() - lastSpeedEncoder;
    currentSpeed = abs(encoderDiff / getActivePpc());
    lastSpeedEncoder = getEncoderValue();
    lastSpeedTime = currentTime;
    String json = "{\"type\":\"speed\",\"speed\":" + String(currentSpeed, 2) + "}";
    webSocket.broadcastTXT(json);

    // Closed-loop scan speed control: compensates for spool diameter growth.
    // Sends SETHZ:<hz> to slave proportionally — runs every second.
    if (scanEnabled && !isGoToActive && currentSpeed > 0.1f) {
      float ratio = TARGET_SCAN_SPEED_CMS / currentSpeed;
      uint32_t newHz = (uint32_t)constrain((float)currentScanHz * ratio, (float)SCAN_HZ_MIN, (float)SCAN_HZ_MAX);
      if (abs((int32_t)newHz - (int32_t)currentScanHz) > 10) {
        currentScanHz = newHz;
        motorQueueTx("SETHZ:" + String(currentScanHz));
      }
    }
  }
}

void sendParamsToClients() {
  String json = "{\"type\":\"params\",\"displayZero\":" + String(displayZeroValue, 2) + 
                ",\"offset\":" + String(caliperZeroOffset, 2) +
                ",\"ppc\":" + String(getActivePpc(), 4) +
                ",\"ppcCalibrated\":" + String((calibratedPpc >= 5.0f && calibratedPpc <= 500.0f) ? "true" : "false") +
                "}";
  webSocket.broadcastTXT(json);
}

// -----------------------------
void loop() {
  server.handleClient();
  webSocket.loop();

  gaugePollRequest();  // consegna i risultati dei comandi gauge_* (l'acquisizione gira nel suo task)
  motorPumpRx();
  motorPollIfNeeded();
  motorPumpTx();
  checkGoToStatus();

  calculateSpeed();

  // FW-09: single consistent snapshot of hardware encoder for this iteration
  long encSnap = getEncoderValue();

  // Watchdog encoder: auto-stop motore dopo 5s fermo
  {
    unsigned long now = millis();
    if (encSnap != encoderLastValueForWatchdog) {
      encoderLastValueForWatchdog = encSnap;
      encoderLastMoveMs = now;
      encoderWatchdogStopSent = false;
    } else if (!isGoToActive && !encoderWatchdogStopSent && encoderLastMoveMs > 0 && (now - encoderLastMoveMs >= 5000)) {
      // FW-10: watchdog suppressed during GOTOPOS (slow final approach looks like no movement)
      motorQueueTx("STOP");
      encoderWatchdogStopSent = true;
      Serial.println("Watchdog: encoder fermo da 5s, motore STOP");
    }
  }

  int currentCm = (int)floorf(encSnap / getActivePpc() - MEAS_OFFSET_CM);

  // Acquisizione dati solo se scansione abilitata e NON in GOTOPOS
  if (!isGoToActive && currentCm != lastCm && currentCm >= 0 && scanEnabled) {
    lastCm = currentCm;

    float displayValue = gaugeReadDisplay();   // mediana del buffer RazorGauge, calibrata; NAN = nessun cavo

    float compensatedDiameter = displayValue - displayZeroValue - caliperZeroOffset;
    compensatedDiameter = roundf(compensatedDiameter * 100.0f) / 100.0f;  // 0.01 mm precision
    // Guard: NaN/Inf in JSON silently breaks JSON.parse in the browser
    if (!isfinite(compensatedDiameter)) compensatedDiameter = 0.0f;
    if (!isfinite(displayValue))        displayValue        = 0.0f;

    // Use encoder position directly: PCNT is hardware-accurate (0.28% error),
    // and using currentCm avoids phantom counts from line oscillation/bounce.
    int actualCm = currentCm;

    addDataPoint(actualCm, currentCm, compensatedDiameter, displayValue);

    String json = "{\"cm\":" + String(actualCm) + ",\"diameter\":" + String(compensatedDiameter, 2) + 
                  ",\"rawDisplay\":" + String(displayValue, 2) + ",\"totalPoints\":" + String(getTotalDataPoints()) + "}";
    webSocket.broadcastTXT(json);

    Serial.print(actualCm);
    Serial.print(",");
    Serial.print(compensatedDiameter, 2);
    Serial.print(",");
    Serial.println(displayValue, 2);
  } else if (isGoToActive) {
    float floatCm = (float)encSnap / getActivePpc() - MEAS_OFFSET_CM;

    // Safety-only overshoot guard: if encoder went MORE than 1 cm past target, force stop.
    // Under normal operation the slave's natural deceleration stops the motor before this fires.
    if (!goToEncoderReached && (goToFwd ? (floatCm > goToTargetEncoderCm + 1.0f) : (floatCm < goToTargetEncoderCm - 1.0f))) {
      goToEncoderReached = true;
      motorQueueTx("STOP");
      Serial.println("⚠ GOTOPOS: overshoot safety stop");
    }

    // Stream encoder position to slave every 100 ms so slave uses encoder
    // (not its own step counter) for dynamic speed and stop detection
    {
      unsigned long nowMs = millis();
      if (nowMs - lastPosSentMs >= 100) {
        lastPosSentMs = nowMs;
        motorQueueTx("POS:" + String(encSnap));
      }
    }

    // Aggiorna solo la posizione durante GOTOPOS
    if (currentCm != lastCm) {
      lastCm = currentCm;
      String json = "{\"cm\":" + String(currentCm) + "}";
      webSocket.broadcastTXT(json);
    }
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    handleCommand(cmd);
  }
}


// -----------------------------
void handleCommand(String cmd) {
  if (gaugeHandleCommand(cmd)) return;   // comandi gauge_* (RazorGauge)

  if (cmd.startsWith("goto ")) {
    float target = cmd.substring(5).toFloat();
    goToPosition(target);
    return;
  }

  if (cmd.startsWith("motor")) {
    String arg = cmd;
    arg.replace("motor", "");
    arg.trim();
    arg.toLowerCase();
    if (arg == "scan") { currentScanHz = SCAN_HZ_INIT; motorQueueTx("SCAN"); }
    else if (arg == "stop") motorQueueTx("STOP");
    else if (arg == "fast_s") motorQueueTx("FAST_S");
    else if (arg == "fast_o") motorQueueTx("FAST_O");
    else motorQueueTx("STATUS?");
    return;
  }

  if (cmd == "help") {
    Serial.println("Comandi disponibili:");
    Serial.println("  reset               - Azzera lunghezza encoder e dati");
    Serial.println("  resetpos            - Azzera solo posizione (non i dati)");
    Serial.println("  calibrate:<cm>      - Calibra PPC: dopo resetpos, estrai <cm> di linea, poi invia questo comando");
    Serial.println("  setppc:<val>        - Imposta PPC manualmente (es: setppc:31.25) e salva in EEPROM");
    Serial.println("  calibrate_reset     - Ripristina PPC alla formula (cancella calibrazione)");
    Serial.println("  goto <cm>           - Vai alla posizione specificata in cm");
    Serial.println("  setoffset <val>     - Imposta offset di compensazione");
    Serial.println("  setdisplayzero      - (RazorGauge) non necessario: azzera lo zero display a 0");
    Serial.println("  readraw             - Mostra la lettura attuale di RazorGauge");
    Serial.println("  readenc             - Mostra tick PCNT, pcntAccum e posizione calcolata (debug)");
    Serial.println("  resetoffset         - Azzera offset a 0");
    Serial.println("  getparams           - Mostra parametri correnti");
    Serial.println("  debugdata           - Mostra statistiche dati");
    Serial.println("  resetwifi           - Reset WiFi");
    Serial.println("  scan_on / scan_off  - Abilita/disabilita ricezione punti");
    Serial.println("  motor scan|stop|fast_s|fast_o|status");
    Serial.println("  gauge_dark | gauge_ref | gauge_cal <mm> | gauge_calreset | gauge_exp <us> | gauge_status | gauge_profile");
    return;
  }

  if (cmd.startsWith("setoffset ")) {
    caliperZeroOffset = cmd.substring(10).toFloat();
    EEPROM.put(0, caliperZeroOffset);
    EEPROM.commit();
    Serial.print("Offset impostato a: ");
    Serial.println(caliperZeroOffset, 6);
    sendParamsToClients();
    return;
  }

  if (cmd == "setdisplayzero") {
    setDisplayZero();
    return;
  }

  if (cmd == "scan_on") {
    if (!isGoToActive) {
      scanEnabled = true;
      String json = "{\"type\":\"scan_enabled\",\"value\":true}";
      webSocket.broadcastTXT(json);
      Serial.println("Scansione ABILITATA");
    } else {
      Serial.println("Impossibile abilitare scansione durante GOTOPOS");
    }
    return;
  }

  if (cmd == "scan_off") {
    scanEnabled = false;
    String json = "{\"type\":\"scan_enabled\",\"value\":false}";
    webSocket.broadcastTXT(json);
    Serial.println("Scansione DISABILITATA");
    return;
  }

  if (cmd == "reset") {
    // Set encoder so the measuring-point position reads 0: encoder/activePpc - MEAS_OFFSET_CM = 0
    setEncoderValue((long)ceilf(MEAS_OFFSET_CM * getActivePpc()));
    lastCm = -1;
    clearAllData();
    Serial.println("Lunghezza azzerata e dati resettati.");
    return;
  }

  if (cmd == "resetpos") {
    // Reset only the encoder position (display → 0); does NOT clear measurement data.
    setEncoderValue((long)ceilf(MEAS_OFFSET_CM * getActivePpc()));
    calStartEncoder = getEncoderValue();  // mark baseline for next calibration run
    lastCm = -1;
    actualPositionCm = 0.0f;
    Serial.println("Posizione azzerata.");
    sendParamsToClients();
    return;
  }

  if (cmd == "readraw") {
    float display = gaugeReadDisplay();
    Serial.print("Display RazorGauge: ");
    if (isfinite(display)) Serial.println(display, 4); else Serial.println("nessun cavo / sensore non pronto");
    return;
  }

  if (cmd == "readenc") {
    long enc = getEncoderValue();
    float cm = (float)enc / getActivePpc() - MEAS_OFFSET_CM;
    int16_t hwCount = 0;
    pcnt_get_counter_value(PCNT_ENC_UNIT, &hwCount);
    Serial.print("Encoder ticks totali: "); Serial.println(enc);
    Serial.print("  pcntAccum: ");          Serial.println(pcntAccum);
    Serial.print("  PCNT HW counter: ");    Serial.println(hwCount);
    Serial.print("  PPC attivo: ");         Serial.println(getActivePpc(), 4);
    Serial.print("  Posizione calcolata: "); Serial.print(cm, 2); Serial.println(" cm");
    return;
  }

  // calibrate:<cm>  — compute actual PPC from encoder delta since last resetpos.
  // Workflow: (1) send resetpos, (2) pull EXACTLY <cm> of line, (3) send calibrate:<cm>.
  // Stores result in EEPROM; survives reboot. Formula value used until first calibration.
  if (cmd.startsWith("calibrate:")) {
    float knownCm = cmd.substring(10).toFloat();
    if (knownCm < 1.0f) {
      Serial.println("calibrate: lunghezza troppo piccola (minimo 1 cm)");
      return;
    }
    long delta = getEncoderValue() - calStartEncoder;
    if (delta <= 0) {
      Serial.println("calibrate: encoder non avanzato. Premi resetpos prima di estrarre la linea.");
      return;
    }
    calibratedPpc = (float)delta / knownCm;
    EEPROM.put(EEPROM_ADDR_CALIB_PPC, calibratedPpc);
    EEPROM.commit();
    Serial.print("PPC calibrato: ");
    Serial.print(calibratedPpc, 4);
    Serial.print(" (delta=");
    Serial.print(delta);
    Serial.print(" ticks / ");
    Serial.print(knownCm, 1);
    Serial.println(" cm)");
    sendParamsToClients();
    return;
  }

  // setppc:<value>  — manually set PPC and save to EEPROM (e.g. setppc:31.25)
  if (cmd.startsWith("setppc:")) {
    float val = cmd.substring(7).toFloat();
    if (val < 5.0f || val > 500.0f) {
      Serial.println("setppc: valore fuori range (5–500)");
      return;
    }
    calibratedPpc = val;
    EEPROM.put(EEPROM_ADDR_CALIB_PPC, calibratedPpc);
    EEPROM.commit();
    Serial.print("PPC impostato manualmente: ");
    Serial.println(calibratedPpc, 4);
    sendParamsToClients();
    return;
  }

  if (cmd == "calibrate_reset") {
    calibratedPpc = 0.0f;
    EEPROM.put(EEPROM_ADDR_CALIB_PPC, calibratedPpc);
    EEPROM.commit();
    Serial.print("PPC resettato alla formula: ");
    Serial.println(getActivePpc(), 4);
    sendParamsToClients();
    return;
  }

  if (cmd == "resetoffset") {
    caliperZeroOffset = 0.0;
    EEPROM.put(0, caliperZeroOffset);
    EEPROM.commit();
    Serial.println("Offset azzerato.");
    sendParamsToClients();
    return;
  }

  if (cmd == "getparams") {
    Serial.print("Parametri correnti - Zero Display: ");
    Serial.print(displayZeroValue, 2);
    Serial.print(" mm, Offset: ");
    Serial.println(caliperZeroOffset, 6);
    return;
  }

  if (cmd == "debugdata") {
    Serial.print("Punti dati totali: ");
    Serial.println(getTotalDataPoints());
    return;
  }

  if (cmd == "resetwifi") {
    Serial.println("Reset WiFi...");
    wifiManager.resetSettings();
    delay(1000);
    ESP.restart();
    return;
  }
}

// -----------------------------
void setDisplayZero() {
  // Con il calibro serviva a registrare la lettura a ganasce chiuse. Con RazorGauge lo zero è
  // intrinseco (nessuna ombra = 0 mm): il comando resta accettato per compatibilità con l'app
  // WPF e riporta lo zero display a 0. Le correzioni fini si fanno con gauge_cal / setoffset.
  displayZeroValue = 0.0f;
  Serial.print("Zero display (RazorGauge) impostato a: ");
  Serial.println(displayZeroValue, 2);
  sendParamsToClients();
}