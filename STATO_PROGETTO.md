# RazorGauge — stato del progetto e punto di ripresa

> **Questo è il repository unificato** (`github.com/stefanodemartini/RazorGauge`): CAD, schede,
> app WPF, CLI, libreria fisica e firmware sono versionati insieme. Il firmware attivo è il master
> **0.4.25-RB2** col calibro e lo slave **0.6.7**, entrambi per ESP32 classico, nelle cartelle
> `master/` e `slave/`. Il master ottico **1.0.0-alpha** è in `master_razorgauge/`: preliminare,
> non ancora operativo.
>
> Le copie in `Claude outputs/` e `_archivio_NON_USARE/` non sono sorgenti attive.
>
> Indici: `README.md` per la struttura, `FIRMWARE.md` per firmware/versioni, `MANUALE.md` per l'app.

Aggiornato: 24 ottobre 2026, 22:42:16 +02:00.

Verifica hardware completa del 19 ottobre: vedi VERIFICA.md.

Documento di progetto (versione modificabile): https://claude.ai/code/artifact/2273b50c-6248-4ea4-96ce-31eaccdc175b
Copia PDF: `RazorGauge_documento_progetto.pdf` in questa cartella.

## Modifiche dal lato software — leggere qui cosa è cambiato

Software e hardware sono ora nello stesso repository. Le modifiche al progetto vanno annotate qui
quando cambiano decisioni o stato del banco; il dettaglio puntuale resta nel `git log`.

### 3 novembre 2026 — compensazione: grafico, ugelli e colori incoerenti nel file C

Verificato su `Phantom ExtraHover V.2 C 0.50ips.flp`. I **dati erano giusti** (4 densità reali:
1.0095 / 1.0150 / 1.0215 / 1.0291 in 7 tratti); sbagliata la presentazione, per due motivi:
- il file C ereditava le **zone del progetto NC** (qui 1900–2050 cm su M2). Grafico e tag M{n}
  colorano per zona → linea a 2 colori (M1 ovunque + M2 a 1900–2050, dove il materiale vero è M4)
  e legenda con 2 voci, contro 4 ugelli in tabella. Ora le zone del C vengono ricostruite dai
  materiali reali (`ZonesFromBakedMaterials`)
- densità ugelli arrotondate a **2 decimali**: 1.0150 e 1.0215 diventavano entrambe 1.02, e la
  ricerca "ugello più vicino" (tag, fasce PDF) sbagliava. Ora 3 decimali, mostrate con `0.00#`

Correzione anche della temperatura dell'acqua: la casella confermava solo perdendo il focus (ora
anche Enter), e zone / file C non ricalcolavano la velocità al cambio d'acqua.
I file C già generati vanno rigenerati da NC.

Seconda verifica (file C 0.55 ips, PDF esportato da CLI):
- **quote sopra il profilo**: nel C seguivano solo i confini dei taper NC, quindi un tratto di
  materiale non aveva la sua lunghezza. Ora la catena usa gli stessi punti delle etichette Ø
  (cambi di taper + cambi di materiale), a schermo e nel PDF
- **M3 sparito dalle "Density zones" del PDF**: il k-means partiva con i centri sui quantili; con
  M4 su più di metà linea due centri cadevano sullo stesso valore e 1.018 + 1.025 diventavano un
  "1.02" inesistente. Ora i centri iniziali sono distribuiti sull'intervallo dei valori. Lo stesso
  difetto c'era nel calcolo vero (`QuantizeCompensationToRealMaterials`): una linea con lungo
  running line poteva uscire con meno di 4 materiali
- aperto: `flyline pdf` su un file C stampa la tabella a righe da 1 cm (106 pagine) — la CLI non
  usa il raggruppamento per zona dell'app

**Decisione di Stefano (3/11): transizione di 30 cm fra un ugello e l'altro** (non "tratto minimo
di 30 cm"). Implementata nella compensazione fisica (`ApplyNozzleTransitions`,
`NozzleTransitionCm = 30`): rampa lineare di densità centrata sul cambio, al massimo metà di
ciascun tratto vicino; diametro invariato. Una densità "fra due ugelli e uguale a nessuno" è una
transizione (`ChartGeometry.TransitionTest`): per questo gli ugelli del C ora sono salvati a
precisione piena; i C vecchi (densità arrotondate) non hanno transizioni e restano come prima.
Prova con banco WPF sul V.2 a 0.55 ips: 6 transizioni da 30 cm, 13 righe in tabella, scarto
peggiore 0.065 in/s. Corretti strada facendo: la CLI per un file C sovrascriveva la densità con
quella della zona (appiattiva le rampe); la riga "Density zones" del PDF con 13 fasce mandava in
errore QuestPDF (ora va a capo).

**Decisione di Stefano (3/11): foglio di progetto con forma, ugello e colore separati, tutto in
inglese.** Mockup approvato, poi implementato (`ProductionSchedule`, `NozzlePattern`,
`ChartGeometry.DrawProductionStrips`): profilo nel solo colore vero; fasce TAPER / NOZZLE ·
DENSITY / COLOR sotto il grafico (schermo e PDF); confini taper continui, ugelli tratteggiati;
ugelli distinti da grigio + tratteggio fitto, mai dal colore; PDF con riepilogo, legenda, schede
ugello e due tabelle (TAPER, NOZZLES). **4 ugelli = 4 densità ⇒ colore unico**: gli ugelli del C
prendono tutti il colore di M1 dell'NC; Compensate avvisa se l'NC ha zone di solo colore.
Bug trovati strada facendo e corretti:
- il PDF C dell'app calcolava massa e testa dalle righe raggruppate (una riga attraversava più
  taper, tronco di cono fra i soli diametri estremi): Head/Total 825/825 gr invece di 682.5/925.3,
  testa 3965 cm invece di 1900. Ora dalle fette; righe a schermo spezzate anche a cambio taper e
  testa/running
- compensazioni "a due punti" (CLI, C caricati, righe raggruppate) estrapolavano il diametro di
  bordo come se i punti fossero centri di fetta: nel PDF NC della CLI Ø 1.58 a 325 cm invece di
  1.40, massa gonfiata. Ora diametri di bordo esatti
- legenda a schermo "Comp. 1.00 in/s" su un C caricato (velocità non salvata): ora "Compensated profile"
Aperto: nell'NC del Phantom due tratti di pendenza diversa (1530–1760 e 1760–1900 cm) si chiamano
entrambi S10 → nel C il cambio di pendenza a 1760 si perde (TAPER mostra un solo S10).

### 28 ottobre 2026 — laser pulsato sulla RazorBoard SMD (master 1.0.1-alpha)

Laser + TSL1401 montati sulla RazorBoard SMD; sul modulo master c'era ancora il master del calibro.
Il modulo non si può tenere sulla scheda con l'USB collegato: **caricato fuori scheda** (COM5,
`arduino-cli upload`), poi rimesso sulla scheda. Prova tutta via WiFi con `/gauge/cmd?c=...` e
`/gauge` (JSON), IP **192.168.1.213**. EEPROM comune ai due firmware: PPC 30.21 e WiFi conservati.
JP2 su 3.3 V.

- **Niente saturazione con l'impulso corto.** Picco (mV) / pixel saturi su 16–125 al variare di
  `gauge_exp`: 2 µs 1345/0 · 4 µs 1368/0 · 8 µs 1813/0 · 16 µs 2981/8 · 30 µs 3155/88. 2 e 4 µs
  danno quasi lo stesso segnale: sotto ~4–5 µs l'impulso effettivo non si accorcia più (commutazione
  Q1 + accensione del diodo), non serve. Saturazione ADC a ~3155 mV. Il problema del banco `ccd_lcd`
  è risolto: R43 = 0 Ω va bene, **trimmer/ND16 non servono**.
- **Buio** (`gauge_dark`, 10 µs): 142 mV identico su tutti i 128 pixel = fondo scala dell'ADC
  dell'ESP32 (sotto ~140 mV non legge), cioè 0 V. I pixel 0–13 a 142 mV sono quindi gli stessi
  pixel morti del 25/10.
- **Riferimento** (`gauge_ref`, 10 µs): picco 1655 mV, accettato ma "uniformita 0% — bordi poco
  illuminati". Pixel 16–24 al buio, salita fra 28 e 40 (metà altezza ~px 32), poi luce fino al 127:
  il bordo sinistro del fascio cade dentro la finestra di misura, il destro fuori dal chip.
  **Fascio decentrato di ~4 mm verso i pixel alti** (come sul banco prima del ricentraggio):
  va ricentrato nella sede prima di buio/riferimento definitivi.
- Profilo in luce ancora "a buccia d'arancia" (±30% fra pixel vicini), come il 27/10.

- **Dopo un primo spostamento del laser** (10 µs, picco ~2050 mV, 0 saturi): luce da px 0 a ~103,
  salita lenta da sinistra (px 8 ≈ 770 mV, px 90 ≈ 1900) e **taglio netto a destra** (px 100 → 108:
  1420 → 480 mV, dal 113 buio). Il fascio è passato oltre: prima il bordo netto era a sinistra (px 33),
  ora a destra. Larghezza illuminata ~100 px ≈ 6.3 mm, **meno dei Ø13 attesi**. Il bordo netto segue il
  fascio: probabile **diaframma nel percorso** (vicino al laser/L1, ingrandito ×5.2 sul chip), non
  verificato.
- **"Rumore" del blu su /diag** (12 frame a 10 µs, pixel 4–105 illuminati): differenza fra pixel
  vicini 12.9% in media ma **ferma** fra un frame e l'altro (frange/speckle, come il 27/10). Nel tempo
  ogni pixel varia del 2.7%, ma quasi tutto è energia dell'impulso comune a tutti i pixel (2.6%);
  dopo la normalizzazione sull'energia, come fa il master, resta **0.16%**. Lo schema fisso lo toglie
  la divisione per il riferimento.
- **I pixel 0–13 rispondono alla luce** (px 0 208 mV, px 9 876 mV): non sono morti. Il 24–25/10 a 0
  fisso, probabilmente perché non illuminati; da ricontrollare prima di cambiare `G_PIX_FIRST`.

- **Sede laser instabile** (Stefano): i 3 grani M3 non tengono fermo il laser. Sezione in
  `immagini/sede_laser_sezione.png` (schema) e `immagini/sede_laser_pezzo_unico.png` (sezioni reali
  dell'STL del pezzo unico, quote verificate: Ø3 / Ø4.3 / Ø5 come nel CAD): solo 4 mm guidati nel perno Ø4.3 (0.15 mm per lato), 10 mm liberi
  nel Ø5 (0.5 mm per lato), grani a 11.5 mm dalla battuta con ~4 mm di filetto nella plastica.
  Inclinazione libera ~44 mrad ≈ ±3.5 mm sul chip. Rimedi: nastro/guaina sulla punta, guaina sotto i grani,
  allineare e incollare; per la ristampa sede più lunga e precisa con molla o O-ring.

**Prossimo passo:** ricentrare il fascio guardando `http://192.168.1.213/diag` (campana che copra
16–125 senza tratti piatti), esposizione ~10–14 µs per picco 1700–2300 mV, poi `gauge_dark` +
`gauge_ref` e prove di `PROCEDURA_PRIMO_AVVIO.md` dal punto 3.

### 27 ottobre 2026 — TSL1401 col laser acceso fisso attraverso L1–L2 (banco `ccd_lcd`)

Laser 650 nm 1 mW alimentato con 2 pile da 1.5 V (acceso fisso, non pulsato), fascio attraverso
L1 + L2, sensore sul kit WROVER con `ccd_lcd`. Misure lette da seriale (`w`) a integrazione fissa.

- **Luce ambiente da sola** (laser spento): risposta lineare ~0.5 LSB/µs al centro, profilo liscio,
  più scuro verso il pixel 14 (~1/3 del centro). Pixel 46, 75, 81 (forse 31) 7–10% sotto i vicini
  in tutti i frame: probabile polvere sulla finestra, **non verificato**.
- **Laser acceso: satura.** Senza filtri, alla posa minima di allora (200 µs richiesti, ~342 µs
  effettivi) i pixel 31–127 sono a 4095. Il fascio ha un bordo verso i pixel 31–40 (salita in
  ~10 px ≈ 0.6 mm) e prosegue oltre il pixel 127: o è **decentrato di ~4 mm** verso i pixel alti
  (fascio atteso Ø13–14 dopo l'espansione ×5.2), o qualcosa lo taglia. **Da verificare**; la
  collimazione non è giudicabile finché satura e non si vedono entrambi i bordi.
- Col fascio in luce piena il profilo è "a buccia d'arancia" (±30–40% fra pixel vicini) ma
  **identico fra un frame e l'altro**: frange/speckle del laser attraverso lenti e finestra, non
  rumore del sensore (con la sola luce ambiente il profilo è liscio). Una soglia sui bordi ne
  risentirebbe; l'algoritmo ad area del master lo media.
- **Sacchetto antistatico argentato** come attenuatore: 1 tentativo ~7–15× (ancora ~20 pixel saturi
  a 200 µs); al secondo il fascio passava in parte fuori dal film (luce ×8). Pellicola solare OD 5.6
  scartata (~10⁴ volte troppo scura); scelto un **ND16 Cokin P** (OD 1.2, da verificare a 650 nm:
  le resine economiche nel rosso attenuano meno del dichiarato).
- **`ccd_lcd`: minimo d'integrazione da 200 a 1 µs** (comando `t` ed esposizione auto) e stampa
  dell'integrazione effettiva in `?`. Minimo effettivo misurato **143 µs** (era ~342): sono i 110
  clock di svuotamento con `digitalWrite` (~1 µs l'uno) + 20 µs di trasferimento carica. Risposta
  lineare con intercetta ~0 fra 143 e 342 µs (px 14: 300 → 768). Ancora 92/110 pixel saturi.
  Con clock via registri si scenderebbe a ~35–45 µs (limite TSL1401 ≈ (n−18) clock a 8 MHz + 20 µs
  ≈ 34 µs), probabilmente non abbastanza da solo.
- **Conclusione:** col laser acceso fisso la saturazione non si toglie dal software. Il laser da
  1 mW **non** è da sostituire: nel master la posa è l'impulso di µs e si regola accorciandolo.
  Sul banco: ND16 (eventualmente + clock veloci) oppure pulsare il laser dal kit con un NPN come
  nel master.
- **Fascio ricentrato, sacchetto tolto** (Stefano scarta la soluzione del sacchetto): a 143 µs
  effettivi saturano 109/110 pixel, solo px 125–127 in scala (3228 → 2385, bordo destro del fascio).
  Il bordo sinistro di prima era quindi il fascio decentrato, non un taglio. Col fascio centrato i
  bordi del fascio escono dal chip: la prova successiva è l'ombra di un filo appoggiato sulla finestra.

**Deciso: il 28/10 si prova con la RazorBoard e il master**, che già pulsa il laser: Q1
(2N7000/2N7002) su GPIO25, JP2 per 3.3/5 V, R43 = 0 Ω pronta per limitare la corrente; firmware
`gCapture` accende il laser solo per `gExposureUs` (default 20 µs, 2–20000 con `gauge_exp`), cioè
7–70 volte meno luce dei 143 µs del banco `ccd_lcd`. Le opzioni qui sotto restano di riserva.

**Opzioni di riserva:** attenuare agendo sul laser.
- Il modulo ha **solo due fili**: non si vede se dentro c'è una resistenza o un driver a corrente
  costante (APC). I Ø4 mm da 1 mW economici di solito hanno solo la resistenza.
- **Trimmer 500 Ω–1 kΩ in serie**, partendo da 0 Ω, regolato mentre si legge il sensore (centro a
  2500–3500). Zona utile stimata 50–200 Ω con 3 V. Se la luce cala gradualmente → resistenza, ok; se
  resta uguale e poi si spegne di colpo → driver, il trimmer non serve. Limite: per ridurre di 10–30×
  il diodo lavora pochi decimi di mA sopra la soglia, quindi la potenza deriva con temperatura e
  tensione delle pile.
- In alternativa (più stabile, indipendente dal tipo di modulo): **laser pulsato dal kit** con NPN
  (2N2222/BC337 + 1 kΩ) su un GPIO libero, impulso di µs dentro l'integrazione, come il master.
  Sketch da scrivere; prima verificare quale GPIO è libero sul WROVER-KIT (GPIO25 è il MISO del display).
- Oppure ND16 Cokin P quando arriva.

### 26 ottobre 2026 — TSL1401 con mappa dei pixel sul display (ESP-WROVER-KIT)

Sketch nuovo **`ccd_lcd/`** per l'ESP-WROVER-KIT v4.1 (board Arduino "ESP32 Wrover Kit", PSRAM
abilitata): stessi pin del sensore di `ccd_test` e del master (SI 26, CLK 27, AO 34), che sul kit
sono liberi **solo senza fotocamera montata**. Sul display 320×240: testata con integrazione, fps,
min/max/media sui pixel 16–125 e ombra trovata (bordi interpolati, larghezza in px e mm); grafico a
aste (rosso = saturo, fondo scuro = pixel morti); striscia con la mappa del frame; cascata degli
ultimi 66 frame. BOOT congela l'immagine. Comandi seriali in testa allo sketch.

**Provato sull'hardware**, funziona:
- Il display del kit è un **ILI9341** che risponde **0** sia a RDDID (04) sia a ID4 (D3). Lo
  sketch quindi sceglie ILI9341 di ripiego e ST7789 solo se legge l'ID 85 85 52. Con ST7789 forzato
  rosso e blu escono scambiati.
- **Svuotamento del sensore con soli clock** (senza `analogRead`): pochi µs invece dei ~5.5 ms di un
  frame letto. L'integrazione minima scende da ~5.2 ms a ~0.2 ms. Con la luce della stanza la
  prima versione restava satura su tutti i 110 pixel anche al minimo; ora l'esposizione automatica si
  ferma a ~2 ms con i pixel tra 2750 e 3500.
- Pixel 0–13 a zero, come sul primo banco: è il sensore, non la scheda.
- Pixel 31 a ~2400 contro ~2800 dei vicini, in un frame sotto luce ambiente: forse polvere sulla
  finestra, **non verificato**.

**La larghezza dell'ombra in mm è molto approssimativa** (osservato da Stefano): senza laser non
misura il diametro. La luce della stanza è una sorgente estesa: penombra larga e ingrandimento che
dipendono dalla distanza del filo dal chip (errore di solito in eccesso). In più la soglia è a metà
fra min e max di tutto il profilo, che non è uniforme (~1400 → saturo), e la misura è su un solo frame.
Il conto di precisione del 25/10 vale col laser collimato, non qui. Migliorie possibili, **non fatte**:
soglia locale per ciascun bordo, media su N frame con deviazione standard, fattore di calibrazione
con un filo noto (come `gauge_cal`); sul banco filo appoggiato sulla finestra e sorgente piccola e
lontana.

Pratico: il kit è su **COM10** (FT2232: COM9 = JTAG, COM10 = UART). L'upload vuole **BOOT premuto**
(l'auto-reset non entra in download). Dopo l'upload non riparte da solo: serve un reset (EN, o RTS
da seriale). Aprire la porta seriale può resettare la scheda; le impostazioni del display sono in NVS
(namespace `ccdlcd`) e sopravvivono.

### 25 ottobre 2026 — LED del modulo Hiwonder: va coperto

Prova con `ccd_test`, modulo sotto una scatola (stanza esclusa), laser spento, media dei pixel 16–125
su 5 frame. Integrazione effettiva = `t` + ~5.5 ms di lettura.

| Integrazione effettiva | LED acceso | LED coperto con nastro |
| --- | --- | --- |
| ~5.7 ms | 0 | 0 |
| ~10.5 ms | 33 LSB | 0 |
| ~25.5 ms | 197 LSB (gradiente 174–212 lungo il chip) | 0 |

- Il LED vale circa **11 LSB/ms (~9 mV/ms)**. Lo 0 a 5.7 ms non vuol dire assenza di luce: la retta
  passa per lo zero a ~85 LSB (~70 mV), cioè la **zona morta dell'ADC** dell'ESP32 sotto ~70 mV.
- Nel master la luce continua si integra per tutta la lettura (~11 ms con 2 letture/pixel), contro un
  impulso laser di µs: il LED aggiunge ~100 mV, circa il **5% del picco** di riferimento (1700–2300 mV).
- Se costante lo toglie il frame di buio, ma consuma scala dell'ADC e, se varia (temperatura,
  alimentazione), entra nella misura: un 2% di variazione del LED vale ~2 µm sul diametro, più l'effetto
  del gradiente. Il buio della stanza col LED coperto è sotto la soglia dell'ADC anche a 25 ms.
- **Decisione: coprire il LED** (nastro nero o vernice) oppure dissaldarlo con la sua resistenza, come
  già previsto. Nella torre chiusa sarebbe l'unica luce parassita.

### 25 ottobre 2026 — precisione teorica del laser e misura della densità

**Precisione attesa (stima teorica, da confermare al banco):** ripetibilità **1–3 µm**, accuratezza
**±3–5 µm** dopo la calibrazione con le spine. Il diametro è l'area dell'ombra, quindi la risoluzione
non è limitata dal pixel (63.5 µm) ma dal rumore. Diffrazione: a 2.5 mm dal chip le frange sono
larghe √(λ·z) ≈ 40 µm, la finestra con 8 pixel di margine (~12 volte) le conteggia quasi tutte.

| Sorgente (Ø 2 mm, finestra ~48 px) | Stima | Tipo |
| --- | --- | --- |
| Rumore ADC (~8 mV su ~2000, 2 letture/px, 8 frame) | ~0.5 µm | casuale |
| Stima energia `k` (~60 px fuori ombra) | < 0.1 µm | casuale |
| Non linearità ADC sui pixel di bordo | ~3 µm | sistematico → offset della calibrazione |
| **Frange d'interferenza che si spostano (temperatura → λ del diodo)** | **2–5 µm** | **deriva: il limite vero** |
| Altezza linea ±0.1 mm con 5 µm/mm di collimazione residua | ~0.5 µm | casuale |
| Linea inclinata 2° sulla fila di pixel | ~1 µm | sistematico |
| Spine di calibrazione | ±1–2 µm | sistematico |

- Controllo della deriva: indice **`flat`** in `/diag` (residuo RMS fuori ombra). Sotto ~1% → deriva
  di pochi µm; se cresce, rifare `gauge_ref`. Far scaldare il laser qualche minuto prima di calibrare.
- Esclusi dal bilancio: ovalità (un solo asse), pixel morti (nessun effetto, vedi sotto).
- Rispetto al calibro (ripetibilità ~50 µm + offset da schiacciamento ~0.05–0.06 mm): 10–20 volte meglio.
- **Tempi di misura da ricontrollare:** con `G_OVERSAMPLE` = 2 e ~43 µs per lettura ADC un frame dura
  ~11 ms, quindi 8 frame ≈ 90 ms per misura e la mediana di 7 ≈ 0.6 s, non i ~35 ms / 0.25 s della
  tabella in "Sviluppi futuri". A 2 cm/s ogni punto mediarebbe ~1.3 cm di linea: misurare il tempo
  reale al primo avvio (`gauge_stat`) e, se serve, scendere a 1 lettura/pixel o meno frame.

**Densità da scan + pesata** (l'app ha già "From Weight", `WeightToDensityDialog`):
ρ = m / Σ V_slice, con V = π/4 · d² · 1 cm. L'errore sul volume è il **doppio** di quello sul
diametro (δρ/ρ ≈ 2·δd/d); peso e lunghezza contano poco (bilancia 0.01 g su 10–20 g ≈ 0.1%,
encoder < 0.5%). Il rumore casuale si media sulle slice, l'offset sistematico no.

| Errore sistematico su Ø | Punta Ø 1.0 | Ventre Ø 2.0 |
| --- | --- | --- |
| Calibro, ~0.05 mm | ~10% | ~5% |
| Laser ±0.01 mm | 2% | 1% |
| Laser ±0.005 mm | 1% | 0.5% |

Floating/neutra differiscono del 5–10%: col calibro non si distinguono, col laser sì.
Limiti che restano: ovalità (sezione non circolare, un solo asse misurato), core incluso (per il
coating: ρ = (m − m_core)/(V − V_core)), una pesata = una sola densità media (le zone richiedono tagli).

**Riferimento indipendente: pesata idrostatica (Archimede)**, ρ = m_aria / (m_aria − m_liquido) · ρ_liquido.
Problema riscontrato: bolle d'aria tra le spire a contatto. Ordine di grandezza: testa 10 m Ø 1.2 ≈ 11 cm³,
l'1% sono 0.11 cm³ d'aria (una bolla Ø ~6 mm o decine di millimetriche). Metodo consigliato:
- **spezzoni dritti** da 20–30 cm appesi a un gancio sottile (niente spire a contatto), oppure telaio
  aperto con spire distanziate (tarato a parte in aria e immerso);
- **etanolo/isopropanolo** invece dell'acqua: bagna meglio (niente bolle) e con ρ ≈ 0.79 fa affondare
  anche le floating senza zavorra. ρ_liquido varia ~−0.1%/°C e con l'umidità: misurarla a ogni sessione
  con un corpo di riferimento (cilindro acciaio/vetro pesato in aria e immerso). Immersione di pochi
  minuti (il PVC plastificato non va lasciato a bagno);
- immersione lenta e inclinata, picchiettare, ripetere finché 3 letture sono stabili (le bolle fanno
  salire le letture successive).
Uso previsto: una volta su uno spezzone già scansionato → errore reale del gauge (e ovalità, se il
volume Archimede è sistematicamente minore di quello dello scan). Se concordano entro 1–2%, da lì in
poi basta scan + pesata.

### 25 ottobre 2026 — pixel 0–13 del TSL1401: morti

Ripresa dai passi del 24/10, con l'ESP32 di prova su COM8 letto direttamente dal PC.
`ccd_test` ha tre comandi nuovi: `z` (primi 24 pixel + zeri in testa), `o <us>` (attesa dopo SI),
`p <us>` (attesa per pixel). Per caricare serve il tasto **BOOT**: il reset automatico non entra in
download mode.

- **Non è un problema di tempi.** Da 0.2 a 20 ms di integrazione, con attesa dopo SI 0–3 ms e
  1–100 µs per pixel (frame da 5.5 a 18 ms), i pixel a zero sono sempre **esattamente 0–13**.
- **Non è una copertura.** Il bordo è netto, senza penombra: pixel 13 = 0 col pixel 14 a 4095. Col
  laser nudo puntato a mano sul chip (circa 25 s, spazzando anche l'estremità 0–13) i pixel 14–127
  sono quasi sempre saturi per la luce diffusa nel package, e i 0–13 non escono mai da 0. Una
  copertura esterna lascerebbe passare almeno la luce diffusa.
- **Conclusione: pixel 0–13 morti** (danno sul chip a quell'estremità o difetto di fabbrica; le
  connessioni invertite non spiegano un blocco di pixel contigui). Restano 114 pixel ≈ 7.2 mm,
  sufficienti fino a 3 mm. Un TSL1401 di scorta conviene ordinarlo comunque.
- Il laser nudo satura tutto il sensore già alla posa minima di `ccd_test` (~5 ms, lettura lenta):
  normale, nel master la posa è un impulso di µs.
- **Master laser 1.0.1-alpha:** `G_PIX_FIRST` = 16 / `G_PIX_LAST` = 125 (pixel usati, inclusi).
  Prima i pixel morti venivano forzati a 1.0 ed entravano nella stima dell'energia `k` e
  nell'uniformità, falsando il diametro; ora ricerca dell'ombra, `k`, uniformità, picco e controllo
  "ombra al bordo" usano solo la zona utile; `center` resta riferito al centro fisico del chip.
  Margine: l'ombra sta sempre entro 1.5 mm dal centro della gola J (larga 3.0) + 0.51 mm di frange;
  verso il lato morto restano 3.02 mm → la gola tollera ~1.0 mm di disallineamento da quel lato
  (1.9 mm dall'altro). Lato fisico del pixel 0 ancora da individuare (segno di `center` in `/diag`).
  Con un sensore sano rimettere `G_PIX_FIRST` = 2. Compilato (82%), non provato sul banco.
  Il simulatore `strumenti/firmware_sim/gauge_v06.inc` ha una sua copia dell'algoritmo, non aggiornata.

### 24 ottobre 2026 — prima prova del sensore CCD (senza laser)

In attesa della ristampa MJF, il modulo **Hiwonder TSL1401** è stato collegato a un **ESP32 di
ricambio** (DevKit V1, identico agli altri) con lo sketch nuovo **`ccd_test/`**: stessi pin del
master (VCC 3V3, SI 26, CLK 27, AO 34; laser non collegato), integrazione regolabile in ms
(`t <us>`), profilo ASCII continuo (`g`), dump raw (`w`), test di linearità (`a`). Il
`gauge_esp32` non serviva: senza laser integra solo ~1.5 ms, troppo poco con luce ambiente.

Risultati:
- **Il sensore funziona.** I pixel **14–127** rispondono alla luce: buio con la mano, ~2400 LSB
  uniformi sotto la torcia del telefono, transizioni morbide e coerenti spostando la luce.
- Luce della stanza a 5 ms: **satura** (4095) su parte del sensore → con la luce ambiente usare
  `t 1000` o meno.
- **Lettura lenta: ~43 µs per pixel** (analogRead del core 3.3.12; dedotto dal primo output, dove
  il valore errato −774 µs era proprio il tempo di 18 letture). Un frame intero richiede ~5.5 ms, e
  la lettura stessa aggiunge ~4.7 ms di integrazione: l'integrazione effettiva di 5728 µs letta
  dopo la correzione è compatibile con `t 1000` + 4.7 ms. **Conta per il master 1.0.0**: con
  laser pulsato la luce ambiente si integra anche durante la lettura, e 8 frame per misura sono
  ~45 ms, non i ~35 ms stimati. Da verificare: è il valore stampato con `t` noto, oppure misurare
  con `t 200`.
- **Punto aperto: i pixel 0–13 leggono 0 fisso, anche con la torcia puntata sopra** (~0.9 mm a
  un'estremità). Lo 0 è il valore del buio pieno, e il passaggio a valore pieno è netto: ipotesi
  principale **copertura fisica della finestrella** (residuo del supporto dell'obiettivo rimosso,
  colla, bordo di plastica), non un difetto di lettura. Non ancora verificato.
- Restano comunque 114 pixel ≈ 7.2 mm di campo, sufficienti per un cavo da 3 mm, ma l'ombra non
  sarebbe più centrata sul fascio.

**Si riprende da qui:**
1. Guardare il chip con lente / macro del telefono sull'estremità dei pixel 0–13: finestrella
   trasparente per tutti gli ~8 mm?
2. Con `g` attivo far passare lentamente l'ombra di una matita verso quell'estremità: se sparisce
   di colpo entrando nella zona → copertura netta.
3. `w` e leggere i primi 20 valori: salto 0 → pieno in un pixel = bordo dell'ostacolo appoggiato
   sul chip; salita graduale = ombra di un bordo più alto (supporto).
4. Lanciare `a` (linearità) con luce costante e annotare l'esito; non è ancora stato fatto.

Corretti nello sketch durante la prova: esecuzione dei comandi anche con il Serial Monitor su
"No Line Ending" (dopo 100 ms di silenzio), e calcolo del tempo d'integrazione effettivo (veniva
negativo → 4294966522 µs).

### 20 ottobre 2026 — firmware diagnostico

- **UART master↔slave: funziona, causa non accertata.** Continuità R10/R11 tra i fori 6/7 degli
  zoccoli corretta (≈ 470 Ω). Ripartita dopo spegnimento e manipolazione dei moduli; il 21/10 si è
  fermata di nuovo nella notte senza che nessuno toccasse nulla ("Motor offline") ed è ripartita
  dopo un nuovo spegnimento. Ipotesi: contatto intermittente (saldature J7 da rifare) oppure blocco
  firmware dopo ore. Al prossimo blocco, senza toccare: leggere `/motor_diag` e `/diag`, poi EN solo
  sullo slave, poi solo sul master; J7 solo se nessun reset basta.

- **UART master→slave non funzionante: il modulo slave è sano.** Slave fuori dalla RazorBoard,
  alimentato da USB: GPIO16 a riposo ≈ 3 V (pull-up, nessun corto). Loopback con ponticello
  GPIO17→GPIO16 e reset (lo slave rimanda a sé stesso il proprio `STATUS`): `/diag` riporta
  `rxBytes` 99965, `rxLines` 5900 → RX2 e TX2 del modulo funzionano.
  Stesso loopback sul master fuori scheda (si interroga da solo con `STATUS?` ogni 2 s):
  `/motor_diag` riporta `txLines` 84, `rxLines` 84, `rxBytes` 672 (= 84 × `STATUS?\n`) → anche
  il master è sano. **Entrambi i moduli funzionano: il guasto è sulla RazorBoard** — R10/R11,
  piste UART, saldature dei fori 6/7 degli zoccoli master e slave.

- **Slave 0.6.7**: `/rx_test` disabilita i pulsanti fino al riavvio, evitando l'attivazione
  intermittente di FAST_O quando GPIO34 è flottante fuori dalla RazorBoard.
  Build timestamp: `2026-10-20 22:10:02 +02:00`.
- **Slave 0.6.6**: `/rx_test` ora arresta lo stepper prima della lettura, evitando il rifiuto
  dovuto a stati transitori dei pulsanti. Build timestamp: `2026-10-20 22:09:07 +02:00`.
- **Slave 0.6.5**: aggiunto `/rx_test`, che verifica RX2/GPIO16 con pull-up interno isolando
  temporaneamente la UART. Build timestamp: `2026-10-20 21:41:38 +02:00`.
- Corretto l'armamento del watchdog encoder: ora parte con un comando di movimento, non dopo
  inattività a motore fermo. Aggiunti contatori diagnostici WebSocket/UART consultabili da
  `/motor_diag`. Build timestamp: `2026-10-20 19:40:43 +02:00`.
- **Master 0.4.25-RB2 e slave 0.6.4**: diagnostica UART lato slave e pagina Wi-Fi `/diag`;
  IP dello slave esposto in `/motor_diag`. Rimosso il test LED GPIO2, non presente sul modulo.
  Build timestamp: `2026-10-20 20:13:29 +02:00`.

### 19 ottobre 2026 — dal lato software

- **Firmware e software sono riuniti in questo repository.** Le sorgenti canoniche sono
  `master/` (0.4.25-RB2, attivo), `slave/` (0.6.7, attivo),
  `master_razorgauge/` (1.0.0-alpha, preliminare) e `gauge_esp32*/` (banco). Indice in
  `FIRMWARE.md`.
- **Il master laser è stato rinumerato 0.6.0 → `1.0.0-alpha`**: il laser è un ramo diverso, non un
  passo avanti sulla linea col calibro. 0.x = era calibro, 1.x = era laser.
- **Tutti gli sketch compilano davvero** con l'`arduino-cli` dell'IDE (core esp32 3.3.8). Prima
  c'era solo un controllo di sintassi con g++ simulato.
- **PPC encoder misurato e verificato** su linea graduata al metro: attivo 30.2100, corretto
  **30.1837** (errore di scala 0.087%). Conferma sperimentale che il contatto tangente non richiede
  correzione in base al diametro.
- **Questa cartella è ora un repo git** (sorgenti: SCAD, KiCad, script, documenti; fuori mesh,
  render, PDF, DXF e le `.history` di VS Code, che contengono repo annidati).
- Aggiornati qui: i riferimenti di versione del firmware, la nota "mai compilato con il core reale",
  e due punti aperti che nel frattempo erano stati chiusi.

## In una riga
Misuratore ottico a ombra per il diametro delle code di topo (0.5–3 mm, tipico ~2 mm), che sostituisce il calibro centesimale nel sistema esistente (master ESP32 + encoder + slave motore passo-passo + app WPF via WebSocket). Precisione attesa ±3–5 µm dopo calibrazione.

## Decisioni prese (non rimettere in discussione senza motivo)
| Tema | Decisione |
| --- | --- |
| Orientamento | Torre verticale: laser in alto, sensore in basso (chip verso l'alto), cavo orizzontale |
| Fissaggio | Piano verticale dietro la torre, faccia d'appoggio a 35.4 mm dall'asse del fascio; 4 viti M4 a ±21 mm, Z = 36 e 86.2 mm dalla faccia del chip (v2; v1: 36 e 126.2) |
| Ottica | Laser 650 nm 1 mW Ø4×14 (1.2 mrad) · L1 biconcava F12F-19.3 (Ø12.47 × 3.11 mm) · L2 plano-convessa f100 (Ø19.95, bordo 2.35, faccia piana in alto — v2) · distanza L1–L2 = 80.7 mm · espansione ×5.2 |
| Quote Z (dalla faccia del chip) | laser 120.2 · L1 105.2 · L2 24.5 (carrello −5/+6) · appoggio cavo 2.5 · chip 0 |
| Cavo | Max 3 mm; tasca guida a J larga 3.5 mm |
| Sensore | Hiwonder CCD TSL1401 V1.0: obiettivo+supporto rimossi, connettore XH spostato sul retro (fatto), LED da togliere/coprire |
| Algoritmo | Diametro = AREA dell'ombra (non soglia) + ri-normalizzazione per frame sull'energia dell'impulso; laser pulsato = tempo di posa |
| Stampa | HP MJF PA12; versione alleggerita 67.5 cm³ totali (torre 58.2, coperchio 7.0, carrello 2.3) |
| Nome | RazorGauge, inciso sul coperchio |
| Controller | ESP32 **classico** (WROOM/DevKit), NON S3. Il master attuale verrà sostituito da un ESP32 identico nuovo |
| Encoder | Contatto tangente con rullo di contrasto → nessuna correzione della lunghezza in base al diametro |
| **Lastre CNC già ordinate** | Le lastre in alluminio (piastra verticale, mensola, base, piastrina IEC) e la ruota encoder sono **fisse**: ogni modifica agli STL stampati deve adattarsi a loro. **Dopo OGNI modifica degli STL** rilanciare `strumenti/verifica_piastre_cnc.py` (legge gli STEP in `piastra_alluminio/cnc`): impronta del pezzo unico dentro la piastra, 8 viti M3×12 allineate ai fori filettati con 7.2 mm di PA12 (4.8 in presa), foro distanziale RazorBoard P12 coperto a filo, aperture A1/A3, nessuna compenetrazione piastra–assieme, encoder nel foro Ø42, ruota CNC reale (mozzo Ø18 + battistrada) con gioco ≥ 0.5 mm. Regola chiesta da Stefano il 30/10/2026. |
| **Montabilità** | Dopo ogni modifica controllare anche che **ogni pezzo si possa montare** nell'ordine reale (non solo che non compenetri da montato): percorsi di inserimento, accesso di viti e chiavi. Sezione M di `verifica_finale_profiler.py`. Regola chiesta da Stefano il 30/10/2026. |
| Calibro centesimale | Tenuto SOLO per il collaudo del laser, poi rimosso. Rullino a cuscinetto con molla verticale dall'alto contro appoggio fisso; legge ~7–8% in meno del reale (deformazione PVC). Niente ovalità, niente secondo RazorGauge; la RazorBoard v0.1 resta senza ingresso calibro |

## Pezzi stampati (arrivati 7/10/2026) — problemi trovati
- **Sede laser senza battuta (errore di progetto, corretto):** nel file SCAD il foro libero Ø9 di L1 era alto 40 mm e arrivava a Z 125.2, asportando la battuta Ø3 e il perno Ø4.3 della sede laser. Nella torre stampata il laser non ha appoggio sotto.
  - Riparazione senza ristampare la torre: inserto `stl/RazorGauge_laser_insert.stl` (Ø8.7 × 7.5 mm, sorgente `cad/RazorGauge_laser_insert.scad`), da infilare DA SOTTO nel foro Ø9 (coperchio tolto, dal canale tra il blocco L1 e il solaio) fino allo scalino del Ø5, e incollare. Ricrea battuta Ø3 + perno Ø4.3. Vedi `immagini/sede_laser_riparazione.png`.
  - `cad/RazorGauge.scad` corretto (parametro `clear_h` in `lens_seat`) e `stl/RazorGauge_tower.stl` rigenerato (58.6 cm³): le prossime stampe hanno la sede giusta.
- **L2 sbagliata:** la lente Ø12.7 disponibile ha f = 20 mm (inutilizzabile: ingrandimento 1.04). La f = 100 disponibile è Ø20 e non entra nel canale 18 × 18. Opzioni: comprare PCX Ø12.7 f = 100 (es. Thorlabs LA1207; torre invariata; il carrello accetta f ≈ 94–105 mm) oppure ridisegnare torre + carrello per la Ø20 (servono spessore al bordo e al centro). **Deciso 7/10/2026: torre v2 per la lente Ø20 (vedi sotto).**

## Torre v2 (7/10/2026) — da stampare
- L2 = PCX **Ø20 f=100**, misurata Ø19.95, bordo 2.35 mm (centro ≈ 3.3): canale interno 24 × 24 (v1: 18 × 18), carrello 23.6 × 23.6 × 12, sede lente Ø20.25 × 3.2 con foro libero Ø14; la faccia curva (in basso) appoggia sul bordo del foro, faccia piana in alto. Vite di blocco del carrello spostata 3.5 mm sopra la sede (asola nella torre spostata di conseguenza).
- Sede laser corretta (battuta Ø3 + perno Ø4.3 + Ø5).
- Fascia di fissaggio superiore abbassata di 40 mm: fori M4 a Z 36 e **Z 86.2** (era 126.2), sempre a ±21 mm; interasse verticale 50.2 mm. Piano sempre a 35.4 mm dall'asse.
- Coperchio: costola più profonda nella zona di L2 (trattiene la lente Ø20 con 0.3 mm di gioco).
- Volumi: torre 68.1 cm³, coperchio 8.3, carrello 3.9 (totale 80.3). Verificato al modello: carrello e lente nelle 3 posizioni (−5/0/+6) senza interferenze con torre e coperchio.
- File: `stl/` (v2), `cad/RazorGauge.scad` (v2), `dxf/` rigenerati, `immagini/preview_v2*.png`. La v1 stampata e l'inserto di riparazione sono in `stl/v1_stampata/` e `cad/RazorGauge_v1.scad`.

## Integrazione nel FlylineProfiler V3 (8/10/2026) — pezzo unico piastra + torre
Cartella `integrazione_profiler/`. Sostituisce torre separata e comparatore: piastra del profiler e torre RazorGauge stampate in **un unico pezzo** (MJF).
- Vincoli: piano di scorrimento del cavo invariato (sopra la ruota encoder, premuto dal rullo superiore), fondo cavo Y 66.91 (coordinate STL originale); asse cavo a **19.2 mm** dalla faccia anteriore della piastra; supporto encoder invariato.
- Chip TSL1401 2.5 mm sotto il cavo; scheda Hiwonder com'è, lato corto (8.5 mm dal chip) verso la ruota, connettore verso il rullo.
- Punto di misura a Z 21.0 (8.55 mm dalla vecchia sede del comparatore verso il rullo) per non toccare la ruota (Ø63.7, circonferenza 200 mm): gioco scheda-ruota 0.9 mm, scheda-rullo 1.2 mm. *(Superato: dopo lo spostamento a Z 21.55 il gioco scheda-ruota è 0.6 mm, vedi sotto.)*
- Rullo inferiore (cuscinetti 625 Ø16), suo braccio e supporto dello spintore spostati di **13 mm** verso l'esterno; piastra allargata di 13 mm su quel lato (Z −9.4). Appoggio centrale con la vecchia sede rimosso.
- Torre = colonna v2 (L2 Ø19.95, sede laser corretta) fusa alla piastra; coperchio con viti a 40/75/133 mm dal chip; vite carrello a X −6 (lontana dal perno dello spintore).
- **Gioco scheda sensore ↔ ruota encoder troppo stretto (28/10/2026, segnalato dall'utente: sembra toccare)**: al modello il punto più vicino è lo spigolo della PCB Hiwonder sul lato corto verso la ruota, faccia posteriore (Y 60.91, Z 30.05): **0.6 mm** con ruota Ø63.66, 0.33 mm con Ø64.2 (massimo tollerato). La slitta è a 1.0 mm. Rimedio provvisorio sul pezzo stampato attuale: smusso a lima 45° × 1 mm su quello spigolo → 1.2 mm. **Superato nel pezzo da ristampare** dalla scheda propria col lato ruota corto (gioco 2.7 mm, vedi sotto).
- **Mensola piena + slitta v2 per la scheda TSL1401CL propria (28/10/2026, pezzo unico NON ancora ristampato)**: l'utente segnala la slitta flessibile *compreso il supporto*: la colonnina della vite era retta solo da una trave 2.5 × 5 mm lunga ~28 mm (stima ~6 N/mm). Sostituite sede + trave + colonnina con una **mensola piena fusa con la piastra** (X 7.22 → 41.5, Z 3 → 30, Y 47 → 58.11; scarico radiale 1.5 mm per la ruota nel tratto X 12–34, anche per la ruota originale 5 mm avanti). Rigidezza stimata ~40 volte maggiore. **Slitta v2** 3.5 mm appoggiata a piano sulla mensola (Y 58.11 = riferimento di quota), linguetta posteriore 2 × 12 nella piastra, **2 viti M3 × 12 verticali dall'alto** a X 38.2 (Z 24.05 e 6.05), autofilettanti 10 mm nella mensola. Il foro di fissaggio Y 52 / Z 18.67 resta raggiungibile da un canale Ø6.5 aperto verso la ruota (serve un cacciavite lungo ~35 mm). Scheda v2: 24 × 18, chip TSL1401CL al centro (datasheet: 9.4 × 3.0 × 1.2, pixel 0.22 sotto la faccia, linea di pixel 0.305 fuori dal centro verso i pin 5–8), 3 fori M2 autofilettanti (posizioni da confermare), connettore 6 poli a ingresso laterale sul bordo anteriore; cavo giù davanti alla mensola, sotto di essa, fino alla tacca della piastra. Chip alla stessa quota (2.5 mm sotto il fondo della coda di topo) e sullo stesso asse. **Gioco scheda ↔ ruota 2.7 mm** (era 0.6), slitta 1.6, mensola 1.5; rullo inferiore ≥ 1.5. Verifica completa (`strumenti/verifica_finale_profiler.py`): nessuna interferenza, estrazione della slitta libera per 45 mm, viti raggiungibili, fascio e forcelle liberi; (gli avvisi sulla linea Ø2/Ø3 a Z 78–83 sono stati risolti il 31/10 allargando il foro di uscita). Slitta 2.57 cm³. **La scheda Hiwonder non si monta sulla slitta v2.** Sorgenti: `cad/FlylineProfiler_RazorGauge.scad` (moduli `pedestal`, `sensor_tray`, `sensor_pcb`), `strumenti/build_profiler.py`. Immagine `integrazione_profiler/mensola_slitta_prima_dopo.png`.
- **Sede laser v3 per Picotronic LFD650-1-12(9x20) (29/10/2026, pezzo unico NON ancora ristampato)**: la sede Ø4 stampata non dava una direzione certa e stabile (laser che balla nel perno Ø4.3, grani M3 autofilettanti nel PA12 che si spingono a vicenda, 1/8 di giro = 0.3° = 0.8 mm sul chip). Calcolo ABCD: **1° di inclinazione del laser = ~2.8 mm sul chip** (il decentramento di ~4 mm del 27/10 = ~1.4°); per ±0.5 mm serve ±0.2°. Scelta utente: soluzione definitiva, laser **annegato in epossidica** una volta allineato; solo MJF + minuteria. Laser: Picotronic **LFD650-1-12(9x20)** (Order 70103984, datasheet REV 22 in `integrazione_profiler/LFD650-1-12_9x20_datasheet.pdf`): 650 nm classe 2, 0.5–1 mW, ottone Ø9 × 20, fronte piano con foro Ø6, apertura 3 mm, 3–12 V / 25 mA, fascio ~3 mm (ellittico con 3 lobi nelle immagini del produttore), divergenza 1 mrad; **involucro a potenziale VDD (+)**, filo rosso +, nero GND. Sede (`laser_block` / `laser_cuts` / `laser_cap` in `cad/RazorGauge.scad`): **appoggio a cono 90°** sul bordo anteriore Ø9 (punto di rotazione all'uscita del fascio, Z_LF = Z_L1 + 9 = 114.2: laser abbassato di 6 mm, Z_TOP invariato), foro Ø11 (inclinazione max ±2.9°), **2 grani M3 × 8 in nylon a 90°** a 14 mm dalla faccia in **inserti a caldo M3** (foro Ø4 × 6): frontale dal foro del coperchio, laterale dal fianco lato rullo (grani in nylon perché l'involucro è a +3.3 V: un attrezzo a massa sul grano cortocircuiterebbe i 3.3 V del master); **O-ring 8 × 1.5** sul corpo a 8 mm dalla faccia come ritorno; **tappo** (2 M3 in inserti) che preme il laser sul cono con un O-ring 6 × 1.5, con foro fili e 2 fori Ø1.6 per colare la resina sopra l'O-ring. Foro del carrello L2 da Ø14 a **Ø17** (fascio ~15.6 mm). JP2 su 3.3 V. Firmware: nessuna modifica necessaria (`k` per misura assorbe la potenza media); tempo di accensione da verificare con impulsi 5–100 µs. **Allineamento guidato**: modulo `master_razorgauge/gauge_align.inc` (istruzioni in `master_razorgauge/ALLINEAMENTO_LASER.md`), pagina `http://<ip>/align` con istruzioni esplicite (quale grano, verso, ottavi o sedicesimi di giro; ricerca dei due punti all'80% per la direzione di traverso; controllo di stabilità prima della resina). **Da includere nello sketch (3 righe)**: controllato (sintassi) sulla 0.6.0 e sulla 1.0.1-alpha, logica della pagina provata in simulazione. Verifica del modello (`integrazione_profiler/verifica_sede_laser_29-10.txt`): nessuna interferenza (20 parti), fascio Ø16 libero da chip a L2 e cono fino a L1, carrello libero. Pezzo unico 118.4 cm³ (mensola + sede laser), coperchio 8.19, carrello 3.24, tappo laser 0.69 (nuovo), kit 138.7 cm³. Immagine `integrazione_profiler/sede_laser_v3.png`.
- **Fondo delle gole delle guide a J troppo sottile (30/10/2026, segnalato da Stefano; pezzo unico NON ancora ristampato)**: errore di modellazione in `build_profiler.py`: l'invito svasato alle due facce era un unico inviluppo convesso tra le facce, quindi la gola risultava allargata di 0.7 mm su tutta la lunghezza e il fondo era sceso a **0.81 mm**; inoltre il fondo tondo R1.5 non c'era (fondo piano). Correzione: invito solo negli ultimi 1.5 mm di ogni faccia e mai sotto il fondo della gola; fondo davvero tondo R1.5 (la Ø3 ci sta, fondo 0.3 sotto la linea come prima); **fondo ispessito a 3.1 mm** (sotto fino a Y 63.5) dove sotto non c'è niente: guida lato rullo Z 2.1–9.0 (fuori dalla scheda e dalla sua corsa di estrazione), guida lato ruota Z 30–32.7, poi segue la ruota con 1.5 mm di gioco radiale fino a 1.5 mm di fondo verso Z 36. Sopra la scheda (Z 9–13) il fondo resta 1.5 mm (sotto ci sono i componenti 0603 a ~1 mm). Verifica completa ripetuta: nessuna interferenza, estrazione slitta libera, fascio libero. Pezzo unico 118.8 cm³, kit 139.2 cm³. Immagine `integrazione_profiler/guide_J_fondo_prima_dopo.png`.
- **Controllo contro le lastre CNC (30/10/2026)**: nuovo `strumenti/verifica_piastre_cnc.py`, eseguito sul pezzo unico con il fondo delle guide J ispessito: **tutto OK** (`integrazione_profiler/verifica_piastre_cnc_30-10.txt`). Note: il gioco minimo con la ruota CNC è 0.78 mm, sull'estremità lato ruota della guida J (Z 37); era già così prima di questa modifica. Le 4 tasche cieche dal retro (Z −10.3 / 53.4, Y 129 / 173.5, profonde 5.6) vengono dal pezzo originale e non toccano i fori della piastra.
- **Ruote encoder intercambiabili + ruota montabile (30/10/2026, richiesta di Stefano; pezzo unico NON ancora ristampato)**:
  - **Fondo della zona encoder riportato a X 0–3 come nel FlylineProfiler originale** (prima X 4.22–7.22 con sede Ø53 sul retro): l'encoder appoggia sul retro del pezzo (X 0), il corpo Ø38.2 × 34.3 entra nel foro Ø42 della piastra in alluminio (gioco 1.9 radiale; dietro non c'è niente nel raggio di 1 mm + 10 mm per il cavo). Davanti c'è una **tasca Ø38 (era Ø40, vedi 'Difetti di mesh') da X 7.22 a X 3** per le teste delle 3 viti M3×6 dell'encoder (viti invariate: 3 mm di fondo + 3 nell'encoder) e per il mozzo Ø29 della ruota originale. Fori Ø22, 6 × Ø3.3 e finestre ad arco invariati.
  - **Vanno bene tutte e due le ruote sullo stesso albero**: **originale** (`Stl_esterrni/Decoder+Ruota.stl`: disco Ø63.8 × 10, mozzo Ø29 × 10, battuta Ø44) montata come nell'originale, mozzo a 1.6 mm dal codolo → cerchio X 17.84–27.84 (0.6 mm dalla mezzeria, come nel FlylineProfiler); **CNC** `RG_ruota_encoder` → cerchio X 17.22–27.22 con la stessa regola del disegno: **10.0 mm dalla faccia anteriore del pezzo (X 7.22) alla faccia posteriore del cerchio**; il mozzo resta a 5.2 mm dal codolo, l'albero entra nel foro per 7.8 mm (prima 11.8) e i grani (X 13.83) sono sull'albero.
  - **Errore trovato (segnalato da Stefano): con la mensola del 28/10 la ruota non si poteva montare** — si infila in asse dal davanti, ma la parte anteriore della mensola (X 34–41.5, Z 20–30) e la vite della slitta a Z 24.05 erano sul suo percorso. Correzioni: scarico ruota (r 33.3) **passante fino al fronte della mensola** (`WHEEL_CUT_X` 12…45); **vite della slitta lato ruota spostata a Z 12.55** (`TR_SCREWS` [15.9, 9.0]): fuori dalla ruota e dal canale Ø6.5 del cacciavite (parete 1.6), fuori dalla proiezione del coperchio (accesso dall'alto); è una **M3×12 a testa svasata ISO 10642** a filo della slitta, perché sopra passa la spina del connettore (staccare la spina per svitarla). L'altra vite (Z 6.05, testa cilindrica) invariata. Slitta allungata di 0.5 mm a filo della mensola (2.60 cm³).
  - **Nuovi controlli di montabilità** in `strumenti/verifica_finale_profiler.py` (sezioni D3 e M, da rilanciare sempre): viti dell'encoder con accesso dal davanti; ruota CNC e ruota originale infilate in asse con slitta, scheda e viti montate (+0.3 mm); grani del mozzo raggiungibili radialmente (16 direzioni su 24); corridoio delle teste delle 8 viti pezzo → piastra. Esito: **tutto OK** (restano solo i due avvisi noti sulla linea Ø2/Ø3 a Z 78–83). Giochi minimi: ruota CNC 0.80, ruota originale 0.72 (entrambi sull'estremità della guida J lato ruota), slitta 1.6. Lastre CNC (`verifica_piastre_cnc.py`): **tutto OK** (`integrazione_profiler/verifica_piastre_cnc_30-10.txt`).
  - Pezzo unico 120.1 cm³, kit 140.5 cm³. Assieme con la ruota CNC reale dallo STEP. Immagine `integrazione_profiler/ruote_encoder_intercambiabili.png`.
- **Forcelle troppo lasche nelle sedi, vibrano al passaggio della coda di topo (30/10/2026, segnalato da Stefano; pezzo unico e tappi NON ancora ristampati)**: la forcella è guidata solo nel tratto basso della sede (prisma 16 × 12 in sede per 1.75 mm senza cavo, ~3 mm con cavo 0.5, ~6 mm al massimo; sotto c'è il rullo, sopra solo il cilindro Ø8 dentro la molla) con 0.3 mm per lato, più lo stelo M5 nel foro Ø5.5 del tappo. Restringere la sede rischierebbe di farla impuntare (tolleranze MJF + forcella stampata). Soluzione: **linguette elastiche anti-gioco** ricavate nelle pareti di ogni sede (`build_profiler.py`, `FLX_*`): una sulla **parete anteriore** (larga 7, spessa 1.0, lunga 14, libera in basso, dente 0.7 → 0.4 mm di interferenza) che spinge la forcella verso la piastra, e una sulla **parete esterna lungo il cavo** (larga 15.4, due denti da 0.6 → 0.3 mm, sui due bracci) che la spinge verso la parete interna. Denti a 0.2–3.6 mm dal fondo della sede con rampa in alto (la forcella si infila dall'alto come prima, la linguetta si apre di 0.3–0.4 mm). Forza stimata ~0.4 N (X) e ~0.7 N (Z) per linguetta → gioco zero anche se la stampa viene più larga o più stretta di qualche decimo. **Tappo dei blocchi guida: foro dello stelo Ø5.2** (era 5.5) per una guida più precisa in alto (se stretto, passare una punta Ø5.2). Verifica: i denti premono la forcella su tutta la corsa (cavo 0 → 3 + 2 mm), spazio libero per la flessione, forcelle/rulli/bulloni liberi, tutte le altre verifiche e le lastre CNC invariate (OK). Pezzo unico 119.5 cm³, tappo 2.83 (×2), kit 139.9 cm³. Immagine `integrazione_profiler/linguette_antigioco_forcelle.png`. Se servisse più o meno precarico: `FLX_BUMP`/`FLX_BUMP_Z` (interferenza) o `FLX_T` (rigidezza).
- **Luce ambiente sul chip + sportellino frontale scorrevole (30/10/2026, segnalato da Stefano; da stampare)**: calcolo di visibilità (400k raggi dal chip, assieme completo): il chip vedeva l'esterno per l'**11% dell'emisfero** (7–15% lungo la fila di pixel), tutto dalla **fessura frontale di carico della coda di topo** (tra scheda, Y ~64, e fondo del coperchio, Y 76.4), con angoli da pochi gradi a ~45°; lati e retro già schermati. Stima: in ufficio ~2% della luce del laser per tempo di integrazione = impulso, ma il TSL1401 integra l'ambiente per tutto il tempo di integrazione (×10–100) ed è più sensibile nel vicino IR (finestre, alogene); il frame di buio toglie solo la parte costante. Diaframmi fissi compatibili col carico frontale avrebbero ridotto solo ~metà. Scelta di Stefano: **sportellino in MJF scorrevole su due guide, senza attrezzi** (`strumenti/build_sportello.py`, `FlylineProfiler_RazorGauge_sportello_luce.stl`, 6.99 cm³): lastra 2 mm a X 39.75–41.75, Y 63.5–101, Z −18.5…61.6, con due fianchi lungo la coda di topo (fermano i raggi radenti lungo il canale; lato ruota da X 30.5) e due incavi in basso (spina + cavo del sensore, testa della vite M3 della slitta). Guide a T nel pezzo unico sul fronte dei due blocchi delle forcelle (`SH_*` in `build_profiler.py`: Z −12.45 e 55.55, Y 86–111.8, piede in basso = fermo), graffe sullo sportellino con 0.25 di gioco, **2 nottolini elastici** (linguette 4 × 8 × 1.0 nella lastra, dente 0.45) che scattano negli incavi delle guide **da chiuso e da aperto (+13 mm)**. Non si premono: basta spingere/tirare lo sportellino dalla presa. **31/10/2026**: incavi delle guide con fianchi a 30° (prima a spigolo vivo: ~1.6 N per nottolino e possibile impuntamento) → ~0.7 N per nottolino (~1.4 N in tutto), ampiamente sopra il peso dello sportellino (~0.07 N) che resta su da aperto. Da chiuso lo tiene giù anche la gravità; lo scatto in basso evita solo che vibri sul gioco di 0.25 delle guide. Aperto: fondo a Y 76.5, sopra i labbri delle guide J → si carica la coda di topo dal fronte; sfilandolo verso l'alto si toglie (serve per montare la ruota encoder e conviene per estrarre la slitta). Verifica (`verifica_finale_profiler.py`, sezione S): **luce diretta sul chip 0.0000 / 0.0000 / 0.0008 dell'emisfero** (prima 0.069 / 0.108 / 0.144), scorrimento e sfilamento senza contatti, nottolini liberi negli incavi e in presa a metà corsa, slitta estraibile a sportellino aperto; tutto il resto e le lastre CNC invariati (OK). Pezzo unico 120.6 cm³, kit 148.0 cm³. Immagini `integrazione_profiler/luce_ambiente_sezione.png`, `sportellino_luce.png`. Consigliato comunque (altra sessione): frame a laser spento alternati e tempo di integrazione minimo; eventuale filtro passa-banda 650 nm sul chip.
- **Difetti di mesh nella tasca dell'encoder e altrove (30/10/2026, segnalato da Stefano: "linee" nella tasca circolare)**: controllo completo della mesh (spessore del materiale dietro ogni faccia, piani, pareti, triangoli). Trovati e corretti, tutti miei:
  1. **Lamelle lungo la parete della tasca**: la tasca anteriore aveva **r 20, esattamente il raggio interno delle 4 finestre ad arco (r 20–26)** → due cerchi uguali con tassellature diverse = 151 facce di lamelle < 0.3 mm (28.8 mm²), le "linee". Provati r 21–23: il cerchio taglia di sbieco gli spigoli delle finestre (cunei 0.05–0.4 mm). Scelto **r 19 (tasca Ø38)**: anello pieno di 1 mm verso le finestre, niente lamelle; teste delle viti dell'encoder a 1.25 mm dalla parete, mozzo Ø29 della ruota originale libero.
  2. **Anelli a gradini sul bordo**: l'invito era fatto a 5 gradini da 0.1 mm → sostituito da un **cono vero 0.5 × 45°**.
  3. **Gradino nella finestra lato mensola**: la mensola parte da X 2.82 e riempiva un angolo della finestra sinistra (faccia a X 2.82) → finestre di nuovo passanti fino alla faccia anteriore.
  4. **Inserti del tappo laser**: a r 10 dall'asse il foro Ø4 usciva dal mozzo Ø22 (pareti 0.03–0.1) → **bossoli Ø8** attorno ai due inserti (`laser_block` in `cad/RazorGauge.scad`).
  5. **Linguette anti-gioco delle forcelle**: l'invito 0.8 sul bordo inferiore delle sedi le lasciava spesse 0.2 mm in fondo → invito tolto (la forcella entra dall'alto).
  6. **Mensola**: filo di 0.4 mm dove lo scarico della ruota esce dal piano della mensola → gradino a 1 mm; cuneo 0.15–0.4 mm tra il canale del cacciavite (Ø6.5) e lo scarico della ruota → tolto.
  Esito: materiale < 0.5 mm in tutto il pezzo **0.50 mm²** (prima ~82), solo piccoli residui già presenti nell'STL originale del FlylineProfiler; zona encoder spessore minimo 0.93 mm, solo piani X 0 / 3 / 7.22 e il cono dell'invito. Nuovo controllo **Q** in `verifica_finale_profiler.py`. Tutte le altre verifiche (montaggio, ruote, sportellino, forcelle) e le lastre CNC: OK. Pezzo unico 121.3 cm³, kit 148.7 cm³. Immagine `integrazione_profiler/tasca_encoder_prima_dopo.png`.
- **Scritta RazorGauge sul coperchio alzata (30/10/2026, richiesta di Stefano)**: centro da z 62 a **z 76** (coordinate torre; scritta da Y 117 a 164 nel pezzo montato), sopra lo sportellino anche da aperto (cima a Y 114). Sotto il foro di accesso al grano frontale del laser (z 128.2) e sopra l'asola della vite del carrello. Da ristampare il coperchio (era già nel kit per la sede laser v3).
- **Logo RazorBlade sullo sportellino (30/10/2026, richiesta di Stefano)**: dal PDF vettoriale di Stefano (`logo/RazorBladeFlyLines.pdf`) → `strumenti/logo_da_pdf.py` (raster 1200 dpi, contorni OpenCV con i fori delle lettere) → `logo/logo_razorblade_76mm.json`. **Inciso 0.6 mm come la scritta RazorGauge del coperchio** (prima versione in rilievo, cambiata su richiesta), **largo 76 mm (alto 14.6), centrato** lungo la lastra (Z 21.55, asse di misura), Y 72.8–87.4 (sotto i nottolini, sopra gli incavi); solchi allargati 0.05 per lato; sotto il logo restano 1.4 mm di lastra (nessun passaggio di luce). Solchi delle linee ~0.7–0.8 mm, delle lettere ~0.5–0.6 mm, lettere alte ~3.3 mm: al limite delle incisioni MJF. Sportellino 6.90 cm³. Verifiche invariate (OK). Immagine `integrazione_profiler/sportellino_logo.png`.
- **Foro di uscita della coda di topo dopo la ruota allargato (31/10/2026, richiesta di Stefano)**: gli avvisi 'Linea Ø2/Ø3' delle verifiche venivano dal foro chiuso di uscita del blocco ORIGINALE (Z 78.5–83.4): 3.0 × 2.8 mm (Y 65.6–68.4), fondo che scende ~4°; identico nel FlylineProfiler originale. La Ø2 dritta toccava il soffitto di 0.5 (in realtà scendeva di <1° e passava), la **Ø3 passava schiacciata di ~0.2 mm e strisciando**. Ora **3.6 × 3.7 mm** (Y 65.3–69.0; pareti 0.9 sopra, 1.4 sotto), spigoli R0.6, fondo raccordato a rampa da Z 69 (niente gradino), smusso all'uscita. Controllo F di `verifica_finale_profiler.py` rifatto sul percorso reale: dritta tra rullo inferiore e ruota, poi filo teso su ruota e fondo della guida di uscita. Esito: **Ø0.5 e Ø2 passano dritte, Ø3 passa libera con una piega di 2.9°** appoggiata sul fondo della guida; nessun avviso residuo. Tutte le verifiche e le lastre CNC OK. Immagine `integrazione_profiler/avviso_linee_uscita_ruota.png`.
- **Copertura della gola d'uscita (a sinistra guardando dal fronte, lato ruota) rimovibile (31/10/2026, richiesta di Stefano)**: la gola chiusa del blocco originale trattiene la coda di topo durante la scansione ma per inserirla bisognava infilarla. Tolto dal pezzo unico il tratto sopra la gola (X 16 – fronte, Y 67.4 – 69.9, Z 77.9 – fine, compreso l'invito originale del soffitto); al suo posto il **tappino** `FlylineProfiler_RazorGauge_tappo_uscita.stl` (0.30 cm³, `strumenti/build_tappo_uscita.py`): a U rovesciata, rifà il soffitto a Y 69.0 (foro 3.6 × 3.7 come prima, soffitto spesso 2.4: sporge 1.5 sopra il braccio), **2 perni Ø2.4 nei fori Ø2.6** delle due pareti, **clip elastica** sul fronte del braccio con dente sotto il braccio (Y 63.9). Si mette premendo dall'alto (la clip scatta), si toglie tirando in avanti la clip e sollevando; senza tappino la gola è aperta in alto per tutta la lunghezza e la coda di topo si cala dall'alto. Verifiche nuove (sezione TU): tappino sfilabile in alto senza toccare nulla, clip in presa, gola aperta senza tappino; linee Ø0.5/2/3 come prima (Ø3 piega 2.9°). Corretto anche il controllo del laser nella sede (non segnala più il contatto voluto sul cono). Tutte le verifiche e le lastre CNC OK. Pezzo unico 121.1 cm³, kit 148.7 cm³. Immagine `integrazione_profiler/tappo_uscita.png`.
- **Revisione completa della slitta (31/10/2026, richiesta di Stefano)**: controlli su spessori, fori, posizionamento e montaggio. Corretti:
  1. **Foro della vite M3 lato rullo a 0.3 mm dal bordo** della slitta (y 15.5, bordo a y 17.5) → spostato a **y 14.3** (parete 1.6; testa a 1 mm dalla spina del connettore, cacciavite dall'alto libero). Aggiornato anche l'incavo dello sportellino sopra la testa.
  2. **Svasatura della vite sotto la spina a 0.36 mm dal bordo anteriore** → slitta allungata di 1 mm oltre il fronte della mensola (bordo 1.36).
  3. **Ripetibilità quando si rimette la slitta**: fori delle viti nella slitta da Ø3.4 a **Ø3.2** e gioco laterale della linguetta nella piastra da 0.25 a **0.15** → posizione del chip ripetibile entro ~±0.1 mm (importante perché il frame di riferimento è per pixel).
  Esito: slitta senza pareti < 1.18 mm; estrazione 45 mm, viti raggiungibili, sportellino, ruota: tutto OK. Nuovo controllo **Q2** (spessori di slitta, sportellino, tappino, coperchio, carrello) che ha trovato anche: **foro M3 frontale del carrello che sfondava nel foro centrale Ø17** (parete 0.01, effetto dell'allargamento del 29/10) → profondità da 5.5 a **4.1** (vite M3×6 invariata, 3.8 in presa, parete 0.8); nel logo inciso dello sportellino tolto l'allargamento dei solchi (creste tra le lettere meno sottili). Restano creste sottili solo dentro le scritte incise (logo e RazorGauge): dettaglio grafico, non strutturale. Da ristampare anche il carrello (era già nel kit). Immagine `integrazione_profiler/slitta_revisione.png`.
  Note (non modificate): la quota del chip dipende da mensola + slitta 3.5 + PCB 1.6 (MJF ±0.2: col fascio collimato non cambia la misura); il chip guarda in alto sotto la coda di topo, quindi raccoglie polvere e residui del rivestimento → pulirlo estraendo la slitta; eventuale vetrino/filtro 650 nm da valutare.
- **Sensore su slitta estraibile** (`FlylineProfiler_RazorGauge_slitta_sensore.stl`, 0.74 cm³): la scheda si avvita alla slitta al banco (4 viti M2 con dado sotto, fori della scheda a 0 e +6.5 mm lungo il cavo); la slitta entra da davanti sotto il cavo (anche con il cavo montato), la linguetta posteriore va in battuta nella sede sul lato piastra, una vite M3 verticale dall'alto nella linguetta anteriore la blocca sulla colonnina. Verificato: estrazione libera per 40 mm, nessun contatto con ruota (anche se larga fino alla piastra), rullo, cavo.
- **Interasse ruota encoder ↔ laser = 28.00 mm (8/10/2026)**: punto di misura (asse laser / linea di pixel) spostato da Z 21.00 a **Z 21.55** (+0.55 verso la ruota): `ZC` nello SCAD integrato, `ZS` in `build_profiler.py`, `ZM` in `make_assembly_profiler.py`. Firmware master **0.5.5**: `MEAS_OFFSET_CM` = **2.800**. Minimo possibile ~27.5 mm (limite: bordo della scheda Hiwonder ↔ ruota): 28.0 scelto per margine. Spostati con la torre: sede linguetta slitta, nervature e pieni sul retro; guida J lato rullo allungata a Z 4.8–13.05, lato ruota accorciata a Z 30.05–37.8 (fascio Z 14.55–28.55 libero con 1.5 mm). Verificato: scheda ↔ ruota 0.62, slitta ↔ ruota 1.02, J ↔ ruota 0.49, fili ≥ 0.7 dal pezzo e ≥ 3.9 dalla ruota, fascetta ≥ 0.5 in estrazione, slitta/carrello/forcelle liberi, fascio libero, tutte le viti raggiungibili.
- **Verifica fissaggio slitta sensore (8/10/2026)**: linguetta posteriore nella sede del blocco: giochi 0.1 sopra/sotto, 0.15 ai lati, 0.1 in fondo, presa 4.5 mm su 4.8; appoggio anteriore: cima colonnina esattamente alla faccia inferiore della slitta (tz −5.50), linguetta anteriore appoggiata su tutta l'area; foro slitta Ø3.42, foro colonnina Ø2.5. **Corretto**: il foro della colonnina era profondo solo 6.5 mm → una M3 × 10 andava a fondo prima di stringere; ora **9.0 mm** (fondo a tz −14.5, 1.5 mm di fondo pieno): vite **M3 × 10** (8 mm in presa) o M3 × 8. Pareti: 1.5 mm attorno al foro nella colonnina, 1.05 mm attorno al foro nella linguetta (sotto la testa Ø5.5). Testa vite ↔ scheda 1.65 mm; accesso dall'alto libero. Trave di sostegno colonnina 2.5 × 5 × 32 mm. Pezzo unico 109.3 cm³.
- **Foro di fissaggio della zona encoder spostato (8/10/2026)**: dei 4 fori Ø3 originali della parte bassa (Y 3 / 57.97 × Z 18.7 / 80.4), quello a **Y 57.97, Z 18.67** era cieco (davanti c'è la sede della linguetta della slitta). Chiuso il tratto cieco e rifatto il foro passante a **Y 52.0, Z 18.67** (5.97 mm più in basso, stessa Z): libero dal davanti (accanto alla ruota encoder) e dal retro, pareti attorno ≥ 3 mm. Gli altri 3 fori invariati e passanti. Sulla piastra di supporto quel foro va spostato di conseguenza. Immagine `foro_fissaggio_spostato_retro.png`. Verifica completa ripetuta: invariata.
- **Piastra allargata sotto i blocchi guida (8/10/2026)**: i blocchi guida delle forcelle sporgevano ~2.2 mm oltre i bordi laterali della piastra. Bordi portati a filo dei blocchi: lato rullo **Z −14.6** (era −12.4), lato ruota **Z 57.7** (era 55.6) → piastra larga 72.3 mm nella zona torre. Fori di fissaggio ricentrati a 8.5 mm dai nuovi bordi: **Z −6.1 e 49.2** (Y 133 / 169.5 invariati) → rettangolo **55.3 × 36.5**; corridoi delle viti liberi (2.7 mm sopra lo stelo della forcella alla corsa massima). Verifica completa ripetuta: invariata. Correzione: l'allargamento lato ruota partiva da Y 41 e lasciava una striscia verticale (Z 55–57.7, Y 41–46) dentro il foro centrale Ø22 dell'encoder; ora parte da Y 69 (sopra la zona encoder): foro Ø22, 6 fori Ø3 e finestre ad arco liberi, identici all'originale. Pezzo unico 109.4 cm³. Sulla piastra di supporto i 4 fori vanno fatti con le nuove quote.
- **Alleggerimento finale (8/10/2026)** — pezzo unico da 118.8 a **107.2 cm³** (−11.6, −10%) senza cambiare funzioni, ingombri, sedi o giochi: (1) tasche sul retro con pelle anteriore 1.6 mm (era 2.0), nervature 2.2 (era 3.0), bordo 3.0 (era 3.5); (2) dietro al canale della torre le tasche arrivano alla faccia anteriore della piastra: resta la parete posteriore della colonna, 3 mm come le pareti laterali; (3) blocco di L1 alleggerito: mozzo attorno alla sede + razza anteriore larga 17.2 mm (inserimento della lente e scanalatura per la costola del coperchio) + 3 razze da 6 mm; (4) pareti dei blocchi guida delle forcelle sulle facce dei bracci 2.0 mm (erano 2.5). Rifatta la verifica completa: tutto invariato (linea, fascio, L1 inseribile dal fronte, coperchio, carrello, slitta, forcelle, fili, fascetta, accessi alle viti); nessuna nuova parete < 0.8 mm. Coperchio, carrello e slitta invariati.
- **Sede del corpo encoder (8/10/2026)**: con la piastra a 7.22 mm l'albero dell'encoder non arrivava più nella sede della ruota. Sul retro c'è ora una **sede Ø53 profonda 4.22 mm** centrata sull'asse ruota (Y 35, Z 49.55): il corpo dell'encoder (Ø38) appoggia sul **fondo spesso 3.0 mm come la piastra originale** (X 4.22–7.22), quindi albero, foro centrale Ø22, 6 fori Ø3 e viti dell'encoder sono **identici all'originale** (viti della stessa lunghezza di prima). Il diametro Ø53 comprende le 4 finestre ad arco (r 20–26) per non lasciare pareti sottili; attorno 4 mm di pieno. Verificato: pezzo chiuso, nessuna parete < 0.8 mm nella zona, encoder ↔ pezzo nessuna compenetrazione. Pezzo unico 118.8 cm³. Immagine `sede_encoder_retro.png`.
- **Rulli simmetrici rispetto al laser (8/10/2026)**: rullo inferiore (con il suo braccio originale) e spintore di misura spostati di altri 3.0 mm verso l'esterno: centro **Z −6.45** → **28.00 mm dal laser**, come la ruota encoder dall'altra parte (Z 49.55): appoggi della coda di topo a 56.00 mm tra loro, punto di misura in mezzo. In `build_profiler.py`: `DZ` = −16 (braccio spostato), `ZE` = −12.4 bordo piastra lato rullo (piastra larga 68 mm, il blocco guida sporge fino a Z −14.6 come prima), `Z_FORK` = (−6.45, 49.55); guida J lato rullo Z 1.8–13.05 (12.4 mm con l'invito); **fori di fissaggio lato rullo a Z −3.9** (8.5 mm dal nuovo bordo; l'altra coppia resta a Z 47.1 → interasse 51 × 36.5, simmetrico sulla piastra). Verificato: linea Ø0.5–3 libera da Z −30 a 76, rullo inferiore tangente al fondo linea (Y 66.91), J ↔ rullo spintore 0.48 (tutta la corsa), ↔ rullo inferiore 2.3, ↔ scheda 0.49; forcelle/carrello/slitta/fascio liberi; fori passanti e raggiungibili; nessuna parete < 0.8 mm nuova. Pezzo unico 122.3 cm³ (118.8 dopo la sede encoder). Immagine `rulli_simmetrici_fronte.png`.
- **Smussi di stampa (10/10/2026)** — solo su spigoli esterni liberi, nessun accoppiamento toccato:
  - Pezzo unico: angoli convessi del contorno piastra raccordati **R3** (come l'originale); smusso **0.6** sul perimetro della faccia posteriore (resta piana per l'appoggio) e della faccia anteriore dove non c'e' nulla attaccato; invito **0.5** sulla bocca della sede encoder Ø53; smusso **0.7** sugli spigoli verticali anteriori dei blocchi guida. Tolta anche una lamella da 0.15 mm sul bordo inferiore (Y 41) rimasta dallo spostamento del braccio del rullo.
  - Tappi: spigoli verticali anteriori 0.7 (uguali ai blocchi), bordo superiore 0.5 (escluso il lato davanti al foro M3), invito 0.3 sul dente di centraggio.
  - Coperchio: perimetro della faccia esterna 0.6, escluse le zone attorno ai 6 fori viti (parete 1.05).
  - Carrello: 4 spigoli lungo lo scorrimento 0.5 e perimetro delle facce di estremita' 0.3 (escluso lo spigolo vicino al foro M3 frontale).
  - Lasciati vivi: slitta del sensore (riferimento di quota del chip e sedi), fori, sedi, guide, facce di appoggio, tacca dei fili.
  - Verifica completa ripetuta: invariata (interferenze, fascio, carrello, slitta, forcelle, tappi, J, viti, fori). Nessuna nuova parete < 0.8 o fessura < 0.5. Volumi: pezzo unico 107.23, coperchio 8.19, carrello 3.85, slitta 1.16, tappo 2.82 (×2); kit 126.06 cm³. Script: `strumenti/build_profiler.py`, `build_tappo.py`, `smussi_coperchio_carrello.py`.
- **VERIFICA DEFINITIVA PRE-STAMPA (8/10/2026, 4 giri completi)** — su richiesta "il pezzo deve essere definitivo": controllati ogni spessore, foro, interferenza e movimento, ripetendo tutto dopo ogni correzione. Correzioni fatte in questa verifica:
  1. **Forcella lato misura non inseribile dal basso** (i bracci urtano il supporto del rullo inferiore dopo 3.5 mm) → blocchi guida **aperti in alto** con **tappo avvitato removibile** (`FlylineProfiler_RazorGauge_tappo_guida.stl`, ×2, 2.83 cm³: piastra 6 mm con foro stelo Ø5.5 alla stessa quota del vecchio cappello Y 111.8–117.8, dente 16.2 × 12.2 × 1.5 che centra il tappo nella sede, 2 fori Ø3.4). Fissaggio: **2 × M3 × 12 per tappo** nei fori Ø2.5 profondi 8.4 mm delle spalle del blocco (6 mm in presa). Forcelle inseribili/estraibili dall'alto per 44.4 mm, libere.
  2. **Gioco forcella ↔ guida 0.3 mm per lato** (sede 16.6 × 12.6, era 0.15): con MJF (fori ~0.1 più piccoli) e forcella stampata 0.15 rischiava di impuntarsi.
  3. **Sede linguetta posteriore della slitta**: gioco 0.25 sopra e ai lati (era 0.1), 0.1 sotto (riferimento di quota del chip). Labbro della sede accorciato di 0.5 mm: il bordo posteriore della scheda era a 0.2 mm (con le asole della scheda poteva toccare prima che la linguetta andasse in battuta) → ora 0.49.
  4. **Guide a J**: estremità accorciate di 0.3 mm (lato rullo, Z 2.1) e 0.8 mm (lato ruota, Z 37.0): giochi verso rullo spintore e ruota che girano da 0.48/0.49 a **0.78/0.79 mm**. Radice della J portata dentro la piastra (eliminate intaccature 0.1–0.3 mm all'attacco).
  5. **Vecchio foro (Y 57.97, Z 18.67) chiuso del tutto**: restava una fessura 0.4 × 4 mm davanti (polvere intrappolata).
  6. Spalle delle viti dei tappi: fondo pieno 1.9 mm sotto il foro (era 0.4). Foro M3 del carrello a z 3.8 (pareti 0.95). Finestre di alleggerimento del coperchio lontane dalle 6 viti.
  - **Esiti finali**: 5 pezzi a corpo unico e chiusi; nessuna fessura < 0.5 né parete < 0.8 mm nuove (restano solo spigoli originali: fori grani laser, invito della guida originale, vertici delle finestre ad arco dell'encoder; fondo della gola J 0.81 agli inviti; slitta 0.85 attorno alle asole M2; carrello 0.95). Nessuna interferenza statica (24 parti). Fori misurati sul modello: 10 fori piastra Ø3.30, 4 fissaggi Ø3.40, encoder Ø22.0, sede encoder Ø53 con fondo 3.0, 12 fori M3 Ø2.50 (coperchio 10 mm, colonnina 9 mm, tappi 8.4 mm). L1, laser, fascio, carrello −5/+6 con vite e asola, slitta+scheda+fascetta estraibili 45 mm (scheda ≥ 0.49, fascetta 0.50), forcelle + bulloni liberi su tutta la corsa (fine corsa alto: dado contro il fondo del blocco a d ≈ 5.4), linee Ø0.5–3 libere da Z −30 a 76, interasse 28.00/28.00, chip ↔ linea 2.50, fili ≥ 0.7, tutte le viti raggiungibili (anche le 4 dei tappi dall'alto). Giochi più stretti rimasti (statici, per costruzione): scheda ↔ ruota 0.63, scheda ↔ fondo J 0.49.
  - Pezzo unico **107.6 cm³**, coperchio 8.24, carrello 3.86, slitta 1.16, tappo 2.83 (×2).
  - **Montaggio forcelle**: (1) bullone+dado e rullo sulla forcella; (2) forcella nella sede dall'alto, rullo sotto; (3) molla sullo stelo; (4) tappo con il dente nella sede, stelo M5 attraverso il foro Ø5.5 avvitato nella boccola; (5) 2 viti M3 × 12.
- **VERIFICA PRE-STAMPA (8/10/2026)** — rigenerati tutti gli STL dai sorgenti (identici ai file in cartella) e controllati:
  - Stampabilità MJF: 4 pezzi a corpo unico, chiusi, nessun vuoto interno (niente polvere intrappolata), ingombri entro il volume MJF (pezzo unico 42 × 202.6 × 95). Spessori: corretti 3 punti sottili trovati → foro M3 del carrello accorciato a 5.5 mm (era 0.1 mm dal foro centrale), linguetta anteriore della slitta e colonnina allargate a 5.5 mm (pareti attorno al foro M3 da 0.55 a ≥ 1 mm), tolte due alette da 0.1 mm lasciate dallo spostamento del braccio del rullo inferiore. Restano solo spigoli dei fori grani del laser e dell'invito della guida originale.
  - Vite di bloccaggio della slitta spostata a tx 17 (X 39.2): prima il cacciavite dall'alto sfiorava il coperchio; ora corridoio libero Ø5.5.
  - Funzionale: nessuna interferenza statica tra 18 parti; laser, L1, L2 nelle sedi; carrello libero su −5/+6 mm e asola del coperchio allineata; slitta + scheda + fascetta estraibili per 45 mm; fascio Ø13 chip→L2 e cono L2→L1 liberi; linee Ø0.5–3 libere da Z −20 a 76 (oltre, l'uscita della guida originale lato ruota è identica all'originale: la linea scende); chip ↔ linea 2.50; forcelle + rulli + bulloni liberi su tutta la corsa; fori M2 scheda allineati; fili ≥ 0.7 dal pezzo; fascetta ≥ 0.5.
  - Accessi: viti coperchio (6), vite carrello, vite slitta, 4 fori di fissaggio, steli delle forcelle: tutti raggiungibili.
  - Firmware master 0.5.4 (`MEAS_OFFSET_CM` 2.855, poi 0.5.5 con 2.800): modifica di una costante; compilazione non eseguita qui (core ESP32 non scaricabile) → compilare in Arduino IDE.
  - Volumi: pezzo unico 120.95 cm³, coperchio 8.20, carrello 3.86, slitta 1.16.
  - **Minuteria per il montaggio integrato**: 6 × M3 × 10 (coperchio, autofilettanti nelle borchie); **4 × M3 × 12 (tappi dei blocchi guida, 2 per tappo)**; 1 × M3 × 6 (blocco carrello L2, dal davanti); 1 × M3 × 10 (blocco slitta, dall'alto nella colonnina); 4 × M2 × 8 + 4 dadi M2 (scheda sulla slitta, fori a ty 0 e 6.5); 3 grani M3 (laser); 4 × M3 + dadi per il fissaggio alla piastra di supporto (lunghezza = 7.2 + spessore piastra + dado); viti encoder come le originali (fondo della sede 3 mm); 1 fascetta 2.5 mm; dalle forcelle originali: 2 boccole filettate, 2 steli M5, 2 molle, 2 bulloni M5 + dado, 4 cuscinetti 625.
- **Guide a J tra i rulli (7/10/2026, allungate al massimo)**: due guide a J nel pezzo unico, **Z 4.8–12.5** (7.7 mm, tra rullo spintore di misura e fascio) e **Z 29.5–37.8** (8.3 mm, tra fascio e ruota encoder); il fascio utile (L2 Ø14, Z 14–28) resta libero con 1.5 mm di margine. **Gola larga 3.0 mm come la guida originale lato ruota** (fondo tondo R1.5), fondo **0.3 mm sotto la linea** (la linea appoggia sempre su ruota e rullo), parete alta verso la piastra (Y 72), labbro davanti (Y 69.9), spigoli R0.5, invito svasato 0.7 mm alle due estremità. Limiti che fissano la lunghezza (giochi minimi verificati): rullo spintore senza cavo 0.54 mm, ruota encoder 0.49, scheda durante l'estrazione della slitta 0.49, rullo inferiore 2.3, forcelle ≥ 3.4, bulloni ≥ 4.5. Linee Ø0.5 e Ø3 passano (Ø3 a gioco zero come la guida originale). Consigliato: levigare la gola. Immagini `guide_J_vista.png`, `guide_J_lato.png`, `guide_J_sezione.png`. Pezzo unico 120.9 cm³.
- **Vite di blocco del carrello L2 dal davanti (7/10/2026)**: l'asola sul fianco della colonna (lato spintore di misura) era coperta dal blocco guida della forcella → vite non raggiungibile. Ora la vite M3 × 6 entra **dal davanti, attraverso un'asola verticale nel coperchio** (Ø3.4, corsa −5/+6 mm come prima, a 6.5 mm dall'asse fuori dalla costola) e si avvita nel carrello (foro Ø2.5 profondo 5.5, a z +3.75 sopra il centro lente, ≥ 0.95 mm di parete sopra/sotto e ≥ 1.2 verso il foro centrale). Stringendo, il carrello si blocca contro l'interno del coperchio. Parametri `CAR_FRONT_SCREW`, `CAR_FS_Y/L/Z` in `RazorGauge.scad` (attivi solo nel file integrato; la torre standalone resta con la vite sul fianco). Asola laterale della colonna eliminata. Da ristampare: coperchio e carrello (oltre al pezzo unico). Accesso frontale verificato libero. Immagine `vite_carrello_frontale.png`.
- **Piastra a spessore unico (7/10/2026)**: tutta la piastra (anche la parte bassa con encoder, rullo inferiore e sensore) ha lo spessore della zona torre, **7.22 mm** (fronte piano a X 7.22, retro a X 0): la sagoma della piastra con tutti i fori e le asole è estrusa per l'intero spessore. Alleggerimento con tasche aperte sul retro su tutta la piastra (pelle anteriore 2 mm, nervature 3 mm, bordo 3.5 mm attorno al contorno e a ogni foro/asola), pieno sotto encoder (disco Ø42, retro piano per il montaggio), braccio del rullo inferiore, sede slitta/trave/colonnina e blocchi guida. Tacca dei fili e sede della linguetta della slitta rifatte nello spessore. (Encoder: vedi 'Sede del corpo encoder' — fondo 3 mm come l'originale.) Pezzo unico 119.6 cm³. Verificato: nessuna interferenza con slitta (anche estratta), scheda, ruota, encoder, albero, coperchio, carrello, rulli, forcelle; fili ↔ pezzo ≥ 0.7.
- **Porta rulli: forcelle ORIGINALI guidate (7/10/2026, definitiva)** — forcelle originali dell'utente (`porta_rullo_spintore_originale.stl`) **senza modifiche**: resta la sede della boccola filettata nel cilindro Ø8, lo stelo M5 si avvita nella boccola, la molla sta attorno a cilindro e stelo tra il ponte della forcella e il cappello; perno dei cuscinetti = bullone M5 + dado. Nel pezzo unico due **blocchi guida chiusi** (Z −3.45 e 49.55) con **sede rettangolare 16.3 × 12.3** (gioco 0.15, più stretta del rullo Ø16), aperta solo in basso, **da Y 85** al **cappello Y 111.8–117.8 con foro Ø5.5** (stessa quota del supporto originale → molla montata identica: 21.9 mm a cavo Ø2). Niente finestre né guide d'angolo. **[Superato dalla verifica definitiva: blocchi aperti in alto con tappo avvitato, gioco 0.3, montaggio dall'alto]** Montaggio dal basso, senza rullo: forcella nella sede, stelo avvitato nella boccola dall'alto attraverso il cappello, poi rullo e bullone (restano sotto la sede). Per la forcella sopra il rullo inferiore conviene smontare prima quel rullo (i bracci passano a ~1–2 mm dal suo perno). Verifica (con bullone e dado): libera da cavo assente fino a 3 mm + 2.2 mm; ponte e bracci in sede 3.4 mm (cavo 0.5) – 5.9 mm (cavo 3); oltre d ≈ 5.2 il dado tocca il fondo del blocco (fine corsa in alto). Forcella tenuta in due punti (sede in basso + stelo nel foro del cappello): inclinazione < 1°, rotazione impedita. Opzione: foro del cappello Ø5.2 per una guida più precisa dello stelo. Anime verso la piastra: centrale + due laterali. Pezzo unico 107.9 cm³.
- **Cavi del sensore (7/10/2026)**: il connettore originale della scheda è un XH 5 poli **a 90°** (foto utente): i fili escono paralleli alla scheda verso il lato dei fori = verso la ruota encoder → incompatibile (ruota e slitta); girato di 180° la spina sporgerebbe oltre il bordo verso il rullo inferiore. Deciso: l'utente dissalda e monta un **XH 5 poli VERTICALE (JST B5B-XH-A o equivalente) negli stessi 5 fori** (fila pin stimata dalla foto a ty ≈ 9.1, cioè ~6.4 mm dal bordo scheda lato connettore — DA MISURARE), spina XHP-5 con fili verso il basso. Ordine pin: GND, VCC5V, AO, CLK, SI. Modifiche: asola della slitta ty 5.3–12.8 (±8 in X); colonnina e trave dell'appoggio anteriore spostate a fianco della spina (ty 13.3–17.8 / 13.3–15.8, trave tz −16..−11), linguetta anteriore e vite M3 di bloccaggio (vedi verifica pre-stampa: ora a tx 17, ty 16.65). Verificato: connettore/spina ↔ pezzo ≥ 1.0 mm anche durante tutta l'estrazione della slitta (si sfila con la spina inserita), spina ↔ ruota 5.7, ↔ rullo inferiore 5.1; fili ↔ ruota ≥ 3.9, passano dalla tacca della piastra (Z 10.5–15.5, aperta dal bordo inferiore). Lasciare ~45 mm di gioco ai fili per estrarre la slitta. Immagini `xh_verticale_montato.png`, `xh_verticale_slitta_estratta.png`.
- **Fili saldati direttamente (7/10/2026, decisione finale)**: niente connettore sotto la scheda; i 5 fili (GND, VCC5V, AO, CLK, SI) entrano dal lato inferiore nei fori della fila a **ty 9.7 (misurata: 5.8 mm dal bordo scheda)**, saldati sopra con reofori tagliati < 1 mm, ed escono verso il basso fino alla tacca della piastra. Slitta: asola fili 13 × 2.8 (tx ±6.5, ty 7.9–10.7) e **aletta antistrappo** sotto la slitta (18 × 1.6, alta 6 mm, a ty 10.7–12.3) con **2 asole 1.6 × 3.1 per fascetta da 2.5 mm** a tx ±(5.9–7.5): la fascetta stringe il nastro dei fili contro l'aletta, chiusura sul lato fili. Slitta 1.14 cm³. Verificato: fili ↔ slitta 0.4, ↔ ruota ≥ 3.9; aletta+fascetta ↔ pezzo ≥ 0.5 mm durante tutta l'estrazione, fascetta ↔ rullo inferiore 3.8, ↔ ruota 7.1. Consigliato un connettore in linea sul retro della piastra per staccare il sensore. Colonnina/trave/linguetta anteriore a **ty 13.9+**, vite M3 di bloccaggio a (16, 16.15); trave ↔ rullo inferiore 1.8, ↔ braccio 1.6. Immagini `fili_saldati_fascetta.png`, `slitta_aletta_fascetta.png`.
- **Fori di fissaggio alla piastra di supporto** (viti M3 da davanti, lato cavo; 7/10/2026): 4 fori Ø3.4 passanti, rettangolo **48 (lungo il cavo) × 36.5 (verticale)** simmetrico sulla piastra: **8.5 mm da entrambi i bordi laterali**, coppia alta a **8.4 mm** dal bordo superiore, coppia bassa a 44.9 mm (coordinate Y 133 / 169.5 × Z −0.9 / 47.1). Accesso frontale libero (testa e cacciavite Ø7) anche con forcelle alla corsa massima (gioco 1 mm dalla testa M5). I 4 fori originali (A–D) sono chiusi; la piastra di supporto va forata col nuovo schema (`fori_fissaggio_fronte.png`).
- Ruota encoder confermata dall'utente (7/10/2026): circonferenza 200 mm, **spessore 10 mm** (X 17.22–27.22, centrata sull'asse del cavo). Giochi verificati: scheda 0.93, slitta 1.40, pezzo unico 1.58 mm.
- Rulli confermati dall'utente: Ø16 × 10 mm (inferiori e degli spintori). Verificati anche i rulli degli spintori sopra cavi da 0.5, 2 e 3 mm: liberi (gioco minimo 1.45 mm dalla colonna).
- Verificato al modello: nessuna interferenza con ruota, rulli, perni degli spintori, fascio, carrello (3 posizioni) e coperchio. Il cavo passa libero (il blocco a destra della ruota è quello originale).
- Piastra ispessita da 3 a 7.2 mm nella zona della torre (Y 76.4 - 177.9, tutta la larghezza): la faccia anteriore coincide con il retro della colonna. Altezza piastra originale (177.9); la torre sporge sopra di 24.7 mm.
- Finestra rettangolare originale chiusa.
- Alleggerimento: tasche aperte sul retro della zona ispessita (pelle anteriore 2 mm, nervature 3 mm allineate a pareti colonna e asse, bordo 3.5 mm, bossoli Ø9 sui fori Ø3, pieno sotto i supporti degli spintori).
- File: `FlylineProfiler_RazorGauge_pezzo_unico.stl` (107.6 cm³ dopo la verifica definitiva; `_tappo_guida.stl` ×2; piastra 7.22 alleggerita e allargata, guide a J, rulli simmetrici a 28 mm, sede encoder), forcelle originali `porta_rullo_spintore_originale.stl` (×2), `_coperchio.stl`, `_carrello.stl`, `_slitta_sensore.stl`; assieme da guardare `_assieme.glb/.3mf/.stl`; sorgente `cad/FlylineProfiler_RazorGauge.scad` (VIEW="column") + `strumenti/build_profiler.py` (unione con la piastra).
- Da chiarire: i 2 fori Ø3 della piastra a Z 6.55 (Y 126.8 e 174.85) finiscono sotto la colonna (quello a Y 174.85 è passante solo nella piastra).

## Collegamenti RazorGauge → ESP32 master
| Modulo | ESP32 |
| --- | --- |
| SI | GPIO26 (ex clock calibro) |
| CLK | GPIO27 (ex dato calibro) |
| AO | GPIO34 (ADC1, solo ingresso — mai ADC2 con WiFi) |
| Laser | GPIO25 via NPN (2N2222/BC337 + 1 kΩ) o MOSFET logic-level (AO3400 + 100 Ω + 100 kΩ) |
| VCC/GND | 3V3 / GND |
Il cavo analogico AO va tenuto corto (≤30–50 cm) e schermato.

## Firmware
- **Master ottico 1.0.0-alpha (10/10/2026)** — era numerato 0.6.0; versione per il primo avvio: ADC in mV calibrati + 2 letture/pixel, scarico veloce senza lettura (meno luce ambiente), buio alla stessa posa del laser, indici di qualità per misura, `gauge_stat [n]`, pagina di servizio **http://<ip>/diag** e JSON `/gauge`; protocollo WPF invariato. Algoritmo provato su simulatore (`strumenti/firmware_sim`). Procedura di prova: `PROCEDURA_PRIMO_AVVIO.md`. Obiettivo dichiarato dall'utente: **±0.01 mm**. È preliminare e non ancora collaudato sul banco; per compilazione e stato attuali vedere `FIRMWARE.md`.
- Master col laser — **v1.0.0-alpha** (USE_RAZORBOARD = 1: encoder su GPIO32/33 della scheda). Era numerata 0.5.3 → 0.6.0 → **rinumerata major il 19/10/2026**: il laser non è un passo avanti sulla linea col calibro, è un ramo diverso (0.x = era calibro, 1.x = era laser). **Ora sta nel repo** in `master_razorgauge/`, non più qui.
  - Calibro rimosso, RazorGauge integrato in un task FreeRTOS su core 0; il loop legge un buffer mediano (7 misure × 8 frame).
  - UI web rimossa; restano gli endpoint `/export` e `/encoder`.
  - Protocollo WebSocket verso l'app WPF **invariato** (verificato confrontando tutti i messaggi e i comandi). Unica aggiunta: messaggio `{"type":"gauge"}` inviato solo al client che manda comandi `gauge_*`.
  - Offset ruota encoder ↔ punto di misura: `MEAS_OFFSET_CM` = **2.800 cm** (master 0.5.5, 8/10/2026): asse ruota Z 49.55, asse laser / linea di pixel Z 21.55 → **28.00 mm** lungo la linea (calibro: 20.0 mm; il punto di misura è 8.0 mm più lontano dalla ruota, stesso verso). Valore da CAD: verificarlo al collaudo con un segno sulla linea.
  - Corretto il bug `goto_status completed:true` non inviato a fine GOTOPOS.
  - Nuovi comandi: `gauge_dark`, `gauge_ref`, `gauge_cal <mm>`, `gauge_calreset`, `gauge_exp <us>`, `gauge_status`, `gauge_profile`. Dati salvati in NVS (namespace `razorgauge`).
  - PPC encoder: invariato (`calibrate:<cm>`, `setppc:<val>`, `calibrate_reset`, EEPROM addr 4).
- `gauge_esp32/gauge_esp32.ino` — sketch di banco (solo sensore), non firmware attivo.
- `ccd_test/ccd_test.ino` — prova del solo modulo TSL1401 **senza laser** (24/10/2026): integrazione regolabile, profilo ASCII, test di linearità. **Provato sull'hardware**: sensore OK sui pixel 14–127, vedi sezione 24 ottobre.
- `ccd_lcd/ccd_lcd.ino` — prova del TSL1401 sull'**ESP-WROVER-KIT** con profilo, mappa dei pixel e cascata sul display (26/10/2026). **Provato sull'hardware**, vedi sezione 26 ottobre. Dal 27/10 integrazione minima 1 µs richiesti (~143 µs effettivi), vedi sezione 27 ottobre.
- ~~Solo controllo di sintassi con g++ su librerie simulate: mai compilato con il core ESP32 reale~~ → **compilato davvero il 19/10/2026** con l'`arduino-cli` dentro l'IDE Arduino (core esp32 3.3.8): master laser 82% di flash, banco 23% e 25%, master calibro 85%, slave 26%. **Provato sull'hardware: ancora no.**
- Slave — **0.6.7**, porting su ESP32 classico con diagnostica UART/Wi-Fi. **Nel repo** in `slave/`. Sul classico i GPIO 6-11 sono la flash, quindi i pin S3 della 0.5.1 non possono funzionare: non è un riordino.

## Da fare / punti aperti
- [x] ~~Eliminare a mano `firmware/RazorGauge_esp32s3`~~ → **fatto 19/10/2026**: archiviato in `_archivio_NON_USARE/`, e la copia nel repo (`gauge_esp32s3/`) è conservata come variante S3, non come firmware attivo.
- [x] ~~Leggere dal vecchio ESP32 il PPC attivo e annotarlo~~ → **fatto 19/10/2026. PPC attivo letto: 30.2100 (calibrato).** Verificato su linea graduata al metro, 18 punti da 100 a 1798 cm: un solo errore di scala dello **0.087%** (il salto da −1 a −2 cm è il troncamento `(int)`, non due regimi). **PPC corretto da impostare: 30.1837** (`setppc:30.1837`). Niente slittamento, nessuna dipendenza dal diametro — conferma sperimentale della decisione "contatto tangente → nessuna correzione".
- [x] **Pixel 0–13 del TSL1401 a 0 fisso** (24/10/2026): morti, esclusi nel master 1.0.1-alpha (`G_PIX_FIRST`) — vedi sezione 25 ottobre
- [ ] Ordinare un TSL1401 di scorta
- [ ] Banco `ccd_lcd` col laser: togliere la saturazione (trimmer in serie, laser pulsato dal kit o ND16), poi ombra di un filo sulla finestra — vedi sezione 27 ottobre
- [ ] Al primo avvio: misurare il tempo reale di una misura (8 frame) e rifare la tabella velocità/rumore
- [ ] Prova Archimede in etanolo su spezzoni dritti già scansionati (verifica indipendente del gauge)
- [x] ~~Ricontrollare l'interasse dei fori della scheda sensore~~ → **chiuso 25/10/2026** col disegno quotato del modulo (`immagini/516cwokwrwL._AC_SX679_.jpg`): scheda 25 × 24, fori Ø2 interasse **21** × passo 6.5, 2 mm dai bordi, chip 8.5 dal lato corto. Coerente con `sensor.stl` e con le asole 20–21.2.
- [ ] Pezzo unico da ristampare (mensola + slitta v2 + sede laser v3 + fondo guide J + zona encoder per le due ruote + linguette anti-gioco delle forcelle + guide dello sportellino, 28–30/10/2026) — stampare anche slitta, sportellino e tappino della gola d'uscita; i 2 tappi dei blocchi guida (foro stelo Ø5.2) sono facoltativi — prima confermare i fori di fissaggio della scheda sensore
- [ ] Includere `master_razorgauge/gauge_align.inc` nello sketch (3 righe in ALLINEAMENTO_LASER.md) e compilare
- [ ] Misurare lo spot del laser a 5–10 cm (serve ≥ ~1.3 mm per i cavi da 3 mm)
- [x] `MEAS_OFFSET_CM` = 2.800 cm da CAD nel master 0.5.5 — [ ] verifica al collaudo (segno sulla linea)
- [x] (master 0.6.0: corretto, slave invariato) Decidere se correggere nel master la conversione GOTOPOS verso lo slave (lo slave usa 30 impulsi/cm fissi; con PPC calibrato ≠ 30 il GOTOPOS si ferma nel punto sbagliato della stessa percentuale). Proposta: inviare `cm × PPC_attivo / 30`, solo nel master
- [ ] Acquistare: transistor, filtro ND OD 2–3 (solo se il sensore satura), passabanda 650 nm (~12×6×1 mm, sul chip), spine calibrate 0.5 / 1.5 / 2.0 / 2.5 / 3.0 mm
- [x] Ordinare la stampa MJF (stl/) — in stampa dal 4/10/2026
- [ ] Primo collaudo: compilare, flash, WiFiManager (AP "DiametroLinea_Setup", pwd 12345678), prenotazione DHCP, `gauge_dark` + `gauge_ref` senza cavo, collimazione, calibrazione con spine, verifiche al banco
- [ ] Collaudo laser vs calibro: stessa coda passata due volte (sistema vecchio 0.4.22 col calibro, poi sistema nuovo col RazorGauge), export CSV da `/export`, confronto per cm. Atteso rapporto calibro/laser ≈ 0.92–0.93 e STABILE lungo la coda (non uguaglianza)
- [ ] Confermare i diametri delle spine (domanda lasciata come commento nel documento)

## Sviluppi futuri (decisi di rimandare)
- **Velocità di scansione** (6/10/2026, non implementato per scelta): oggi 2 cm/s, limite ereditato dal calibro. Il firmware registra 1 punto/cm; il RazorGauge fa ~1 misura ogni 35 ms (8 letture) e il punto è la mediana delle ultime 7 misure (~0.25 s). **[25/10/2026: probabilmente ottimistico — con 2 letture ADC/pixel a ~43 µs servono ~90 ms per misura e ~0.6 s per punto; vedi sezione 25 ottobre, tabella da rifare coi tempi misurati.]**
  | Velocità | Media | Cavo per punto | Rumore atteso |
  | --- | --- | --- | --- |
  | 2 cm/s (oggi) | 8 × 7 | 0.5 cm | ±3–5 µm |
  | 4 cm/s | invariata | 1 cm | ±3–5 µm |
  | 8–10 cm/s | 4 × 5 | ~0.8 cm | ~±5–7 µm |
  | > ~16 cm/s | — | — | limite motore (FAST 12000 Hz) |
  Coda da 30 m: 25 min a 2 cm/s, ~12 a 4 cm/s, ~5 a 10 cm/s. Da toccare: `TARGET_SCAN_SPEED_CMS` (master), limite `SETHZ` 200–3000 Hz (slave, 3000 Hz ≈ 4 cm/s), `GAUGE_FRAMES_PER_MEAS` / `GAUGE_BUF_SIZE` (master). Idea: renderli impostabili dall'app WPF con comandi. Verificare al collaudo le vibrazioni laterali del cavo nella guida.

## Scheda controller (RazorBoard) — in corso
Cartella `scheda/`. Stato: **schema + layout PCB v0.1 completati** (175 × 125 mm, 2 strati, tutto a foro passante). DRC KiCad: 0 errori, 0 connessioni mancanti. Gerber + foratura in `scheda/produzione/RazorBoard_gerber.zip`. Non ancora ordinata.
- Specifiche decise: ingresso 24 V (fusibile 5x20 1A, 1N5822, TVS P6KE33CA) → Traco TSR 2-2450 (5 V 2 A) con jumper per 5 V esterno; zoccoli per due ESP32 DevKit V1 30 pin (master e slave, WROOM-32 — lo slave S3 è stato sostituito da un DevKit V1 CH340C), file a 25.4 mm; 1N5819 in serie al VIN di ciascun modulo.
- Encoder LPD3806-600BM-G5-24C (NPN OC, 5 V): pull-up 4.7k a 3.3 V, RC 1k/10nF, 74HC14 a 3.3 V (doppia inversione) → **GPIO32/33** (non più 12/13: cambiare ENCODER_DATA_PIN/CLOCK_PIN nel master quando si passa alla scheda).
- TB6600 a catodo comune: 74HCT245 a 5 V, R 100 ohm in serie, LED su PUL/DIR/ENA; ENA con pull-up (motore libero all'accensione). Morsetto con +5V per eventuale anodo comune. Il TB6600 si alimenta direttamente dal 24 V.
- RazorGauge: morsetto 8 poli (3V3, GND, SI, CLK, AO, LASER+, LASER-, calza), R serie 100 ohm, clamp 1N4148 su AO, 2N7000 per il laser, jumper 3.3/5 V per il laser. Cavo schermato max 50 cm.
- Pulsanti SCAN/FAST_S/FAST_O (slave) e WIFI_RST (master) a bordo + morsetto, pull-up 10k, RC 1k/100nF.
- UART master↔slave su pista con R 470 ohm, header debug.
- Montaggio: solo PCB, componenti a foro passante saldati a mano. Ingombro libero.
- Netlist dello schema verificata identica alla netlist sorgente (`scheda/script/board_def.py`); schema rigenerabile con `script/gen_sch.py`.
- Slave attivo 0.6.7 su ESP32 classico: PUL/DIR/ENA GPIO25/26/27, pulsanti GPIO32/33/34, UART GPIO16/17 e diagnostica Wi-Fi → `slave/slave.ino`. La versione S3 precedente è storica e non va usata al posto dello slave attivo.
- Master laser (1.0.0-alpha): `#define USE_RAZORBOARD 1` (scheda, encoder 32/33). Per tornare al vecchio cablaggio volante (encoder 12/13) mettere 0.
- Da verificare: interasse file del nuovo slave CH340C (atteso 25.4 mm), dimensioni dei moduli per la serigrafia.
- Layout: moduli con USB sul bordo superiore, aree senza rame sotto le antenne, morsetti su bordo inferiore (encoder, RazorGauge, TB6600, pulsanti) e sinistro (24 V, 5 V ext), pulsanti a destra, fori M3 agli angoli; piste di potenza 1 mm, segnali 0.4 mm, piani GND su entrambi i lati. Sbroglio con Freerouting 1.9; pipeline rigenerabile con `scheda/script/run_all.sh` (KiCad 7 + Java).
- Viste 3D: `scheda/immagini/RazorBoard_3D_iso/top/morsetti/retro.png` (texture reale dei layer + modelli semplificati dei componenti; script `scheda/script/render3d.py`, pyvista). Ingresso fili dei morsetti verso il bordo scheda.
- Prossimo passo: revisione visiva (aprire RazorBoard.kicad_pcb in KiCad 7+), verifica del verso d ingresso fili dei morsetti, ordine PCB.

## Scheda sensore TSL1401CL v1 (29/10/2026) — BOZZA, fori di fissaggio da definire
Cartella `scheda_sensore/` (KiCad 7 generato da `script/`: `sens_def.py` unica fonte, `run_all.sh` rigenera tutto). Sostituisce il modulo Hiwonder sulla slitta v2 del pezzo unico.
- 24 × 18 mm, 2 strati, 1.6 mm, tutto SMD lato TOP, montaggio JLCPCB (Economic). TSL1401CL **C2802316** Extended, montabile da JLCPCB **con pre-ordine** (verificato su jlcpcb.com il 29/10); 100 pezzi LCSC a ~21.82 $.
- Circuito: TSL1401CL a 3.3 V, 100 nF + 10 µF, R 100 Ω su SI/CLK, carico 330 Ω su AO; buffer LMV321 (C7972) con offset: **Vout = 0.958·AO + 0.154 V** (sopra la zona morta ~70 mV dell'ADC ESP32); 100 Ω in uscita. Connettore JST GH 6 poli a ingresso laterale (C133065): 1 3V3, 2 GND, 3 SI, 4 CLK, 5 AO, 6 calza = J5 pin 1–5, 8.
- Footprint dal datasheet (fig. 9/10): origine = centro della linea di pixel (0.305 dal centro del package verso i pin 5–8), al centro scheda = asse laser; pixel 1 verso il fronte. Il CPL usa il centro del package.
- Lato ruota libero (fori), lato rullo: sotto la guida J solo 0603; U2 a 0.53 mm (diagonale) dallo spigolo della guida J anche in estrazione.
- DRC 0 errori / 0 connessioni mancanti. **Da fare prima dell'ordine:** decidere i fori di fissaggio (ora 3 aree vietate provvisorie), rigenerare, controllare rotazioni U1/U2/J1 nell'anteprima JLCPCB. Note d'ordine in `scheda_sensore/NOTE_ORDINE_JLC.txt` (ENIG + maschera nera consigliati, 2–3 schede montate, remark MSL 5a).

## Scheda controller versione SMD (RazorBoard SMD v0.2) — alternativa alla v0.1
**4/10/2026: PCB SMD v0.2 ORDINATO a JLCPCB (montaggio SMD in fabbrica) con i file di `scheda_smd/produzione`. STL della torre (tower, lid, carriage) in stampa MJF.** La v0.1 THT non viene prodotta.
Cartella `scheda_smd/`. Stesso circuito della v0.1 (netlist identica, verificata su schema e PCB) con componenti SMD montati in fabbrica (JLCPCB).
- 150 × 95 mm (v0.1: 175 × 125), 2 strati, DRC 0 errori / 0 connessioni mancanti. Fori M3 agli angoli (4,4)(146,4)(4,91)(146,91).
- In fabbrica (61 pezzi, 23 righe BOM, tutti lato TOP): 0603 R/C, MLCC 0805/1206 al posto degli elettrolitici (5 V: 3 × 10 µF 25 V C15850, basic — ex 22 µF C45783), polyfuse 1812 SMD1812P050TF/30 (0.5 A hold, 30 V) al posto del fusibile 5x20, SS34 (ex 1N5822), SMBJ33CA (ex P6KE33CA), B5819W (ex 1N5819), 1N4148W, 2N7002 (ex 2N7000), 74HC14D, 74HCT245D (SOIC-20W), LED 0603 (verde KT-0603G C12624, giallo KT-0603Y C2287, rosso KT-0603R C2286 — sostituiti C72043/C72038 per scorte basse). Resistenze LED portate a 1k (ex 2.2k).
- A mano (THT): morsetti, zoccoli ESP32, Traco TSR 2-2450, pulsanti, jumper JP1/JP2/J7.
- Codici LCSC verificati sul sito JLCPCB (01/10/2026). File: `produzione/RazorBoard_SMD_gerber.zip`, `_BOM_JLCPCB.csv`, `_CPL_JLCPCB.csv`.
- Da controllare nell'anteprima JLCPCB prima di confermare: rotazione/pin 1 di U3, U4, Q1 e polarità di D1–D10 (le rotazioni KiCad a volte differiscono da quelle JLCPCB).
- Note tecniche (TB6600, calza, jumper) sulla serigrafia lato BOTTOM.
- Rigenerabile con `scheda_smd/script/run_all.sh` + `produzione.py` (percorsi di lavoro /home/claude/board_smd).

## Contenuto della cartella
| Cartella | Contenuto |
| --- | --- |
| VERIFICA.md | rapporto della verifica completa del 6/10/2026 (esiti, rischi, controlli al collaudo) |
| stl/ | RazorGauge_tower / lid / carriage — da stampare |
| dxf/ | piante e sezioni 1:1 |
| cad/ | RazorGauge.scad (sorgente parametrico), RazorGauge_dxf_views.scad, sensor.stl (modello scheda, serve per l'assieme) |
| master/, slave/, master_razorgauge/, gauge_esp32*/ | Firmware canonico attivo, firmware ottico preliminare e sketch di banco; versioni e schede in `FIRMWARE.md` |
| immagini/ | tavola posizione sensore, anteprime, coperchio con nome |
| scheda/ | progetto KiCad della scheda controller THT v0.1 (schema, BOM, librerie, script) |
| scheda_smd/ | RazorBoard SMD v0.2: progetto KiCad, file JLCPCB (gerber, BOM, CPL), immagini, script |
| strumenti/ | simulazioni Python (metodo ad area, energia impulso), script tavole/sezioni, script che genera il master dall'originale, versione pesante v1 della torre |
| Claude outputs/ | file originali forniti (master.ino 0.4.22, slave.ino) e copie precedenti |

## Comandi utili
- Rigenerare un pezzo: `openscad -D 'PART="tower"' -o RazorGauge_tower.stl cad/RazorGauge.scad` (PART = tower | lid | carriage | assembly)
- DXF: `openscad -D 'VIEWSET="tower"' -o RazorGauge_tower.dxf cad/RazorGauge_dxf_views.scad`
- Simulazioni: `python3 strumenti/sim_fresnel_metodo_area.py` (numpy, scipy, matplotlib)

## Per riprendere con Claude
Apri una nuova conversazione collegando questa cartella e scrivi: "Riprendiamo RazorGauge: leggi STATO_PROGETTO.md".

---
## Struttura in alluminio e ruota encoder (2026-10-13) — FILE DEFINITIVI PER L'ORDINE
Cartella `piastra_alluminio/`. Sorgenti: `layout.py` (assieme), `fori.py` (unica fonte di fori/linguette), `disegni.py` (PDF), `step_export.py` (STEP), `build_viewer.py`.
- Lastre 6 mm, Al 6061: piastra verticale 314×227, mensola 89×116, base 314×165, piastrina presa IEC 56×41 sul retro (bordo posteriore della base). Fissaggi con linguette nelle asole (22.4×6.2 R1, gioco 1.2) + viti svasate M3×12 nei filetti nel bordo (foro 10, filetto utile ≥8).
- Presa IEC C14 a vite: foro 27.6×19.6 R1 (dima 27×19), 2 × Ø3.4 interasse 40, cover all'interno con le stesse viti.
- Alimentatore 24 V 150 W (183×49): asole 3.5 mm in angoli opposti, interasse 175×35 → 4 fori M3 sulla base (B14–B17, entrambe le diagonali).
- Pulsanti Ø12 (filetto 12 mm): fori passanti Ø12.2, dado + controdado.
- Staffa NEMA: asole 4.2×30 a 30 mm verificate col disegno; asole mensola 4.5×14 a croce (tensione cinghia ±5).
- `cnc/`: 5 STEP + 5 PDF + `NOTE_PREVENTIVO.txt`; `RG_preventivo_cnc.zip`, `cnc_per_pezzo/*.zip`. `VITERIA_E_MONTAGGIO.txt` = viteria e sequenza.
- Preventivo JLCCNC (prima delle ultime modifiche ai fori): piastra 42.22, base 31.63, piastrina 16.05, mensola 14.48 (sabbiatura + anodizzazione naturale), ruota 27.96 (senza finitura) = 132.34 € + spedizione/IVA.
- ERRORE NOTO nel pezzo unico già stampato: parete encoder a X 4.2–7.2 (nell'originale X 0–3) → la ruota originale con mozzo resta 5 mm avanti. Soluzioni: ruota girata + Loctite 641, mozzo accorciato a 6 mm, oppure ruota su misura `RG_ruota_encoder` (Al, Ø63.66 ±0.10, disco pieno, mozzo Ø18×6.78, foro Ø6 6.01–6.03, 2 grani M3; montaggio 10.0 mm parete→cerchio, un grano sul piano dell'albero LPD3806). In una ristampa del pezzo unico riportare la parete a X 0–3. **Fatto nel pezzo da ristampare (30/10/2026)**: vanno bene sia la ruota originale sia quella CNC.
- Vista 3D sede encoder: `integrazione_profiler/Ruota_encoder_3D.html`.
- RazorBoard sulla piastra verticale, lato posteriore (componenti verso il retro), fori P9–P12 M3 filettati passanti, interasse 87 × 142, bordo superiore scheda a filo della piastra (USB in alto). **Distanziali scelti (26/10/2026): 4 × M3 maschio-femmina, filetto maschio 4 mm, OD 5, corpo 10 mm** (maschio ≤ 6 mm: davanti a P12 c'è il pezzo MJF); scheda fissata con viti M3×6 nella femmina. Va bene anche corpo 12 mm.
- RazorBoard SMD (già ordinata): U1 TRACO TSR 2-2450 da saldare a mano, pin 1 sul pad quadrato (corpo 14 mm, sporge ~1 mm dalla serigrafia TSR-1: ok). D2 SMBJ33CA protegge poco il TSR (max 36 V): eventuale sostituzione a mano con SMBJ28A (stesso SMB). Accendere dal lato 220 V con i 24 V già collegati, oppure aggiungere 22–47 µF/50 V elettrolitico sui poli di J1.
