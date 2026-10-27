/*
  RazorGauge - prova del sensore CCD TSL1401 con mappa dei pixel sul display
  Hiwonder CCD Module TSL1401 V1.0 + ESP-WROVER-KIT v4.1 (LCD 320x240 ILI9341 o ST7789V;
  quello provato il 26/10/2026 è un ILI9341, riconosciuto in automatico)
  Board Arduino: "ESP32 Wrover Kit (all versions)"  (esp32:esp32:esp32wroverkit)

  COLLEGAMENTI (stessi pin di ccd_test e del master; liberi se la fotocamera NON è montata)
    Modulo VCC -> 3V3     (NON 5V: AO supererebbe il range dell'ADC)
    Modulo GND -> GND
    Modulo SI  -> GPIO26
    Modulo CLK -> GPIO27
    Modulo AO  -> GPIO34  (ADC1: funziona anche col WiFi)
  Il display è già cablato sulla scheda: SCK 19, MOSI 23, MISO 25, CS 22, DC 21, RST 18, BL 5.

  SCHERMO
    in alto    integrazione, fps, min/max/media sui pixel validi, ombra trovata
    grafico    un'asta per pixel (2 px ciascuno), colore = livello; rosso = saturo,
               fondo scuro = pixel morti 0..PIX_FIRST-1, linee gialle = bordi dell'ombra
    striscia   la mappa dei 128 pixel nel frame attuale
    cascata    gli ultimi 66 frame, il più recente in alto: un pixel morto è una colonna nera fissa
  Tasto BOOT: congela / riprende l'immagine.

  COMANDI SERIALI (115200, terminatore newline)
    t <us>     tempo d'integrazione (1 .. 200000 us), spegne l'automatico; l'effettiva
               aggiunge i clock di svuotamento + 20 µs (la stampa ?)
    e          esposizione automatica on/off (picco ~3000)
    k          scala verticale: assoluta 0..4095 / automatica sul massimo
    h          congela / riprende
    w          dump dei 128 valori raw del frame mostrato
    L          controller del display: auto / ILI9341 / ST7789 (salvato)
    r          ruota / specchia l'immagine (salvato)
    b          scambia rosso e blu (salvato)
    i          inverte i colori (salvato)
    ?          aiuto
*/

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Preferences.h>

const int PIN_SI  = 26;
const int PIN_CLK = 27;
const int PIN_AO  = 34;
const int PIN_BOOT = 0;

const int LCD_SCK = 19, LCD_MOSI = 23, LCD_MISO = 25;
const int LCD_CS = 22, LCD_DC = 21, LCD_RST = 18, LCD_BL = 5;   // BL attivo basso sulla v4.1
const uint32_t LCD_HZ = 40000000;

const int NPIX = 128;
const int ADC_SAT = 4000;
const int PIX_FIRST = 16;     // 0..13 morti su questo sensore (vedi STATO_PROGETTO 25/10): come G_PIX_FIRST del master
const int PIX_LAST  = 125;
const float PIX_MM  = 0.0635f;

// Disposizione dello schermo 320x240
const int W = 320, H = 240;
const int PX0 = 32;                    // x del pixel 0, 2 px di larghezza per pixel
const int PLOT_Y = 34, PLOT_H = 110;
const int LBL_Y = 146;
const int STRIP_Y = 156, STRIP_H = 16;
const int WF_Y = 174, WF_H = H - WF_Y;

uint16_t buf[NPIX];
uint32_t integUs = 5000;
const uint32_t INTEG_MIN = 1, INTEG_MAX = 200000;   // attesa richiesta; l'effettiva è in lastEff
uint32_t lastEff = 0;
uint32_t tIntStart = 0, tIntEnd = 0;
bool autoExp = true, autoScale = false, hold = false;
float fps = 0;

SPIClass lcdSpi(VSPI);
GFXcanvas16 *cv = nullptr;
Preferences prefs;
uint16_t cmap[256];

// Impostazioni del display: il kit monta ILI9341 o ST7789V a seconda del lotto
enum { CTL_AUTO, CTL_ILI, CTL_ST };
const char *CTL_NAME[] = {"auto", "ILI9341", "ST7789"};
const uint8_t MADCTL_ROT[] = {0x20, 0xE0, 0x60, 0xA0};   // MV (orizzontale) + specchiature MX/MY
int ctlPref = CTL_AUTO, ctl = CTL_ILI;
int rot = 0, bgr = -1, inv = -1;       // -1 = predefinito del controller

// ---------------------------------------------------------------- sensore

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

// Svuota il sensore con i soli clock, senza ADC: pochi µs invece dei ~5.5 ms di readFrame,
// così l'integrazione minima scende a qualche decina di µs (laser acceso fisso sul banco)
void flushFrame() {
  digitalWrite(PIN_SI, HIGH);
  digitalWrite(PIN_CLK, HIGH);
  digitalWrite(PIN_SI, LOW);
  for (int i = 0; i < NPIX; i++) {
    digitalWrite(PIN_CLK, LOW);
    digitalWrite(PIN_CLK, HIGH);
    if (i == 17) tIntStart = micros();
  }
  digitalWrite(PIN_CLK, LOW);
  delayMicroseconds(20);
}

// Scarica il sensore, aspetta, legge: ritorna l'integrazione effettiva in µs
uint32_t capture(uint16_t *b, uint32_t us) {
  flushFrame();
  uint32_t start = tIntStart;
  uint32_t t0 = micros();
  while (micros() - t0 < us) {}
  readFrame(b);
  return tIntEnd - start;
}

struct Stats { int mn, mx, imn, imx; float mean; int nSat; };
Stats stats(const uint16_t *b);   // prototipo esplicito: quello generato da Arduino finirebbe prima della struct

// Solo sui pixel validi: i morti tirerebbero il minimo a 0
Stats stats(const uint16_t *b) {
  Stats s = {4096, -1, 0, 0, 0, 0};
  for (int i = PIX_FIRST; i <= PIX_LAST; i++) {
    if (b[i] < s.mn) { s.mn = b[i]; s.imn = i; }
    if (b[i] > s.mx) { s.mx = b[i]; s.imx = i; }
    if (b[i] >= ADC_SAT) s.nSat++;
    s.mean += b[i];
  }
  s.mean /= PIX_LAST - PIX_FIRST + 1;
  return s;
}

// Ombra = tratto più lungo sotto la soglia a metà fra min e max, bordi interpolati
struct Shadow { bool ok; float xl, xr; bool cutL, cutR; int thr; };
Shadow shadow(const uint16_t *b, const Stats &s);
int scaleMax(const Stats &s);
void drawFrame(const Stats &s, const Shadow &sh, uint32_t eff);
void adjustExposure(const Stats &s);

Shadow shadow(const uint16_t *b, const Stats &s) {
  Shadow sh = {false, 0, 0, false, false, (s.mn + s.mx) / 2};
  if (s.mx - s.mn < 200) return sh;
  int best0 = -1, bestN = 0;
  for (int i = PIX_FIRST; i <= PIX_LAST; ) {
    if (b[i] >= sh.thr) { i++; continue; }
    int j = i;
    while (j <= PIX_LAST && b[j] < sh.thr) j++;
    if (j - i > bestN) { bestN = j - i; best0 = i; }
    i = j;
  }
  if (best0 < 0) return sh;
  int i0 = best0, i1 = best0 + bestN - 1;
  sh.cutL = i0 == PIX_FIRST;
  sh.cutR = i1 == PIX_LAST;
  sh.xl = sh.cutL ? i0 : (i0 - 1) + float(b[i0 - 1] - sh.thr) / (b[i0 - 1] - b[i0]);
  sh.xr = sh.cutR ? i1 : i1 + float(b[i1] - sh.thr) / (b[i1] - b[i1 + 1]);
  sh.ok = true;
  return sh;
}

// ---------------------------------------------------------------- display

void lcdBegin() {
  lcdSpi.beginTransaction(SPISettings(LCD_HZ, MSBFIRST, SPI_MODE0));
  digitalWrite(LCD_CS, LOW);
}
void lcdEnd() {
  digitalWrite(LCD_CS, HIGH);
  lcdSpi.endTransaction();
}
void lcdCmdNL(uint8_t c) {
  digitalWrite(LCD_DC, LOW);
  lcdSpi.write(c);
  digitalWrite(LCD_DC, HIGH);
}
void lcdSend(uint8_t c, const uint8_t *d = nullptr, int n = 0) {
  lcdBegin();
  lcdCmdNL(c);
  if (n) lcdSpi.writeBytes(d, n);
  lcdEnd();
}
void lcdSend1(uint8_t c, uint8_t v) { lcdSend(c, &v, 1); }

uint32_t lcdRead32(uint8_t c) {
  lcdSpi.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  digitalWrite(LCD_CS, LOW);
  lcdCmdNL(c);
  uint32_t id = 0;
  for (int i = 0; i < 4; i++) id = (id << 8) | lcdSpi.transfer(0);
  lcdEnd();
  return id;
}

// Lo ST7789V risponde 85 85 52 a RDDID (04), dopo un bit di attesa: lo cerco a ogni allineamento.
// L'ILI9341 del kit v4.1 risponde 0 sia a 04 sia a D3, quindi è la scelta di ripiego.
bool lcdIsIli() {
  uint32_t id = lcdRead32(0x04), d3 = lcdRead32(0xD3);
  Serial.printf("LCD RDDID = %08lX  ID4 = %08lX\n", (unsigned long)id, (unsigned long)d3);
  if ((d3 & 0xFFFF) == 0x9341) return true;
  for (int sh = 0; sh <= 8; sh++)
    if (((id >> sh) & 0xFFFFFF) == 0x858552) return false;
  return true;
}

// Sequenza di Adafruit_ILI9341 senza MADCTL/SLPOUT/DISPON, mandati dopo
const uint8_t ILI_INIT[] = {
  0xEF, 3, 0x03, 0x80, 0x02,
  0xCF, 3, 0x00, 0xC1, 0x30,
  0xED, 4, 0x64, 0x03, 0x12, 0x81,
  0xE8, 3, 0x85, 0x00, 0x78,
  0xCB, 5, 0x39, 0x2C, 0x00, 0x34, 0x02,
  0xF7, 1, 0x20,
  0xEA, 2, 0x00, 0x00,
  0xC0, 1, 0x23,
  0xC1, 1, 0x10,
  0xC5, 2, 0x3E, 0x28,
  0xC7, 1, 0x86,
  0x37, 1, 0x00,
  0x3A, 1, 0x55,
  0xB1, 2, 0x00, 0x18,
  0xB6, 3, 0x08, 0x82, 0x27,
  0xF2, 1, 0x00,
  0x26, 1, 0x01,
  0xE0, 15, 0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00,
  0xE1, 15, 0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F,
  0x00
};

void lcdApplyMode() {
  bool b = bgr < 0 ? ctl == CTL_ILI : bgr;
  bool v = inv < 0 ? false : inv;
  lcdSend1(0x36, MADCTL_ROT[rot] | (b ? 0x08 : 0x00));
  lcdSend(v ? 0x21 : 0x20);
}

void lcdInit() {
  digitalWrite(LCD_RST, LOW);  delay(20);
  digitalWrite(LCD_RST, HIGH); delay(150);
  lcdSend(0x01); delay(150);                  // reset software
  ctl = ctlPref != CTL_AUTO ? ctlPref : (lcdIsIli() ? CTL_ILI : CTL_ST);
  if (ctl == CTL_ILI) {
    for (const uint8_t *p = ILI_INIT; *p; ) {
      uint8_t c = *p++, n = *p++;
      lcdSend(c, p, n);
      p += n;
    }
  } else {
    lcdSend1(0x3A, 0x55);                     // 16 bit/pixel
  }
  lcdSend(0x11); delay(120);                  // fuori dallo sleep
  lcdApplyMode();
  lcdSend(0x29);                              // display acceso
  Serial.printf("Display %s (%s)  rot %d  bgr %d  inv %d\n", CTL_NAME[ctl],
                ctlPref == CTL_AUTO ? "rilevato" : "forzato", rot, bgr, inv);
}

void lcdPush() {
  uint8_t ca[] = {0, 0, (W - 1) >> 8, (W - 1) & 0xFF};
  uint8_t ra[] = {0, 0, (H - 1) >> 8, (H - 1) & 0xFF};
  lcdBegin();
  lcdCmdNL(0x2A); lcdSpi.writeBytes(ca, 4);
  lcdCmdNL(0x2B); lcdSpi.writeBytes(ra, 4);
  lcdCmdNL(0x2C);
  lcdSpi.writePixels(cv->getBuffer(), W * H * 2);   // scambia i byte: il display vuole big-endian
  lcdEnd();
}

void loadPrefs() {
  prefs.begin("ccdlcd", true);
  ctlPref = prefs.getInt("ctl", CTL_AUTO);
  rot = prefs.getInt("rot", 0);
  bgr = prefs.getInt("bgr", -1);
  inv = prefs.getInt("inv", -1);
  prefs.end();
}
void savePrefs() {
  prefs.begin("ccdlcd", false);
  prefs.putInt("ctl", ctlPref);
  prefs.putInt("rot", rot);
  prefs.putInt("bgr", bgr);
  prefs.putInt("inv", inv);
  prefs.end();
}

// ---------------------------------------------------------------- disegno

// Scala tipo "inferno": nero -> viola -> rosso -> arancio -> giallo chiaro
void buildCmap() {
  const uint8_t st[5][3] = {{0, 0, 4}, {87, 16, 110}, {188, 55, 84}, {249, 142, 9}, {252, 255, 164}};
  for (int i = 0; i < 256; i++) {
    float f = i / 255.0f * 4;
    int k = min(int(f), 3);
    float u = f - k;
    uint8_t c[3];
    for (int j = 0; j < 3; j++) c[j] = st[k][j] + (st[k + 1][j] - st[k][j]) * u;
    cmap[i] = ((c[0] & 0xF8) << 8) | ((c[1] & 0xFC) << 3) | (c[2] >> 3);
  }
}

int scaleMax(const Stats &s) {
  return autoScale ? max(256, int(s.mx * 1.1f)) : 4095;
}
uint16_t colorOf(int v, int top) {
  return cmap[constrain(v * 255 / top, 0, 255)];
}

void drawFrame(const Stats &s, const Shadow &sh, uint32_t eff) {
  const uint16_t BG = 0x0000, GRID = 0x2945, TXT = 0xFFFF, DIM = 0x8410;
  const uint16_t RED = 0xF800, YEL = 0xFFE0, DEAD = 0x3000;
  int top = scaleMax(s);

  // Testata
  cv->fillRect(0, 0, W, PLOT_Y, BG);
  cv->setTextSize(1);
  cv->setTextColor(TXT, BG);
  cv->setCursor(2, 2);
  cv->printf("TSL1401  int %lu us %s  %4.1f fps  %s", (unsigned long)eff,
             autoExp ? "AUTO" : "fisso", fps, autoScale ? "scala auto" : "scala 4095");
  if (hold) { cv->setTextColor(YEL, BG); cv->print("  FERMO"); cv->setTextColor(TXT, BG); }
  cv->setCursor(2, 12);
  cv->printf("min %4d@%3d  max %4d@%3d  media %6.1f", s.mn, s.imn, s.mx, s.imx, s.mean);
  if (s.nSat) { cv->setTextColor(RED, BG); cv->printf("  SATURI %d", s.nSat); }
  cv->setCursor(2, 22);
  if (sh.ok) {
    float w = sh.xr - sh.xl;
    cv->setTextColor(YEL, BG);
    cv->printf("ombra %6.2f..%6.2f  L %5.2f px = %5.3f mm  c %6.2f%s", sh.xl, sh.xr, w, w * PIX_MM,
               (sh.xl + sh.xr) / 2, sh.cutL || sh.cutR ? "  TAGLIATA" : "");
  } else {
    cv->setTextColor(DIM, BG);
    cv->print("ombra: nessuna (contrasto < 200)");
  }

  // Grafico
  cv->fillRect(0, PLOT_Y, W, LBL_Y + 8 - PLOT_Y, BG);
  cv->fillRect(PX0, PLOT_Y, PIX_FIRST * 2, PLOT_H, DEAD);
  cv->fillRect(PX0 + (PIX_LAST + 1) * 2, PLOT_Y, (NPIX - 1 - PIX_LAST) * 2, PLOT_H, DEAD);
  for (int q = 0; q <= 4; q++) cv->drawFastHLine(PX0, PLOT_Y + PLOT_H - 1 - q * (PLOT_H - 1) / 4, NPIX * 2, GRID);
  for (int p = 32; p < NPIX; p += 32) cv->drawFastVLine(PX0 + p * 2, PLOT_Y, PLOT_H, GRID);
  for (int i = 0; i < NPIX; i++) {
    int h = min(PLOT_H, buf[i] * PLOT_H / top);
    uint16_t c = buf[i] >= ADC_SAT ? RED : colorOf(buf[i], top);
    if (h) cv->fillRect(PX0 + i * 2, PLOT_Y + PLOT_H - h, 2, h, c);
  }
  if (sh.ok) {
    int yt = PLOT_Y + PLOT_H - 1 - min(PLOT_H - 1, sh.thr * PLOT_H / top);
    for (int x = PX0; x < PX0 + NPIX * 2; x += 4) cv->drawPixel(x, yt, YEL);
    cv->drawFastVLine(PX0 + int(sh.xl * 2 + 1), PLOT_Y, PLOT_H, YEL);
    cv->drawFastVLine(PX0 + int(sh.xr * 2 + 1), PLOT_Y, PLOT_H, YEL);
  }
  cv->setTextColor(DIM, BG);
  cv->setCursor(0, PLOT_Y);                 cv->printf("%4d", top);
  cv->setCursor(0, PLOT_Y + PLOT_H / 2 - 4); cv->printf("%4d", top / 2);
  cv->setCursor(0, PLOT_Y + PLOT_H - 8);    cv->print("   0");
  for (int p = 0; p < NPIX; p += 32) { cv->setCursor(PX0 + p * 2, LBL_Y); cv->print(p); }
  cv->setCursor(PX0 + NPIX * 2 - 18, LBL_Y); cv->print("127");
  cv->setCursor(PX0 + NPIX * 2 + 4, PLOT_Y + PLOT_H - 8); cv->print("px");

  // Striscia: il frame attuale come mappa di colori
  cv->fillRect(0, STRIP_Y, W, STRIP_H, BG);
  for (int i = 0; i < NPIX; i++) cv->fillRect(PX0 + i * 2, STRIP_Y, 2, STRIP_H, colorOf(buf[i], top));

  // Cascata: scorre di una riga verso il basso, il frame nuovo in alto
  if (!hold) {
    uint16_t *fb = cv->getBuffer();
    memmove(fb + (WF_Y + 1) * W, fb + WF_Y * W, (WF_H - 1) * W * 2);
    cv->drawFastHLine(0, WF_Y, W, BG);
    for (int i = 0; i < NPIX; i++) cv->drawFastHLine(PX0 + i * 2, WF_Y, 2, colorOf(buf[i], top));
  }

  lcdPush();
}

// ---------------------------------------------------------------- comandi

void dumpRaw() {
  for (int i = 0; i < NPIX; i++) Serial.println(buf[i]);
}

void help() {
  Serial.println("t <us>=integrazione  e=esposizione auto  k=scala  h=fermo  w=raw  ?=aiuto");
  Serial.println("display: L=controller  r=rotazione  b=rosso/blu  i=inverti colori");
  Serial.printf("Integrazione %lu us %s, effettiva %lu us\n", (unsigned long)integUs, autoExp ? "(auto)" : "",
                (unsigned long)lastEff);
}

void handleCommand(String s) {
  s.trim();
  if (s.length() == 0) return;
  char cmd = s.charAt(0);
  String arg = s.substring(1); arg.trim();
  switch (cmd) {
    case 't': integUs = constrain((uint32_t)arg.toInt(), INTEG_MIN, INTEG_MAX); autoExp = false;
              Serial.printf("Integrazione %lu us\n", (unsigned long)integUs); break;
    case 'e': autoExp = !autoExp; Serial.printf("Esposizione auto %s\n", autoExp ? "on" : "off"); break;
    case 'k': autoScale = !autoScale; break;
    case 'h': hold = !hold; break;
    case 'w': dumpRaw(); break;
    case 'L': ctlPref = (ctlPref + 1) % 3; bgr = inv = -1; savePrefs(); lcdInit(); break;
    case 'r': rot = (rot + 1) % 4; savePrefs(); lcdApplyMode(); break;
    case 'b': bgr = !(bgr < 0 ? ctl == CTL_ILI : bgr); savePrefs(); lcdApplyMode(); break;
    case 'i': inv = !(inv < 0 ? false : inv); savePrefs(); lcdApplyMode(); break;
    default: help();
  }
}

// Picco verso ~3000: lontano dalla saturazione, ma con segnale abbondante
void adjustExposure(const Stats &s) {
  if (s.nSat) integUs /= 2;
  else if (s.mx > 50) integUs = integUs * (0.5f + 0.5f * 3000.0f / s.mx);
  else integUs *= 2;
  integUs = constrain(integUs, INTEG_MIN, INTEG_MAX);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_SI, OUTPUT);
  pinMode(PIN_CLK, OUTPUT);
  digitalWrite(PIN_SI, LOW);
  digitalWrite(PIN_CLK, LOW);
  pinMode(PIN_BOOT, INPUT_PULLUP);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_AO, ADC_11db);   // ~0–3.1 V

  pinMode(LCD_CS, OUTPUT);  digitalWrite(LCD_CS, HIGH);
  pinMode(LCD_DC, OUTPUT);  digitalWrite(LCD_DC, HIGH);
  pinMode(LCD_RST, OUTPUT); digitalWrite(LCD_RST, HIGH);
  pinMode(LCD_BL, OUTPUT);  digitalWrite(LCD_BL, LOW);
  lcdSpi.begin(LCD_SCK, LCD_MISO, LCD_MOSI, -1);

  delay(300);
  Serial.println("\nRazorGauge - TSL1401 con mappa dei pixel sul display");
  cv = new GFXcanvas16(W, H);       // 150 kB: va in PSRAM
  if (!cv || !cv->getBuffer()) {
    Serial.println("ERRORE: memoria per lo schermo non disponibile (PSRAM abilitata nel menu Board?)");
    while (true) delay(1000);
  }
  cv->fillScreen(0);
  buildCmap();
  loadPrefs();
  lcdInit();

  for (int i = 0; i < 3; i++) readFrame(buf);  // pulizia iniziale
  help();
}

void loop() {
  static String line;
  static uint32_t lastCharMs = 0, lastFrameUs = 0;
  static bool bootPrev = true;
  static uint32_t bootMs = 0;

  while (Serial.available()) {
    char ch = Serial.read();
    lastCharMs = millis();
    if (ch == '\n' || ch == '\r') { handleCommand(line); line = ""; }
    else line += ch;
  }
  // Anche senza terminatore (Serial Monitor su "No Line Ending"): esegue dopo 100 ms di silenzio
  if (line.length() && millis() - lastCharMs > 100) { handleCommand(line); line = ""; }

  bool boot = digitalRead(PIN_BOOT);
  if (!boot && bootPrev && millis() - bootMs > 250) { hold = !hold; bootMs = millis(); }
  bootPrev = boot;

  if (!hold) lastEff = capture(buf, integUs);
  Stats s = stats(buf);
  Shadow sh = shadow(buf, s);
  drawFrame(s, sh, lastEff);
  if (!hold && autoExp) adjustExposure(s);

  uint32_t now = micros();
  if (lastFrameUs) fps = 0.9f * fps + 0.1f * 1e6f / (now - lastFrameUs);
  lastFrameUs = now;
  if (hold) delay(30);
}
