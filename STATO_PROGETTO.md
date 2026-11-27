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

Aggiornato: 20 novembre 2026 (punto di ripresa core + coating).

Verifica hardware completa del 19 ottobre: vedi VERIFICA.md.

Documento di progetto (versione modificabile): https://claude.ai/code/artifact/2273b50c-6248-4ea4-96ce-31eaccdc175b
Copia PDF: `RazorGauge_documento_progetto.pdf` in questa cartella.

## Modifiche dal lato software — leggere qui cosa è cambiato

Software e hardware sono ora nello stesso repository. Le modifiche al progetto vanno annotate qui
quando cambiano decisioni o stato del banco; il dettaglio puntuale resta nel `git log`.

### 23 novembre 2026 — revisione generale del codice (calcoli)

Controllati: SinkingSpeedCalc (cilindro isolato, corpo rigido, Compensate, densità per velocità), LineCore
(ρ_eff, massa, compound, conversione file), CoreCatalog, ProjectSegment (massa, colonna Sink), famiglie
(AFFTA, peso, velocità, densità), zone (ApplyZoneDensities), quantizzazione C, PDF (masse e velocità per
ugello), Sink Map app e PDF, CLI build/report, Prototype, gemello FlyLinePhysics (45/45 test).
Formule di base corrette: equilibrio peso/spinta/drag, unità, acqua (densità polinomiale, ν tabellata),
massa core + coating, inversi. Verifica incrociata: CLI `report` sul vecchio Phantom Hover (0.993) dà
0.156 → 0.481 in/s, identico a un ricalcolo indipendente in Python.

**Errori trovati e corretti:**
1. **Core condiviso fra le schede.** `LineCore.Current` è unico per tutta l'app, ma ogni scheda ha il suo
   core: affiancate o dopo un cambio scheda, masse e velocità usavano il core dell'ultima scheda caricata
   o modificata. Ora ogni scheda rimette il suo core quando diventa visibile e prima di ogni
   clic/tasto/rotella (`MainWindow.Tabs.cs`). Probabile causa della Sink Map di stamattina (0.060 → 0.443
   in/s nell'app contro 0.156 → 0.481 del calcolo).
2. **CLI `build`: zone a massa conservata senza core.** Il core veniva impostato solo dopo `Build`, quindi
   la riscalatura usava √(ρ_base/ρ_zona) da linea omogenea. Ora `Build` imposta il core della spec prima
   di riscalare. Verifica (Phantom Hover, zona 0–325 a 1.40): S1 0.264 g come senza zona, Ø 0.964 (prima
   sarebbe stato 0.888).
3. **Prototype: massa senza core.** I pezzi portavano solo la ρ del compound. Ora portano il core del file
   (salvato nel .flproto, ricaricato dalla sorgente per i vecchi), la massa usa ρ_eff(D) e il progetto
   assemblato eredita il core se è uguale per tutti i pezzi.

**Osservazioni (non errori, da decidere):**
- Zone a massa conservata con nodo al bordo: il tratto vicino fuori zona parte dal Ø riscalato e cambia
  massa (prova sopra: S3 3.101 → 2.800 g, 30 ft 246.0 → 241.4 gr). È la scelta "bordo zona = nodo".
- Compensate: la quantizzazione a ≤ 4 densità lascia i Ø e cambia le densità ⇒ anche la massa del file C
  si scosta dall'NC (oltre alla velocità). Da misurare su un file vero.
- Sink Map / colonna Sink = cilindro isolato; tratti con zona = corpo rigido (velocità unica): due modelli
  voluti, ma la mappa e la colonna non sono confrontabili su quei tratti.
- Drag Cd = 1 + 10/Re^(2/3): poco affidabile sotto Re ≈ 1 (tratti quasi neutri, < ~0.1 in/s).
- Codice morto: `LineSinkSpeed`, `LineSinkSpeedRange` (ancora 1.001–2.5), `TaperedSegmentSinkSpeed`.

### 23 novembre 2026 — Sink Map "invertita": primo dato reale, compound hover ≥ 1.02

- Stefano: la Sink Map di **Phantom Hover** dava la pancia (Ø 2.16) più lenta (blu) e la running line
  (Ø 0.98) più veloce (rosso). **In acqua si osserva il contrario: dove il Ø è maggiore affonda più
  veloce.** Primo dato reale sulle velocità.
- Legenda e colori corretti (blu = lento, rosso = veloce, app e PDF). Causa: compound del file 0.993
  (< acqua) con core 17 lb a 1.056 ⇒ le parti sottili affondano per il core, la pancia è quasi neutra.
- Calcolo: con core 17 lb il Ø più grosso affonda più veloce solo se compound ≳ **1.005** (inversione;
  a 1.00 la pancia è già più lenta, a 1.01 già più veloce). ⇒ un compound sinking/hover sotto ~1.005
  contraddice l'osservazione.
- **Decisione di Stefano: compound Phantom Hover = 1.02.** Applicato a `Phantom Hover.flp` con diametri
  invariati (backup `Phantom Hover.backup_2026-11-23.flp`): massa totale 59.95 → 61.13 g, testa
  0–1900 cm 43.95 → 44.93 g, 30 ft 240.8 → 245.8 gr. Le varianti 0.70 / 0.75 ips erano già 1.020 / 1.025.
- Controllo dei 26 progetti in Projects (23/11): nessun altro da correggere. Sotto 1.02 solo
  Phantom Hover 0.70ips (1.0198, sopra l'inversione) e ST27 - 60 0.30ips / C 0.20ins (1.007) e
  ST27 - 65 (1.006), che hanno core generico senza Ø o nessun core ⇒ calcolati omogenei, pancia
  più veloce comunque. Da valutare: avviso nell'app per compound sinking/hover sotto l'inversione.
- Anche: finestra About ad altezza automatica (titolo tagliato) e pulsante "?" con padding 0.

### 20 novembre 2026 — PUNTO DI RIPRESA (chiusura sessione)

**Stato:** peso e velocità di affondamento calcolati con core + coating in tutta l'app (NC, C/Compensate,
zone, famiglie, mappa, PDF). Core unico dalla punta alla fine della linea; la velocità varia lungo la linea
per il Ø (equilibrio peso/drag, Cd = 1 + 10/Re^(2/3)) e per la quota di sezione del core.
Verificato: pesi dei campioni tornano (hover 2.02 g, floating 0.78 g); Phantom Hover 0.75 punta
0.48 → 0.64 in/s con core 17 lb. **Velocità mai misurate in acqua.**

**Decisioni del giorno (Stefano):**
- compound minimo **0.88** (era 0.94), massimo 2.0; coating minimo 0.10 mm per lato;
- linea finita fino a **Ø 0.60**: core massimo = Ø minimo − 0.20 (avviso "Core too thick" già in disegno);
- assunti: floating di riferimento = core 17 lb (0.72 / 0.43 g/m) + compound 0.88; hover compound 1.066.
  Ritirata l'ipotesi "floating galleggia per l'aria nel core"; pesata del core estratto (0.10 g) messa da parte.
- Stefano: "keep it simple" — obiettivo = sapere quanto pesa e quanto veloce affonda la linea.

**Da fare (ripresa 21/11):**
1. Rigenerare i file C pre-19/11 con Compensate dagli NC.
2. Prova in acqua: cilindro hover 50 cm, acqua dolce ~20 °C, previsto 3.8 cm/s (1.50 in/s).
3. Fornitore: core ~0.40 mm (e carico di rottura) se servono punte < 0.80.

Commit del giorno: 07bd39f … 01c7473 (dettagli nella sezione core + coating più sotto).

### 19 novembre 2026 — core + coating nell'app (fase 1: calcoli) e conversione dei file

**Decisioni di Stefano:** "compound per tutti" (la densità di ogni ugello e di ogni file è il
compound, i file vecchi convertiti a massa conservata) e, in questo giro, solo i calcoli.

Fatto:
- `app/Models/LineCore.cs`: ρ(D) = ρ_coat + (ρ_core − ρ_coat)(d_core/D)², correzione di massa, compound
  da densità di linea, diametro a massa per lunghezza data, conversione dei file.
  `LineCore.Current` = core della linea in calcolo (app: al caricamento e a ogni cambio core; CLI:
  dopo il load). Senza core noto tutto torna identico a prima.
- `SinkingSpeedCalc`: tutte le velocità (cilindro, corpo rigido, linea, segmento) usano ρ(D);
  CompensateProfile conserva la massa col core dentro e restituisce il **compound**, limite 0.94 sul
  compound; DensityForTargetSinkSpeed restituisce il compound (minimo ora 0.94, non 1.001).
- Masse: `FrustumMassG`, `MassG`, 30 ft/AFTMA, PDF per ugello, Weight → Density (dà il compound).
- Riscalature a massa costante col core: Generate by Density, zone dell'app e della CLI, famiglie
  per grammatura (s iterato sulla massa vera).
- `.flp`: nuovi campi `DensityIsCompound`, `CoreDensityGCm3`. `ProjectService.Load` converte i file
  vecchi (un compound per materiale, massa del materiale conservata, materiali/zone/≤4 ugelli
  preservati). CLI `flyline convert-compound <cartella>`: cartella Projects convertita
  (backup `FlyLineProfiler/backup_prima_del_compound_2026-11-19.zip`, 140 file): 24 convertiti,
  116 senza core solo segnati. Massa totale: scarto ≤ 0.24 % (file C ExtraHover V.2 2.40 C),
  0.00–0.06 % altrove.
- Esempio: Bellaria #8 Opt.2 (17 lb, 1.06): compound 1.00, massa 493.2 gr invariata, punta
  0.39 → 0.48 in/s, corpo 0.62 → 0.36 in/s.

**Verifica funzionale nell'app vera (19/11 notte, banco WPF via reflection, copie dei file in temp).**
Stefano: i file C sono solo esperimenti, si rifanno tutti; verificare che il sistema nuovo funzioni.
Provati Bellaria #8 Opt.2 (17 lb), Phantom Hover V.2 0.70 (17 lb), Nautilus 0.5 (20 lb), ExtraHover
V.2 2.40 (17 lb), ST27-60 V.2 (12 lb):
- File vecchio aperto → convertito, massa 31.960 g invariata; salva + riapri → nessuna seconda
  conversione, massa identica.
- Cambio core (12/20 lb/generico) → core, massa e velocità ricalcolati subito, segno giusto.
- Famiglie per grammatura #5/#8/#11 → 140.0/210.0/330.0 gr esatti col core.
- `flyline pdf` di un C nuovo → PDF creato (contenuto non controllato a vista).
- Compensate 0.5–1.0 in/s → compound 0.95–1.38, massa totale ±0.3 %, finestra 30 cm ≤ 2 %, Ø continuo.
- **Trovato e corretto: Compensate veloce chiedeva compound assurdi** (2.4 in/s: 8.75, 59, 190, 408).
  Col core, stringere una sezione sottile a massa costante la porta verso il core e il poco coating
  rimasto dovrebbe essere densissimo. Aggiunto **tetto del compound `RhoCeiling` = 2.0 PROVVISORIO**
  (come il minimo 0.94: la fetta resta a 2.0, Ø a massa conservata, va più lenta del target, avviso).
  Dopo: compound 1.21–2.00, massa totale ±0.5 %, finestra 30 cm fino a −4.7 % a 2.4 in/s.
- **Aggiunto avviso spessore coating** sotto `MinCoatWallMm` = 0.10 mm per lato PROVVISORIO (solo
  avviso). Esempio: Bellaria a 2.4 in/s scende a Ø 0.787 sul core da 0.72 ⇒ 0.03 mm per lato.
- **Decisione di Stefano (19/11):** si tengono buoni **compound massimo 2.0 g/cm³** e **coating minimo
  0.10 mm per lato**. Non più provvisori.
- I file C in Projects sono ancora quelli convertiti (non validi): da rifare con Compensate nuovo.

**Non ancora adeguati (da sapere):**
- ~~`FlyLinePhysics`~~ **fatto (19/11 sera)**. Principio di Stefano: *FlyLinePhysics usa la massa
  finale, indipendentemente da come è composta.* L'analisi lavora solo su m(x) e D(x); la
  composizione serve solo a calcolare m(x). ρ·d = (m/A)·D, cioè densità vera della sezione, non del
  compound. Riscalatura delle zone a massa finale conservata col core. `flyline analyze` carica il
  file passando dall'app (conversione + core da catalogo), poi lo dà al gemello. Verifica Bellaria #8
  Opt.2: 32.0 g e masse per segmento identiche all'app. Test FlyLinePhysics 45/45 (2 nuovi sul core).
- Gli script `strumenti/stima_affondamento_core*.py` sono **SUPERATI** (19/11, controllato: nessuno
  li richiama, si usavano solo per le stime del 18-19/11). Segnati in testa al file; restano come
  documentazione. Leggono la densità del file come densità di linea, quindi sui file convertiti
  sbagliano: il calcolo ora lo fa l'app.
- `strumenti/verifica_massa_C.py` e `verifica_massa_zone.py` (verifiche indipendenti del 16/11):
  **tenuti e aggiornati al core** (19/11 sera), perché servono proprio a controllare l'app. Core dal
  file o dal catalogo (copia di CoreCatalog nello script). Lanciare con `python -X utf8`.
  - Zone (Bellaria #8 Opt.2, core 17 lb): dentro la zona massa conservata 0.00 %; scarto solo nel
    segmento appena fuori, come accettato il 16/11. OK.
  - **File C convertiti: NON validi.** Massa totale ok (≤ 0.3 %), ma localmente no. Peggior finestra
    30 cm prima/dopo la conversione: ExtraHover V.2 2.40 C +3.5 % → **+32 %** (punta), Nautilus 0.5 C
    0.50 −0.27 → −2.1 %, Phantom Hover V.2 C 0.70 +0.43 → −0.97 %, ST27-60 V.2 C 0.50 invariato.
    Causa: un file C è la soluzione di Compensate col modello omogeneo; il materiale più denso sta
    nelle parti sottili, dove il core occupa fino al 70 % della sezione. Per mantenerne la massa il
    compound esplode: ExtraHover 2.40 C 1.53 → **3.57**, Bellaria 1.00 C 1.13 → 1.41, Nautilus 1.5 C
    1.19 → 1.41. 3.57 non è producibile. I progetti NC convertiti invece sono plausibili (compound
    0.85–1.47).
  - **Da fare:** rigenerare i file C con Compensate nuovo (col core) partendo dagli NC, e dare a
    Compensate un **limite massimo del compound** producibile (oggi c'è solo il minimo 0.94): serve
    il valore massimo che il fornitore può estrudere. Fino ad allora i file C con core non vanno in
    produzione.
- I 4 QC "(Real)" con Ø core 0.575 e CoreType vuoto non hanno densità del core ⇒ niente core nei calcoli.
- Nessun campo nell'interfaccia per scrivere a mano la densità del core (solo da catalogo o nel file).
- Fase 3 (PDF con compound per ugello + ρ per sezione + avvisi) non fatta: il PDF usa già le
  masse e velocità col core, ma le etichette dicono ancora "density".
- Non provato a mano nell'interfaccia (solo build + CLI su tutti i progetti).

### 18 novembre 2026 — core + coating: stima sui profili esistenti (solo calcolo, app invariata)

Finora la linea è trattata come materiale unico. Modello nuovo discusso con Stefano:
`ρ_eff(x) = [ρ_core·A(d_core) + ρ_coat·(A(D) − A(d_core))] / A(D)`, dove si controlla solo ρ_coat
(l'ugello). **Il coating non penetra nella treccia**: con l'acetone si ammorbidisce e poi, con un
cappio di nylon, scivola via come un tubo, quindi non è agganciato alle fibre. Il core è
tutto l'involucro d_core, aria compresa. In punta il core occupa il **30–69 %** della sezione
(nel corpo il 6–22 %).

Incognita decisiva: la **densità apparente del core** (λ/A(d_core)). Il fornitore dà solo i Ø; si
chiede il dtex/g·m. Stimata con PET 1.38 × impaccamento 0.50/0.65/0.80 ⇒ **0.69 / 0.90 / 1.10**.
Script: `strumenti/stima_affondamento_core.py` (densità del file = coating, tutti i progetti con
core da catalogo) e `strumenti/stima_affondamento_core_misurate.py` (file QC "(Real)": densità =
media della linea finita, massa totale conservata, coating ricavato).

Risultati (in/s, acqua del file):
- **Densità del file letta come coating**: il segno della punta dipende dal core. Con core 0.90 le
  linee da ~0.4–0.5 in/s (Bellaria, Nautilus, Phantom Hover, ST27 V.2, Buck) **galleggerebbero in
  punta** (−0.4…−0.75); con core 1.10 affonderebbero più veloci (0.7–0.9).
- **Densità media misurata (QC Real)**: punta più lenta, corpo più veloce. Con core 0.90 la punta
  passa da 0.93 a 0.69 e il corpo da 1.69 a 1.93 (Phantom Extra Hover real 001). Con core 1.10
  (≈ densità della linea) quasi invariato. Coating ricavato ≈ 1.12–1.22.

Conclusione: finché non si conosce ρ_core le previsioni sulla punta non sono affidabili nemmeno
nel segno. Misura proposta, fattibile subito: pesare ~10 m di core nudo (bilancia 0.01 g) e misurarne
il Ø col RazorGauge ⇒ ρ_core. In alternativa si calibra all'inverso da una linea vera di cui si
conosce il comportamento della punta. **Chiarito da Stefano (corretto la stessa sera):** le densità
dei .flp sono la **densità della linea finita**, core compreso, NON quella del compound. Prima
aveva detto "compound" e si è corretto. Vale quindi la seconda lettura, quella a massa conservata
(`stima_affondamento_core_misurate.py --tutti`, progetti NC con core e senza zone). La massa totale
e la velocità media restano giuste. Cambia la **distribuzione**: se il core è più leggero della
linea, le parti sottili (punta, running line) rallentano e il corpo accelera. Se è più pesante,
succede il contrario. La densità del compound **non è nota** e va ricavata:
`ρ_coat = (ρ_linea·A(D) − ρ_core·A(d_core)) / (A(D) − A(d_core))`.
Esempi (core 0.90): Bellaria #8 Opt.2 punta +0.39 → −0.17, corpo +0.62 → +1.19, coat 1.12.
Phantom Hover V.2 0.70: punta +0.53 → −0.07, corpo +0.97 → +1.37, coat 1.07. Con core 1.10 le punte
accelerano leggermente (+0.5…+0.7) e il corpo di alcune linee da 1.02 arriva a galleggiare.
**Precisazione di Stefano:** finora la coda è stata trattata **come un corpo unico omogeneo**, non
come core + coat. Il numero del .flp è quindi la densità di quel corpo, uguale in ogni sezione,
non una misura fatta su un pezzo particolare. Nel modello nuovo diventa la **media** della linea a
massa totale fissa, mentre la densità reale ρ_eff(x) varia con D. Il compound si ricava riferendo
la massa alla linea intera (è quello che fa lo script). Per i progetti nuovi converrà progettare
direttamente con compound + core e mostrare la densità media solo come dato derivato.

**In attesa (18/11):** Stefano ha chiesto al fornitore il **peso in g/m di ogni size** di core.
Procedura all'arrivo dei dati:
1. ρ_core = λ [g/m] / A(d_core) [mm²], con il Ø minimo e il Ø massimo del catalogo per vedere
   quanto pesa la tolleranza. Esempio 17 lb (0.685 mm): 0.33 g/m ≈ 0.90, 0.40 g/m ≈ 1.10.
2. Controllo incrociato: pesare 10 m di almeno un size di core nudo (bilancia 0.01 g).
3. Rilanciare `strumenti/stima_affondamento_core*.py` con i valori veri al posto degli scenari.
4. Aggiungere λ a ogni voce di `app/Models/CoreCatalog.cs` (e al gemello FlyLinePhysics).

**19/11 — arrivati i dati del fornitore** (riportati così, Ø + peso di 1 m):
`0.72 → 0.43 g · 0.82 → 0.57 g · 0.90 → 0.61 g · 0.95 → 0.80 g` (Stefano ha corretto l'ultima
riga, prima riportata per errore come 0.89 g).
Densità apparente λ/A(d) col Ø dichiarato: **1.056 / 1.079 / 0.959 / 1.129**.
Abbinamento al catalogo (da confermare col fornitore): 0.72 = 17 lb, 0.82 = 20 lb, 0.90 = 25 lb;
0.95 è probabilmente il 30 lb (a catalogo 1.00–1.05 ⇒ 0.92–1.02), ma non è detto.
Peso della tolleranza sul Ø (densità con Ø max / nominale / min del catalogo):
17 lb 1.06 / 1.17 / 1.30 · 20 lb 0.96 / 1.02 / 1.08 · 25 lb 0.86 / 0.91 / 0.96. Il 12 lb non è
nella risposta (3 progetti lo usano).
Conclusione: **il core è circa 1.0–1.1, cioè quasi uguale alla linea**, non leggero (gli scenari
0.69/0.90 sono esclusi). Ma per il 17 lb (17 progetti su 28) basta la tolleranza 0.65–0.72 per
spostarlo da 1.06 a 1.30, e lì il segno del corpo cambia:
- con Ø 0.72 (1.06): modello quasi omogeneo, punta e corpo cambiano di ±0.1–0.3 in/s
  (Bellaria Opt.2: punta +0.39 → +0.47, corpo +0.62 → +0.38, coat 1.00);
- con Ø nominale 0.685 (1.17): coat ricavato < 1 (0.92) ⇒ punta più veloce, **corpo che galleggia**
  (Bellaria Opt.2 corpo +0.62 → −0.69, Nautilus invariata perché core 20 lb).
Prossimo passo decisivo: **misurare il Ø del core 17 lb nudo col RazorGauge** (e pesarne 10 m,
bilancia 0.01 g). Controllo di realtà: se il corpo delle linee da 0.5 in/s non galleggia in acqua,
il core 17 lb è sul lato 0.72 mm.

**Decisione di Stefano (19/11):** niente tolleranze così ampie sui core. Valgono le coppie Ø/peso del
fornitore: **17 lb = 0.72 mm, 0.43 g/m (ρ 1.06) · 20 lb = 0.82 mm, 0.57 g/m (1.08) · 25 lb =
0.90 mm, 0.61 g/m (0.96)**. Fatto: `CoreCatalog` con Ø singolo e g/m (densità mostrata sotto il
selettore), etichette vecchie riconosciute per materiale + carico, 21 `.flp` migrati sul disco
(backup `FlyLineProfiler/backup_core_2026-11-19.zip`). Il 0.95 mm / 0.80 g non è ancora abbinato a
un carico (30 lb a catalogo è 1.00–1.05): 30 lb invariato. Il 12 lb (3 progetti) è senza dati.
Con 17 lb a 1.06 il modello core + coating cambia poco rispetto alla linea omogenea (scenario
"r1.06" sopra): la punta accelera e il corpo rallenta di 0.1–0.3 in/s, senza cambi di segno.

**Dedotti (19/11), il fornitore non dà altro.** Stefano: "0.95 è il limite del 25 lb". Coerenza dei
tre core noti: 35–41 lb per g/m (media 38.5), densità 0.96–1.08 (media 1.03). Il 0.80 g/m come 25 lb
farebbe 31 lb per g/m (fuori serie), come 30 lb 37.5 (in serie); a densità 1.03 è Ø 0.99 ⇒
**30 lb = 1.00 mm, 0.80 g/m, ρ 1.02**. **12 lb stimato = 0.60 mm, 0.29 g/m, ρ 1.03** (flag
Estimated nell'app). Prima stima 0.31 g/m (12/38.5) ⇒ ρ 1.10, più denso del 17 lb: Stefano l'ha
scartata, giustamente; ora densità media dei noti e 41 lb per g/m, dentro la serie. 35 lb senza peso. Migrati i 3 progetti 12 lb (Buck, ST27-60 V.2 e il suo C;
backup `backup_core12_2026-11-19.zip`). 4 progetti hanno Ø 0.575 con CoreType vuoto: non toccati.

**Ricerca web (19/11) su trecce di poliestere:** nessun produttore di core per coda pubblica g/m.
Ashaway (core nylon) dà solo Ø .012–.040". Dati di cordini in poliestere con g/m e Ø ⇒ densità
apparente: Extremtextil 1.5 mm 1.2 g/m ⇒ 0.68; Teufelberger 3 mm 6.70 g/m ⇒ 0.95; Showtex Ribcord
1 mm 0.872 g/m (Dyneema/Dacron) ⇒ 1.11. I nostri 0.96–1.08 cadono dentro questo intervallo.
Prossimo: Stefano pesa campioni da 50 cm dei vari core (17 lb da 50 cm ≈ 0.21 g ⇒ serve bilancia
da 0.001 g, o più campioni insieme) e ne misura il Ø al RazorGauge con una tensione leggera e
sempre uguale (la treccia tubolare si schiaccia e si allunga).

**Protocollo misure concordato (19/11, da fare):**
1. *Core nudi* (12/17/20/25/30 lb), 50 cm ciascuno: Ø medio su più punti + peso ⇒ ρ_core vera,
   sostituisce stime/deduzioni nel CoreCatalog.
2. *Spezzone di linea finita*, tratto cilindrico da 50 cm: Ø linea, peso intero, poi via il coating
   (acetone + cappio), Ø e peso del core asciutto ⇒ ρ_core, ρ_coat e ρ_linea misurate. Su una linea
   nostra con .flp: confronto col coat dello script a massa conservata. Su una linea di altri
   produttori: frazione (d/D)².
Taglio a caldo e a lunghezza esatta; più spezzoni insieme se la bilancia è da 0.01 g.
Ragionamento collegato (19/11): altri produttori usano core relativamente più grossi in hover/slow
sink. Spiegazioni: linee veloci più sottili (spazio), core come volume perso nelle affondanti,
core ≈ neutro come riempitivo che stabilizza la densità delle hover; il rischio acqua nella
treccia (coating che non penetra) si gestisce sigillando le estremità.
**Approfondimento (20/11) — perché core più grossi in floating/hover.** ρ_linea = f·ρ_core + (1−f)·ρ_coat,
f = (d/D)². Il core non è una scelta "per la galleggiante": è un costo nelle affondanti e quasi gratis nelle altre.
- *Affondanti:* il core è volume morto. Con tetto compound 2.0, corpo Ø 1.00: core 0.45 ⇒ ρ 1.80, core 0.60 ⇒
  1.65; punta 0.80 con core 0.60 ⇒ 1.45. In più sono sottili e MinCoatWall 0.10 limita il core. ⇒ core fini.
- *Hover:* core ≈ 1.03–1.06 ≈ compound hover (1.066) ⇒ filler neutro: la scelta del core non sposta la densità,
  solo meccanica (allungamento). Riduce la sensibilità all'errore di dosaggio: dρ_linea = (1−f)·dρ_coat; con
  Δρ ≈ 0.03–0.06 dall'acqua, ±0.01 di compound vale 20–30 % della velocità.
- *Floating:* con un core ~1.05 il core spessore è una piccola penalità nel corpo (Ø 1.47, core 0.70: con
  compound 0.94 ⇒ 0.965) e grande in punta (Ø 0.90: core 17 lb ⇒ 1.017, **affonda**; 12 lb ⇒ 0.98; 0.45 ⇒ 0.96).
  La floating misurata (0.919, core ~0.70) richiede compound ≈ 0.88, **sotto il nostro RhoFloor 0.94**, oppure
  un core più leggero del nostro (treccia lasca con aria sigillata, ~0.7). Il vantaggio del core grosso nelle
  floating è meccanico: meno allungamento ⇒ meno deformazione del coating caricato di microsfere (più fragile,
  si crepa), più sensibilità/ferrata; e le floating sono più grosse, c'è spazio.
- Dato contrario da tenere presente: la nostra hover misurata ha core 0.45 (4 %), la floating 0.70 (21 %).
Da verificare: densità del compound floating realizzabile dal fornitore (se < 0.94 abbassare RhoFloor), e
controllo punta floating nell'app (core vs Ø punta) prima di scegliere il core.
**Pesata core floating (20/11):** 50 cm del core estratto dalla floating 1.47 = **0.10 g** ⇒ 0.20 g/m (meno del
nostro 12 lb, 0.29). Con Ø 0.65–0.70 ⇒ **ρ_core 0.52–0.60** (vuoti ~56–62 % su poliestere 1.38): treccia lasca.
Compound ricavato (linea 1.56 g/m, Ø 1.47): **≈ 1.00–1.04** (0.96 se il core in linea fosse 0.60 e si è gonfiato
all'estrazione); ±0.01 g sulla pesata ⇒ ±0.015. **La linea galleggia grazie all'aria nel core, non al compound**
(compound ≈ acqua, sopra il nostro RhoFloor 0.94). Risponde alla domanda sui core grossi delle floating: il core
è il galleggiante. Se l'acqua riempie i vuoti la linea passa a ~1.03–1.06 e affonda ⇒ estremità sigillate
indispensabili. Il nostro core (~1.05) non può fare questo lavoro: per una floating serve un core leggero.
**Pesate ripetute (20/11, con zavorra) confermano 0.10 g / 50 cm.** Resta incognito solo il Ø del core in linea (0.60–0.70 ⇒ compound 0.96–1.04).
**Floating col core leggero (20/11, analisi):** core 0.65 mm / 0.20 g/m (ρ 0.60, vuoti ~57 %, allagato ~1.17).
Punta minima costruibile Ø 0.85 (coat 0.10). Densità linea asciutta / allagata:
compound 0.94 — punta 0.90: 0.76 / 1.06, corpo 1.47: 0.87 / 0.98 · compound 1.00 — 0.79 / 1.09, 0.92 / 1.03 ·
compound 1.03 — 0.81 / 1.10, 0.95 / 1.06. Asciutta galleggia con qualsiasi compound fino a ~1.07 (anche quello
hover 1.066: corpo 0.97, punta 0.82) ⇒ niente compound galleggiante con microsfere. Allagata affonda sempre
in punta; solo corpo + compound 0.94 resta a galla. Punti critici: tenuta delle estremità (punta e loop),
il compound non deve entrare nella treccia lasca in estrusione (prova acetone + cappio sul primo pezzo),
Ø del core sotto la tensione di linea, carico di rottura del core (non noto). Nell'app basta il core nel
CoreCatalog (o CoreDensityGCm3 nel progetto): il modello è generico.
**Verifica obiettivo peso + velocità (20/11, flyline report su cilindri 50 cm, vecchio omogeneo vs core+coat):**
hover Ø 2.20: 2.020 g / 1.496 in/s in entrambi (misurato 2.02 g). Floating Ø 1.47: 0.780 / 0.783 g (misurato 0.78).
Punta floating Ø 0.90 (core leggero): **0.292 g vecchio vs 0.252 g nuovo (−14 %)**. ⇒ peso: verificato sui campioni;
la differenza fra i modelli c'è solo dove il core è una parte grande della sezione (punte, core leggeri).
Velocità: calcolata in modo coerente ma **mai misurata in acqua** ⇒ obiettivo non ancora dimostrato.
Prove semplici proposte: pesare 50 cm di punta della floating (0.25 nuovo vs 0.29 vecchio) e cronometrare
il cilindro hover 50 cm in acqua dolce a 20 °C (previsto 1.50 in/s = 3.8 cm/s).
**Pesata 20/11:** spezzone Ø 1.02, 50 cm = **0.41 g** ⇒ ρ_linea **1.00 ± 0.04**. Se è della floating 1.47:
previsto 0.375 g (omogeneo 0.919) e 0.343 g (core leggero + compound 1.00) ⇒ pesa più di entrambi; servirebbe
compound 1.28 in quel tratto (zona densa in punta?) — da chiarire con Stefano da che linea/tratto viene.
Stefano: viene da una floating con core ~uguale (0.65 mm). Se il core pesa come quello della 1.47 (0.10 g/50 cm)
serve compound 1.28 (non da floating) ⇒ quasi certamente il core qui è più pesante. Compound in funzione del peso
del core (50 cm): 0.10→1.28, 0.14→1.11, 0.16→1.03, 0.18→0.95, 0.20→0.87. Da fare: togliere il coating a questo
spezzone e pesarne il core (atteso 0.16–0.18 g se il compound è da floating).
**ASSUNTI DI LAVORO (20/11, Stefano: "facciamo assunti e andiamo avanti"):**
- *Nostre linee:* core del catalogo fornitore (già nell'app), nessun assunto nuovo.
- *Floating di riferimento (spezzoni 1.47 e 1.02, stessa famiglia):* risolvendo i due pesi insieme
  (stesso compound, stesso core) ⇒ compound **0.84** (0.76–0.93 con gli errori) e core ~0.41–0.48 g/m, cioè un
  core normale tipo 17 lb. Assunto: **core 0.72 mm / 0.43 g/m (ρ 1.06) + compound 0.88** ⇒ previsti 0.783 g e
  0.395 g contro 0.78 e 0.41 misurati. La pesata 0.10 g del core estratto è messa da parte (probabile parte della
  treccia rimasta nel tubo di coating, o impregnazione tolta dall'acetone).
  ⇒ **Ritirata** la conclusione "galleggia per l'aria nel core": galleggia per il compound 0.88.
- *Hover:* compound 1.066, core 12 lb (invariato).
Conseguenza: compound 0.88 < RhoFloor 0.94 ⇒ per floating così serve sapere se il fornitore estrude ~0.88.
**Decisione Stefano (20/11): il fornitore estrude ~0.88 ⇒ RhoFloor 0.94 → 0.88** (app, FlyLinePhysics, PDF,
dialogo Generate by Density, doc). Cambia anche la variante Floating delle famiglie (densità = RhoFloor).
**Ø minimo linea finita: 0.60 mm (Stefano).** Il core si sceglie di conseguenza: core max = D_min − 2·0.10.
Punta 0.60 ⇒ core ≤ 0.40 (nessuno a catalogo: il più fine è 12 lb 0.60 stimato); 0.80 ⇒ 12 lb; 0.92 ⇒ 17 lb;
1.02 ⇒ 20 lb; 1.10 ⇒ 25 lb. Un core poliestere 0.40 a ρ 1.03 pesa ~0.13 g/m e tiene ~5 lb (serie 38–41 lb per g/m):
più debole di molti finali ⇒ per punte < 0.80 valutare core più resistenti a parità di Ø. Archivio attuale:
punte ≥ 0.97, nessun progetto sotto la parete minima.
Avviso "Core too thick" nel pannello core mentre si disegna (Ø minimo − 0.20), verificato nell'app vera con
harness: Phantom Hover 0.75 (Ø min 0.969) con core 0.82 ⇒ avviso, 0.72 ⇒ nulla, 0.95 ⇒ avviso.

**Prime misure (19/11), spezzoni cilindrici da 50 cm di due linee finite.** Bilancia da 0.01 g con
ripetibilità pessima a vuoto: risolto con una **zavorra** (moneta sul piatto, poi tara), che evita
l'auto-zero sui carichi piccoli.
- **Hover, Ø 2.20, 2.02 g** ⇒ ρ_linea **1.063 ± 0.012** (Ø ±0.01 mm pesa più della bilancia).
  Cilindro da 2.20: ~1.5 in/s in acqua dolce a 20 °C, ~1.1 in salata; alto per un'hover, ma è il
  corpo, che è la parte più grossa.
- **Floating, Ø 1.47, 0.78 g** ⇒ ρ_linea **0.919 ± 0.018** (−1.25 in/s, galleggia).
Misurate solo le ρ delle linee finite. **Core dei due spezzoni ignoto (Ø e peso)** — osservazione di
Stefano: senza quei dati il compound non si può ricavare. Solo come ipotesi, con un core del nostro
fornitore (ρ ~1.03–1.06): hover compound ≈ 1.06 (= linea); floating compound 0.88–0.90, cioè core
che appesantisce. Con una treccia lasca (ρ ~0.7) sarebbe il contrario. Servono Ø del core estratto
(RazorGauge) e la sua densità (5–10 m dalla bobina, se è un core che abbiamo).
**Core estratti (19/11):** hover 2.20 ⇒ core **~0.45 mm** (4.2 % della sezione); floating 1.47 ⇒
core **0.65–0.70 mm** (~21 %, classe 17 lb). Core in bobina non disponibili, solo questi.
- Hover: con ρ_core qualunque fra 0.7 e 1.3 il compound è 1.079…1.053 ⇒ **ρ_coat ≈ 1.066 ± 0.013**,
  primo compound ricavato da misura, indipendente dal core. 0.45 mm è sotto tutto il catalogo (≈8–10 lb?).
  **Decisione di Stefano:** per la hover si assume core **12 lb** (0.60 mm, 0.29 g/m stimati, ρ 1.03,
  7.4 % della sezione) ⇒ **ρ_coat = 1.066**, invariato: il core qui non sposta il risultato.
- Floating: stesso intervallo ⇒ compound 0.82…0.98, troppo largo. Prossimo: pesare il core estratto
  (zavorra, 10 ripetizioni; atteso 0.16–0.20 g; ogni 0.01 g sposta il compound di ~0.015).

Piano di integrazione nell'app, concordato in linea di principio e da fare dopo i dati:
- **Fase 1, solo lettura:** ρ_eff e velocità con il core accanto a quelle attuali, nessuna modifica
  alla geometria, interruttore per progetto.
- **Fase 2:** Compensate (risolve ρ_coat per sezione) e riscalatura a massa costante corretta
  `A(D_new) = A_core + (m − λ_core)/ρ_coat_new`. Il limite minimo 0.94 passa al coating.
  Segnalare le punte non costruibili.
- **Fase 3:** PDF con coat density per ugello, ρ_eff per sezione e avvisi.

Non cambia: forma, ugelli, zone sui nodi (niente rampa), file C separati, etichette S/M.
Da tenere presente, non modellato: l'acqua che risale nella treccia dalla punta tagliata.

### 18 novembre 2026 — densità a 2 decimali, tabella Zones, ugelli, PDF

Richieste di Stefano nella stessa sessione (dettaglio d'uso in `MANUALE.md`, commit `3313367`…`b08f3da`).

- **Densità degli ugelli a 2 decimali alla sorgente**: i centri della quantizzazione k-means
  (`QuantizeSliceDensities`) sono arrotondati a 0.01 g/cm³ prima di costruire il file C. Così file C,
  legenda, PDF e anteprima degli errori usano le densità che si danno davvero al produttore. Tutte
  le visualizzazioni di densità sono ora a 2 decimali (tabella segmenti, etichetta del grafico,
  ugelli, PDF).
- **Densità coincidenti dopo l'arrotondamento**: due centri diversi a 3 decimali possono diventare
  uguali a 2, e allora si pagherebbe una coda multidensità con due ugelli uguali. Vengono uniti (un
  ugello in meno) e c'è un avviso in tre punti: nel dialogo Compensate (riga gialla), nel messaggio
  finale e all'apertura di un file C vecchio. L'avviso dice che l'ugello liberato si può usare per
  differenziare i colori. Per i file C vecchi l'avviso offre **Regenerate**: apre il progetto NC e
  rilancia Compensate con la stessa velocità e lo stesso numero di densità. Caso reale:
  4 densità chieste, intervallo ideale 1.016–1.033, a 2 decimali diventano 1.02 / 1.03, cioè 2.
- **Riga verde (volume e massa di testa e totali) nei file C controllata**: ricalcolata dal file,
  torna (C: 26.351 cm³ / 26.895 g; NC: 26.033 cm³ / 26.814 g). Nella tabella segmenti del C i
  pezzetti < 2 cm fra una rampa e un confine di taper sono uniti alla riga della rampa (prima
  compariva una riga S8 da 1 cm); vale solo per la visualizzazione, la geometria salvata non cambia.
- **Tabella Zones = sequenza completa della linea**: tolta la riga M1 fissa in alto (confondeva).
  I tratti scoperti compaiono al loro posto come righe M1 derivate, in corsivo e di sola lettura.
  Bug trovato da Stefano: Canc non cancellava più. Causa: la ricostruzione a ogni aggiornamento
  (`Items.Refresh`) rubava il fuoco. Ora le righe vengono notificate, non ricostruite; c'è anche il
  pulsante ✕ Remove.
- **Menu col tasto destro sulle zone** (Stefano: "fai tutto"): cambia ugello, modifica
  inizio/fine, estendi (alla precedente, alla successiva, alle estremità, anche sopra altre zone
  con conferma), dividi, unisci con la successiva, mostra sul grafico, rimuovi. Sulle righe M1 c'è
  "crea zona". Nei file C le voci che modificano sono disattivate.
- **Rimozione degli ugelli non usati** (pulsante ✕ Material e tasto destro): M1 e gli ugelli usati
  da zone non si possono togliere, e il menu dice perché. Gli slot sono fissi, quindi il buco si
  chiude: gli ugelli sopra scendono di un posto e le zone vengono rinumerate.
- **PDF, etichette dei nodi senza sovrapposizioni**: l'altezza dell'immagine del grafico segue la
  scala usata per disporre le etichette (600–1600 px). Prova su Coastal: 933 px, nessuna
  sovrapposizione.
- **Generate by Sink Speed creava due segmenti da 5 cm**: erano nodi spuri ai confini delle zone.
  Ora i generatori di famiglie prendono la forma dai nodi disegnati e la massa dal progetto
  effettivo. Le varianti a materiale unico hanno solo M1.
- **Sink Map nel PDF** (`SinkMapRenderer`, stesso modello dello schermo: ogni fetta è un cilindro
  isolato col suo Ø e la sua densità): è un'immagine a parte con barra dei colori in in/s, mai
  sovrapposta al grafico dei materiali. **Decisione di Stefano**: è l'ultima sezione del documento
  ("3 · SINK SPEED MAP" nei file C, senza numero negli NC) e va inclusa esplicitamente. A ogni
  Export PDF c'è la domanda Sì/No/Annulla (predefinito No), indipendente dall'interruttore Sink Map
  dello schermo. Da CLI: `flyline pdf … --sinkmap`. Verificato coi PDF della CLI su ST27 V.2 C
  0.50ips (pagina 2, dopo le tabelle 1 e 2) e Coastal(Original) (pagina 2, dopo la tabella). La
  domanda all'esportazione nell'app non è stata provata.

### 16 novembre 2026 — tolta la correzione scan Ø ±

**Decisione di Stefano:** col nuovo dispositivo a ombra la misura è diretta, quindi la correzione
degli scan del vecchio calibro (Ø ±, +0.06 mm o +8%) non serve più. Tolti pulsante, casella,
interruttore mm/% e le tre impostazioni. Per uno scan vecchio, lo scarto da ricordare è ~0.06 mm
costante (analisi 21/10).

### 16 novembre 2026 — Compensate con 2, 3 o 4 ugelli

Richiesta di Stefano: la compensazione usava sempre 4 ugelli (k = 4 fisso). Ora il dialogo
Compensate ha la scelta **2 / 3 / 4 nozzles** (ricordata nelle impostazioni, `CompNozzleCount`),
con accanto lo scarto di velocità, peggiore e medio, di ciascuna scelta alla velocità dello slider.
È calcolato con la stessa quantizzazione del file vero (`QuantizeSliceDensities`: k-means + rampe
di 30 cm), su copie, senza toccare il progetto. File: `… C 0.55ips.flp` con 4, `… C 0.55ips 3noz.flp`
/ `2noz` con meno. Prova con banco WPF su Phantom ExtraHover V.2 (scarto in/s, peggiore / medio):

| Target | 2 ugelli | 3 ugelli | 4 ugelli |
| --- | --- | --- | --- |
| 0.45 ips | 0.110 / 0.031 | 0.067 / 0.017 | 0.055 / 0.011 |
| 0.55 ips | 0.131 / 0.037 | 0.080 / 0.020 | 0.065 / 0.013 |
| 0.65 ips | 0.152 / 0.043 | 0.093 / 0.023 | 0.076 / 0.016 |

Il valore con 4 ugelli a 0.55 ips (0.065) è quello del 3/11, quindi il caso di sempre resta
invariato. I file C a 2/3 ugelli contengono 2/3 densità, gli altri ugelli restano a ρ = 0.
**Stesso giorno, ugelli liberi per il colore (Stefano: "ottima idea").** Ogni ugello è una coppia
(densità, colore) (`CompoundsOf`): le zone colore dell'NC passano nel C se le coppie distinte sono
≤ 4, altrimenti il C viene di un colore solo, con avviso. Con zone colore il dialogo dice
"densities" e mostra, per ogni scelta, gli ugelli necessari. Zone del C assegnate per colore e
densità (`ZonesFromBakedMaterials` con `colorAt`); rampe colorate secondo la zona quando due ugelli
hanno la stessa densità (`ChartGeometry.GetSliceColor`). Prova sul V.2 (arancione FF5C00,
1900–2050 cm) a 0.55 ips:
- 2 densità → 3 ugelli: 1.0147 / 1.0336 verde + 1.0336 arancione (M3 = 1900–2050)
- 3 densità → 4 ugelli: 1.0121 / 1.0205 / 1.034 verde + 1.034 arancione (M4 = 1900–2050)
- 4 densità → ne servirebbero 5: un colore solo, come prima
PDF non controllato a vista (manca un renderer PDF sul PC): da guardare la prima volta.

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
Nomi dei taper (Stefano: "i tratti non dovrebbero chiamarsi entrambi con lo stesso nome"): il nome
era legato all'X di partenza, quindi inserire un nodo lasciava buchi (S6, S9) e doppioni (due S10
nel Phantom: il cambio di pendenza a 1760 cm spariva dal C). Ora i nomi automatici `S{n}` sono
sempre rinumerati per posizione (`SegmentNaming`), i nomi scritti a mano restano; i file C non
vengono rinumerati. Phantom V.2: S1…S10, S8 1530–1760, S9 1760–1900.
Temperatura/acqua su un file C aperto: la tabella non cambiava (righe raggruppate costruite a
parte, mai ricostruite). Ora sì: test C 0.55 ips, prima riga 0.580 → 0.498 in/s a 5 °C.
PDF in cinese (richiesta di Stefano, solo il PDF): lingua scelta nel menu Tipo file del Salva
(English / 中文 / English + 中文), ricordata nelle impostazioni; CLI `--lang`. Testi in `SheetText`
(chiave = testo inglese, chiave mancante → inglese), font Microsoft YaHei di riserva. Traduzione
dei termini tecnici = prima stesura, da far rivedere al produttore.

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
- **Sede laser v3 per Picotronic LFD650-1-12(9x20) (29/10/2026) — SUPERATA il 31/10/2026 dalla sede precisa (vedi sotto): niente cono, grani né O-ring**: la sede Ø4 stampata non dava una direzione certa e stabile (laser che balla nel perno Ø4.3, grani M3 autofilettanti nel PA12 che si spingono a vicenda, 1/8 di giro = 0.3° = 0.8 mm sul chip). Calcolo ABCD: **1° di inclinazione del laser = ~2.8 mm sul chip** (il decentramento di ~4 mm del 27/10 = ~1.4°); per ±0.5 mm serve ±0.2°. Scelta utente: soluzione definitiva, laser **annegato in epossidica** una volta allineato; solo MJF + minuteria. Laser: Picotronic **LFD650-1-12(9x20)** (Order 70103984, datasheet REV 22 in `integrazione_profiler/LFD650-1-12_9x20_datasheet.pdf`): 650 nm classe 2, 0.5–1 mW, ottone Ø9 × 20, fronte piano con foro Ø6, apertura 3 mm, 3–12 V / 25 mA, fascio ~3 mm (ellittico con 3 lobi nelle immagini del produttore), divergenza 1 mrad; **involucro a potenziale VDD (+)**, filo rosso +, nero GND. Sede (`laser_block` / `laser_cuts` / `laser_cap` in `cad/RazorGauge.scad`): **appoggio a cono 90°** sul bordo anteriore Ø9 (punto di rotazione all'uscita del fascio, Z_LF = Z_L1 + 9 = 114.2: laser abbassato di 6 mm, Z_TOP invariato), foro Ø11 (inclinazione max ±2.9°), **2 grani M3 × 8 in nylon a 90°** a 14 mm dalla faccia in **inserti a caldo M3** (foro Ø4 × 6): frontale dal foro del coperchio, laterale dal fianco lato rullo (grani in nylon perché l'involucro è a +3.3 V: un attrezzo a massa sul grano cortocircuiterebbe i 3.3 V del master); **O-ring 8 × 1.5** sul corpo a 8 mm dalla faccia come ritorno; **tappo** (2 M3 in inserti) che preme il laser sul cono con un O-ring 6 × 1.5, con foro fili e 2 fori Ø1.6 per colare la resina sopra l'O-ring. Foro del carrello L2 da Ø14 a **Ø17** (fascio ~15.6 mm). JP2 su 3.3 V. Firmware: nessuna modifica necessaria (`k` per misura assorbe la potenza media); tempo di accensione da verificare con impulsi 5–100 µs. **Allineamento guidato**: modulo `master_razorgauge/gauge_align.inc` (istruzioni in `master_razorgauge/ALLINEAMENTO_LASER.md`), pagina `http://<ip>/align` con istruzioni esplicite (quale grano, verso, ottavi o sedicesimi di giro; ricerca dei due punti all'80% per la direzione di traverso; controllo di stabilità prima della resina). **Da includere nello sketch (3 righe)**: controllato (sintassi) sulla 0.6.0 e sulla 1.0.1-alpha, logica della pagina provata in simulazione. Verifica del modello (`integrazione_profiler/verifica_sede_laser_29-10.txt`): nessuna interferenza (20 parti), fascio Ø16 libero da chip a L2 e cono fino a L1, carrello libero. Pezzo unico 118.4 cm³ (mensola + sede laser), coperchio 8.19, carrello 3.24, tappo laser 0.69 (nuovo), kit 138.7 cm³. Immagine `integrazione_profiler/sede_laser_v3.png`.
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
- ~~Tappino a incastro della gola d'uscita~~ (31/10/2026, **superato** dalla piastrina girevole qui sotto: troppo complicato secondo Stefano; i file `FlylineProfiler_RazorGauge_tappo_uscita.*` e `strumenti/build_tappo_uscita.py` non vanno più usati). Dettagli originali: **Copertura della gola d'uscita (a sinistra guardando dal fronte, lato ruota) rimovibile (31/10/2026, richiesta di Stefano)**: la gola chiusa del blocco originale trattiene la coda di topo durante la scansione ma per inserirla bisognava infilarla. Tolto dal pezzo unico il tratto sopra la gola (X 16 – fronte, Y 67.4 – 69.9, Z 77.9 – fine, compreso l'invito originale del soffitto); al suo posto il **tappino** `FlylineProfiler_RazorGauge_tappo_uscita.stl` (0.30 cm³, `strumenti/build_tappo_uscita.py`): a U rovesciata, rifà il soffitto a Y 69.0 (foro 3.6 × 3.7 come prima, soffitto spesso 2.4: sporge 1.5 sopra il braccio), **2 perni Ø2.4 nei fori Ø2.6** delle due pareti, **clip elastica** sul fronte del braccio con dente sotto il braccio (Y 63.9). Si mette premendo dall'alto (la clip scatta), si toglie tirando in avanti la clip e sollevando; senza tappino la gola è aperta in alto per tutta la lunghezza e la coda di topo si cala dall'alto. Verifiche nuove (sezione TU): tappino sfilabile in alto senza toccare nulla, clip in presa, gola aperta senza tappino; linee Ø0.5/2/3 come prima (Ø3 piega 2.9°). Corretto anche il controllo del laser nella sede (non segnala più il contatto voluto sul cono). Tutte le verifiche e le lastre CNC OK. Pezzo unico 121.1 cm³, kit 148.7 cm³. Immagine `integrazione_profiler/tappo_uscita.png`.
- **Revisione completa della slitta (31/10/2026, richiesta di Stefano)**: controlli su spessori, fori, posizionamento e montaggio. Corretti:
  1. **Foro della vite M3 lato rullo a 0.3 mm dal bordo** della slitta (y 15.5, bordo a y 17.5) → spostato a **y 14.3** (parete 1.6; testa a 1 mm dalla spina del connettore, cacciavite dall'alto libero). Aggiornato anche l'incavo dello sportellino sopra la testa.
  2. **Svasatura della vite sotto la spina a 0.36 mm dal bordo anteriore** → slitta allungata di 1 mm oltre il fronte della mensola (bordo 1.36).
  3. **Ripetibilità quando si rimette la slitta**: fori delle viti nella slitta da Ø3.4 a **Ø3.2** e gioco laterale della linguetta nella piastra da 0.25 a **0.15** → posizione del chip ripetibile entro ~±0.1 mm (importante perché il frame di riferimento è per pixel).
  Esito: slitta senza pareti < 1.18 mm; estrazione 45 mm, viti raggiungibili, sportellino, ruota: tutto OK. Nuovo controllo **Q2** (spessori di slitta, sportellino, tappino, coperchio, carrello) che ha trovato anche: **foro M3 frontale del carrello che sfondava nel foro centrale Ø17** (parete 0.01, effetto dell'allargamento del 29/10) → profondità da 5.5 a **4.1** (vite M3×6 invariata, 3.8 in presa, parete 0.8); nel logo inciso dello sportellino tolto l'allargamento dei solchi (creste tra le lettere meno sottili). Restano creste sottili solo dentro le scritte incise (logo e RazorGauge): dettaglio grafico, non strutturale. Da ristampare anche il carrello (era già nel kit). Immagine `integrazione_profiler/slitta_revisione.png`.
  Note (non modificate): la quota del chip dipende da mensola + slitta 3.5 + PCB 1.6 (MJF ±0.2: col fascio collimato non cambia la misura); il chip guarda in alto sotto la coda di topo, quindi raccoglie polvere e residui del rivestimento → pulirlo estraendo la slitta; eventuale vetrino/filtro 650 nm da valutare.
- **Piastrina girevole sulla gola d'uscita (31/10/2026, richiesta di Stefano: al posto del tappino)**: tolto dal pezzo unico il soffitto della gola (Z 77.8 – fine): gola aperta in alto per tutta la lunghezza. Sopra il braccio la **piastrina** `FlylineProfiler_RazorGauge_piastrina_uscita.stl` (0.16 cm³, spessa 1.8, `strumenti/build_piastrina_uscita.py`) gira su una **vite a spalla M3 con spalla Ø4 × 2** avvitata in un **inserto a caldo M3** nel braccio (foro Ø4 × 6, a X 13.5 / Z 80, accanto alla gola). **Chiusa** copre la gola (soffitto a Y 69.9: foro 3.6 × 4.6), **ruotata di 90° verso l'interno** sta sopra il braccio pieno e la gola è libera; **due scatti** (dente sotto la piastrina, incavi nel braccio). Nervatura per spingerla con un dito. Verifiche (sezione TU): rotazione 0–90° senza toccare nulla, scatti liberi a 0° e 90° e in presa a metà, gola libera da aperta; linee Ø0.5/2/3 ora tutte dritte (piega 0°). Immagine `integrazione_profiler/piastrina_uscita.png`.
- **Fissaggio della slitta più robusto (31/10/2026)**: le 2 viti della slitta ora vanno in **inserti a caldo M3 in ottone** nella mensola (foro Ø4 × 6 + 2 mm Ø2.6), **viti M3 × 8** (una a testa svasata, una cilindrica): il filetto non si consuma togliendo e rimettendo la slitta (pareti attorno ≥ 1.3 mm). **Passaggio per una fascetta** sotto la mensola (2 asole dal basso a Z 4.5–6.1 e 12.9–14.5 unite da un tunnel sopra un ponticello di 1.5 mm, X 24–27; fascetta fino a 2.5 × 1.1) come fermacavo del cavo del sensore: lasciare tra fascetta e spina un'ansa di almeno 45 mm per estrarre la slitta. Dopo ogni estrazione della slitta rifare `gauge_dark` e `gauge_ref` (nota per l'altra sessione: ricordarlo nella pagina di calibrazione).
- **Sede del laser PRECISA (31/10/2026, decisione di Stefano)**: il laser deve entrare quasi forzato e si fissa dopo averlo posizionato. Tolti cono, foro Ø11, 2 grani in nylon con i loro inserti, O-ring 8×1.5 e 6×1.5, foro d'accesso al grano nel coperchio. Ora: **foro Ø9.0 esatto per tutta la lunghezza del laser (20 mm)** (prima versione Ø8.9 da alesare, cambiata su richiesta di Stefano: niente alesatura; invito 0.6×45° in cima), **battuta piana** su cui appoggia la faccia anteriore (foro Ø6 per il fascio). Montaggio: infilare il laser fino in battuta, **ruotarlo a mano** per orientare l'ellisse lungo la fila di pixel (pagina /align, passo 'ellisse'), fissarlo con un **cordone di epossidica nello smusso 1×45° in cima al foro** (tra laser e torre). **Tappo eliminato** (31/10/2026, decisione di Stefano) con i suoi 2 inserti e i bossoli: la cima della torre è liscia; i fili escono liberi (fermarli con un punto di colla o una fascetta più avanti). I file `FlylineProfiler_RazorGauge_tappo_laser.*` non vanno più stampati. La direzione del fascio è data dal foro (il gioco reale dipende dalla tolleranza MJF del foro) più la tolleranza del laser stesso tra fascio e corpo. **Nota per l'altra sessione**: nella pagina /align (`gauge_align.inc`) i passi con i grani non servono più; restano 'fascio', 'ellisse' e 'stabilità'; il centraggio residuo si verifica (deve stare entro la fila di pixel) ma non si regola. Minuteria: niente grani, niente O-ring, niente tappo: 4 inserti e 2 viti M3 in meno rispetto alla v3. Pezzo unico 122.0 cm³, coperchio 8.21, tappo 0.61, kit 149.5 cm³. Verifica: foro Ø9.00 su tutta la lunghezza, battuta sotto la faccia del laser, fascio libero, tutto il resto OK. Immagine `integrazione_profiler/sede_laser_precisa.png`.
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
- [x] **Caricato master 1.0.4-alpha** (27/11/2026 13:11, verificato via WiFi: fw 1.0.4-alpha, ppc 30.0200, dark/ref presenti, exp 20 ms, slave in STOP). (Era: compilato 27/11, core 3.3.8.) Innocuo anche prima dell'MCP6001 (solo attesa per pixel 1 -> 5 us). IDE: ESP32 Dev Module, COM8, **Erase All Flash Before Sketch Upload = Disabled** (altrimenti si perdono PPC 30.02, WiFi, dark/ref/esposizione), BOOT premuto su "Connecting...", rifiutare l'aggiornamento del core. Dopo: verificare via WiFi fw 1.0.4-alpha (/gauge) e ppc 30.02 (getparams).
- [ ] (rimandato, 27/11/2026) Porting dell'encoder del master al driver PCNT nuovo (esp_driver_pcnt) per il core ESP32 4.x; fino ad allora core 3.3.8 e niente aggiornamenti dall'IDE. Dopo il porting rifare prova 10 giri a mano + corsa da 15 m.
- [ ] Banco `ccd_lcd` col laser: togliere la saturazione (trimmer in serie, laser pulsato dal kit o ND16), poi ombra di un filo sulla finestra — vedi sezione 27 ottobre
- [ ] Al primo avvio: misurare il tempo reale di una misura (8 frame) e rifare la tabella velocità/rumore
- [ ] Prova Archimede in etanolo su spezzoni dritti già scansionati (verifica indipendente del gauge)
- [x] ~~Ricontrollare l'interasse dei fori della scheda sensore~~ → **chiuso 25/10/2026** col disegno quotato del modulo (`immagini/516cwokwrwL._AC_SX679_.jpg`): scheda 25 × 24, fori Ø2 interasse **21** × passo 6.5, 2 mm dai bordi, chip 8.5 dal lato corto. Coerente con `sensor.stl` e con le asole 20–21.2.
- [ ] Pezzo unico da ristampare (mensola + slitta v2 + sede laser v3 + fondo guide J + zona encoder per le due ruote + linguette anti-gioco delle forcelle + guide dello sportellino, 28–30/10/2026) — stampare anche slitta, sportellino e piastrina girevole della gola d'uscita; i 2 tappi dei blocchi guida (foro stelo Ø5.2) sono facoltativi — prima confermare i fori di fissaggio della scheda sensore
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

## Scheda sensore TSL1401CL v1 (29/10/2026; fori definiti 31/10/2026) — PRONTA PER L'ORDINE
Cartella `scheda_sensore/` (KiCad 7 generato da `script/`: `sens_def.py` unica fonte, `run_all.sh` rigenera tutto). Sostituisce il modulo Hiwonder sulla slitta v2 del pezzo unico.
- 24 × 18 mm, 2 strati, 1.6 mm, tutto SMD lato TOP, montaggio JLCPCB (Economic). TSL1401CL **C2802316** Extended, montabile da JLCPCB **con pre-ordine** (verificato su jlcpcb.com il 29/10); 100 pezzi LCSC a ~21.82 $.
- Circuito: TSL1401CL a 3.3 V, 100 nF + 10 µF, R 100 Ω su SI/CLK, carico 330 Ω su AO; buffer LMV321 (C7972) con offset: **Vout = 0.958·AO + 0.154 V** (sopra la zona morta ~70 mV dell'ADC ESP32); 100 Ω in uscita. Connettore JST GH 6 poli a ingresso laterale (C133065): 1 3V3, 2 GND, 3 SI, 4 CLK, 5 AO, 6 calza = J5 pin 1–5, 8.
- Footprint dal datasheet (fig. 9/10): origine = centro della linea di pixel (0.305 dal centro del package verso i pin 5–8), al centro scheda = asse laser; pixel 1 verso il fronte. Il CPL usa il centro del package.
- Lato ruota libero (fori), lato rullo: sotto la guida J solo 0603; U2 a 0.53 mm (diagonale) dallo spigolo della guida J anche in estrazione.
- DRC 0 errori / 0 connessioni mancanti. **Da fare prima dell'ordine:** decidere i fori di fissaggio (ora 3 aree vietate provvisorie), rigenerare, controllare rotazioni U1/U2/J1 nell'anteprima JLCPCB. Note d'ordine in `scheda_sensore/NOTE_ORDINE_JLC.txt` (ENIG + maschera nera consigliati, 2–3 schede montate, remark MSL 5a).

- **Fori di fissaggio definiti (31/10/2026)**: 3 fori **NPTH Ø2.2** per **viti M2 × 5** autofilettanti nella slitta (non più lunghe: slitta 3.5 + PCB 1.6, sotto c'è la mensola), in **X 2.0 Y 14.0 / X 2.0 Y 6.0 / X 22.0 Y 14.5** (KiCad) = x torre ±10 (spostati di 0.5 verso l'interno rispetto alle posizioni provvisorie ±10.5: foro a 0.9 mm dal bordo invece di 0.4). Area senza rame Ø4.4 attorno (testa M2 Ø3.8). Aggiunti alla scheda già sbrogliata (tracce a ≥ 2.8 mm): `script/add_holes_s.py` + `script/fill_drc_s.py` (in `run_all.sh`). DRC: 0 errori elettrici, 0 collegamenti mancanti; 1 avviso di sovrapposizione delle aree di ingombro H3/J1 (solo disegno: ~0.5 mm tra testa della vite e connettore). Gerber con il file NPTH (3 fori), BOM e CPL invariati (17 componenti). Slitta aggiornata con i fori Ø1.7 alle stesse posizioni (verifica montaggio OK, teste fuori dal fascio Ø16). `NOTE_ORDINE_JLC.txt` aggiornato: stato PRONTA PER L'ORDINE.
- **Cavo saldato, niente connettore (31/10/2026, decisione di Stefano)**: tolto il JST GH; il cavo si salda su **5 piazzole passanti J1** (passo 2 mm, foro 0.8, bordo anteriore, nomi in serigrafia sopra): **1 3V3 → J5-1, 2 GND → J5-2, 3 SI → J5-3, 4 CLK → J5-4, 5 AO → J5-5**. **La calza del cavo schermato va SOLO a J5-8** sulla RazorBoard, dal lato sensore tagliata e isolata (niente anello di massa sul segnale AO). J1 non è nella BOM né nel CPL (JLCPCB monta 16 componenti, 9 righe). Scheda risbrogliata (Freerouting), vie di cucitura GND messe solo dove libere (`add_zones_s.py` ora controlla le distanze), DRC 0 errori / 0 collegamenti mancanti; sparito anche l'avviso H3/J1. Slitta: **scarico 0.8 mm sotto le piazzole** per le saldature/fili tagliati a filo; il cavo appoggia sulla slitta ed esce dall'incavo dello sportellino (come prima la spina). Verifica montaggio e lastre CNC OK. `NOTE_ORDINE_JLC.txt`, schema PDF e anteprima aggiornati.

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

### 30/10/2026 - Scheda sensore: serigrafie in inglese, file d'ordine JLCPCB rigenerati
- Serigrafie sotto: "LATO RULLO" -> "ROLLER SIDE"; "FRONTE ->" -> "<- FRONT" (la freccia prima puntava dalla parte opposta al fronte = bordo piazzole cavo). Aggiunto "JLCJLCJLCJLC" (numero d'ordine: "Specify a location").
- Gerber zip senza le mappe di foratura (solo PTH/NPTH .drl). DRC 0 errori / 0 non collegati. BOM/CPL invariati (16 componenti, 9 righe).
- LCSC 30/10: C2802316 TSL1401CL 100 pz a magazzino, 21.82 $ (1+). Procedura d'ordine passo passo in scheda_sensore/NOTE_ORDINE_JLC.txt.

### 31/10/2026 - Slitta sensore: 1 vite + chiavetta di centraggio (richiesta di Stefano: le 2 viti M3 erano a 5.3 mm, teste quasi a contatto)
- Prima: 2 viti M3 x 8 a Z 12.55 (svasata) e Z 7.25 (cilindrica), costrette tra X ~38 (accesso dall'alto davanti al coperchio) e Z <= ~15 (sotto, la mensola e' scavata per la ruota e per il canale del cacciavite).
- Ora: UNA vite M3 x 8 svasata a filo (X 38.12, Z 9.0) in un inserto a caldo M3 (Ø4 x 6) + **chiavetta** 6 x 3 x 1.8 sotto la slitta (X 34-40, Z 19.5-22.5, lato ruota) in una **cava 3.2 x 2.0 aperta sul fronte** della mensola (invito 45° all'imbocco). Si infila in orizzontale come prima. Vincoli: quota = appoggio piano; lungo la coda di topo e rotazione = linguetta (dietro) + chiavetta (davanti, 12 mm dalla vite); X e serraggio = vite nel foro Ø3.2.
- `cad/FlylineProfiler_RazorGauge.scad`: TR_SCREWS = [[15.9, 12.55, 1]], nuovi TR_KEY / TR_KEY_SLOT (costola in sensor_tray, cava in column_v3). `build_sportello.py`: tolto l'incavo per la testa della vite cilindrica (Z 3.9-10.6). `make_assembly_profiler.py`, `verifica_finale_profiler.py` (nuovo controllo J: chiavetta, gioco 0.10, inserimento/estrazione 45 mm libero, parete della cava >= 1.35 mm).
- Verifica montaggio: 42 OK, 0 problemi (`integrazione_profiler/verifica_montaggio_31-10.txt`); lastre CNC: TUTTO OK (`verifica_piastre_cnc_31-10.txt`). Pezzo unico 121.95 cm3, slitta 2.72, sportellino 6.93, kit 148.9 cm3. **Scheda sensore invariata** (vite e chiavetta fuori dalla scheda, X > 34.2).
- Minuteria: inserti M3 da 3 a 2 (1 slitta + 1 piastrina), 1 sola vite M3 x 8 svasata per la slitta. Disegno `integrazione_profiler/slitta_fissaggio.png`, lista `ORDINE_MJF_E_MINUTERIA.txt`.
- **Inserti a caldo verificati per il montaggio (31/10/2026, richiesta di Stefano)**: pareti attorno ai fori Ø4 troppo sottili per il godronato (mensola 1.35 mm verso il fronte, braccio d'uscita 1.4 mm verso la fine del pezzo). Aggiunte due borchie cilindriche: mensola r 4.4 attorno all'inserto (fronte a X 42.52, a filo della slitta, sotto il piano) -> parete 2.35 mm; braccio d'uscita r 4.6 (Y 63.8-69.9, fino a Z 84.6, dentro il contorno della piastra) -> parete 2.55 mm. Punta del saldatore in asse dall'alto libera (cilindro r 3.5 per 40 mm) per entrambi; ordine: inserti PRIMA di coperchio, slitta e piastrina. Nuovo controllo K in `verifica_finale_profiler.py`. Verifica montaggio 44 OK / 0 problemi, lastre CNC TUTTO OK. Pezzo unico 122.02 cm3, kit 149.0 cm3.
- **01/11/2026 (Stefano): spigoli della faccia posteriore del pezzo unico VIVI** (in appoggio sulla piastra in alluminio). Tolto lo smusso 0.6 a gradini sul perimetro posteriore (`build_profiler.py`, smussi di stampa punto 2); i raccordi R3 degli angoli del contorno ora vanno a tutto spessore (prima partivano da X 0.6). Impronta posteriore da 6656 a 6963 mm2, identica alla sezione a X 1.5 (nessuno smusso). Restano solo gli smussi sulla faccia anteriore libera. Verifica montaggio 44 OK, lastre CNC TUTTO OK (impronta dentro la piastra). Pezzo unico 122.12 cm3, kit 149.1 cm3. Regola: niente smussi sugli spigoli che toccano la piastra.
- **01/11/2026 (Stefano): braccio d'uscita (mensolina sopra la sede encoder) con gli spigoli smussati come il resto.** La faccia di testa (Z 83.43) aveva spigoli vivi mentre gli spigoli lungo Z sono raccordati R0.5: smusso 0.5 a gradini sul perimetro della faccia di testa (sopra, fronte, sotto, labbri della gola), esclusi la gola (ha gia' il suo smusso d'uscita) e lo spigolo sulla faccia posteriore (vivo, da X 0.5). Borchia del perno della piastrina con smussi 0.5 sopra e sotto. Faccia posteriore invariata (6963 mm2). Verifica montaggio 44 OK, lastre CNC TUTTO OK. Pezzo unico 122.11 cm3. Immagine `integrazione_profiler/braccio_uscita_smussi.png`.
- **02/11/2026: STL riparati per il service** (il service segnalava STL da riparare, soprattutto il pezzo unico). Il pezzo unico era chiuso ma aveva 581 spigoli < 1 micron e 519 triangoli di area quasi nulla lasciati dai booleani (coperchio: 24 spigoli < 1 micron). Nuovo `strumenti/ripara_stl.py` (manifold3d simplify 0.001 mm + fusione vertici 0.0012 mm + controlli: chiuso, normali, 0 autointersezioni, 0 non-manifold, 0 microspigoli, 0 facce nulle, scostamento <= 0.001 mm). Applicato a tutti gli 8 file del kit; da lanciare su ogni STL prima dell'invio al service. Report `integrazione_profiler/controllo_stl_service.txt`. Verifiche dopo la riparazione: montaggio 44 OK, lastre CNC TUTTO OK.
- **02/11/2026: scheda sensore verificata sul datasheet del componente acquistato (C2802316, ams TSL1401CL v1-01, `scheda_sensore/C2802316_ams_TSL1401CL_datasheet_v1-01.pdf`)**. Pinout, package, linea di pixel (0.305 verso i pin 5-8, 0.22 sotto la faccia), passo e piazzole: OK, tranne **la piazzola del pin 1 (1.4 mm) che era allungata verso l'esterno: il datasheet (fig. 18) la allunga verso il pin 2** -> spostata di 0.6 mm (footprint + scheda, `script/gen_lib.py`), spostato un tratto di pista GND vicino; DRC 0 errori / 0 non collegati; CPL e BOM invariati; Gerber rigenerati. Remark JLCPCB aggiornato: MSL 5a, eventuale bake SOLO 60 C x 24 h (datasheet), reflow max 260 C. **Nota firmware (altra sessione)**: a VDD 3.3 V il TSL satura a 2.5-2.8 V -> all'ADC fino a ~2.84 V dopo il buffer, ma l'ADC ESP32 a 11/12 dB e' lineare solo fino a ~2.45 V: tenere il bianco sotto ~2.3 V con impulso laser / tempo di integrazione. Clock 5 kHz - 8 MHz, tint min 33.75 us, esercizio 0-70 C.
- **02/11/2026 (Stefano): sede del laser Ø9.03** (laser misurato Ø8.97 -> gioco 0.03 per lato; era Ø9.00). `cad/RazorGauge.scad`: LAS_BORE = 9.03 misurato sui PIATTI del poligono a 96 lati (diametro ai vertici LAS_BORE_V = 9.035; prima il Ø9.00 ai vertici dava 8.995 sui piatti). Controllo in `verifica_finale_profiler.py` ora su 48 direzioni. Pezzo unico rigenerato e riparato (ripara_stl), verifica montaggio 44 OK, lastre CNC TUTTO OK. Coperchio e carrello invariati.
- **02/11/2026: stampa MJF da PolyD (polyd.com, HP MJF, Rimini), adattamento alle loro linee guida** (tolleranza +/-0.3 fino a 100 mm; gioco tra pezzi da montare >= 0.4 con +/-0.2 per pezzo; scritte >= 1 mm; pareti <= 10 mm). Applicato (scelta di Stefano): cava della chiavetta 0.2 per lato (era 0.1, TR_KEY_SLOT), sede della linguetta della slitta 0.2 per lato (era 0.15); scritta RazorGauge del coperchio e logo dello sportellino incisi 1.0 mm (erano 0.6; sotto restano 1.0 mm); tasca di alleggerimento chiusa dal basso nella mensola (X 9-20.5, Z 5.5-11.5, Y 46.5-52): spessore massimo del pezzo da 11.9 a ~10.4 mm (solo punti). Verifica montaggio 44 OK, lastre CNC TUTTO OK, STL riparati. Pezzo unico 121.76, coperchio 8.16, sportellino 6.87, kit 142.9 cm3 (148.6 con i tappi). Colore: nero standard.
- **02/11/2026: PolyD segnala parti sotto 1 mm nel pezzo unico -> corrette** (`integrazione_profiler/spessori_pezzo_unico_02-11.txt`, misura con `strumenti/spessori_minimi.py`). Da 78.5 a 0.15 mm2 sotto 1 mm (restano solo punti sugli spigoli degli smussi). Modifiche: cava chiavetta 1.6 profonda e chiavetta 1.4 (TR_KEY/TR_KEY_SLOT; sotto la cava 1.26 mm); fondo della gola d'uscita tolto fino a Z 62.6 (era 0.56 mm sopra lo scarico ruota; la linea li' appoggia sulla ruota); ENC_FR 18.8 (anello encoder 1.18 mm); incavi di scatto dello sportellino passanti su tutta la testa delle guide; niente smusso anteriore vicino ai fori M3 a Y 3; tolte pellicole (soffitto gola, alette orecchie rullo, gradino scarico ruota 24.7, smussi del braccio). Verifica montaggio 44 OK, lastre CNC TUTTO OK. Pezzo unico e slitta rigenerati, kit 148.7 cm3 (con tappi). Possibile prossima segnalazione: creste sottili tra le lettere incise (coperchio/sportellino), inevitabili con lettere piccole incise 1 mm.

### 03/11/2026 - TERMINOLOGIA (precisazione di Stefano): verso della coda di topo
- La coda di topo **ENTRA dal lato ruota** (estremita' Z+ del pezzo unico, Z ~83.4, braccio sopra la sede dell'encoder), passa sulla ruota encoder, poi sotto il laser, tra i rulli, ed **ESCE dal lato rullo inferiore** (Z-).
- Quindi quelli che nelle note dal 31/10 al 02/11 sono chiamati "braccio d'uscita", "gola d'uscita", "foro di uscita", "piastrina d'uscita" sono in realta' **braccio / gola / foro / piastrina d'INGRESSO**. I nomi dei file restano quelli storici (`FlylineProfiler_RazorGauge_piastrina_uscita.stl`, `strumenti/build_piastrina_uscita.py`) per non confondere gli ordini gia' caricati.
- Verificato che il verso non cambia nulla nel progetto: lo smusso all'estremita' Z 83.4 e' l'invito d'ingresso (giusto), la rampa del fondo sale verso la ruota, lo spigolo a Z 62.6 (fine del fondo della gola, verso la ruota) e' raccordato; il controllo della linea (filo teso su ruota e fondo) non dipende dal verso.
- **03/11/2026: file rinominati** (nulla era ancora caricato in modo definitivo): `FlylineProfiler_RazorGauge_piastrina_uscita.*` -> `..._piastrina_ingresso.*` (anche in `kit_stampa_stl`), `strumenti/build_piastrina_uscita.py` -> `build_piastrina_ingresso.py`, parte `piastrina_ingresso` nell'assieme e nelle verifiche; testi delle verifiche con "braccio/gola d'ingresso". Verifica montaggio 44 OK. **Da cancellare a mano sul PC**: `..._piastrina_uscita.*` (integrazione_profiler e kit_stampa_stl), `strumenti/build_piastrina_uscita.py`, `..._tappo_laser.*`, `..._tappo_uscita.*`.

## 03/11/2026 - Sensore TSL1401CL (C2802316): approvvigionamento
- Primo pre-ordine JLCPCB di 2 pezzi ANNULLATO e rimborsato: il fornitore esterno vuole MOQ 15.
- Verificato: il TSL1401CL e' **fuori produzione** (ams "Discontinued", scorte passate a Rochester Electronics); anche il successore indicato TSL1401CCS e' discontinued. LCSC a magazzino 0.
- **Ripreso pre-ordine JLCPCB da 15 pezzi, pagato 76 EUR** (~5 EUR/pz). I pezzi vanno in "My Parts Lib": 2 per l'ordine PCBA (qty 2), 13 restano di scorta nel magazzino JLCPCB per ordini futuri. Il file della scheda NON cambia.
- Alternativa futura (RazorGauge v2): Hamamatsu S9226-04 (in produzione), 1024 px da 7.8 um su 7.99 mm, 3.3-5 V, uscita analogica con buffer, max 200 kHz (~5 ms/riga). Richiederebbe nuova scheda, adattamento ADC e firmware; non su JLCPCB/LCSC.

## 03/11/2026 - Braccio d'ingresso: raccordi tutti R0.5 tondi
- Stefano: gli smussi della mensola d'ingresso (dove c'e' la piastrina) non erano tutti uguali; preferisce il raccordo dell'STL originale (R0.5 tondo sugli spigoli lungo Z).
- `strumenti/build_profiler.py`: la testata del braccio (Z 83.43) passa dallo smusso a gradini 0.5 a un **raccordo tondo R0.5** (sfera fatta scorrere sul profilo, minkowski con manifold3d), stesse esclusioni (faccia posteriore X 0-1 viva, blocco sotto, gola col suo invito); **spigoli alti della gola aperta** (Z 77.8-fine) raccordati R0.5 (prima vivi); **borchia del perno** con raccordi R0.5 sopra e sotto (prima smusso dritto).
- Volume invariato (121.87 cm3). STL riparato e pulito; verifica montaggio 44 OK; piastre CNC TUTTO OK; area sotto 0.98 mm da 0.15 a 0.05 mm2.
- Aggiornati: pezzo unico STL/3MF (anche in kit_stampa_stl), kit_stampa STL/3MF, assieme, visualizzatore 3D, `braccio_ingresso_raccordi.png`.
- Restano a gradini 0.6 gli smussi del perimetro anteriore della piastra (tutto il contorno), non toccati.
- **03/11/2026 (2): TUTTI gli smussi a gradini -> raccordi tondi R0.5** (Stefano). Pezzo unico: perimetro della faccia anteriore (prima 0.6 a gradini), ora R0.5 da minkowski; tolta anche l'esclusione vicino ai fori M3 a Y 3 (con R0.5 restano >= 1 mm: area sotto 0.98 mm ora 0.01 mm2). Coperchio (`smussi_coperchio_carrello.py`): perimetro della faccia esterna R0.5 (prima 0.6 a gradini). `ripara_stl.py` fa fino a 3 passate. Volumi: pezzo unico 121.92, coperchio 8.20 cm3. Montaggio 44 OK, piastre CNC TUTTO OK. Restano smussi dritti 45 gradi (non a gradini): carrello, tappi guida, spigoli verticali dei blocchi guida, slitta. Immagine: `raccordi_R05.png`.
- **03/11/2026 (3): gola della mensola d'ingresso rifatta UNIFORME** (Stefano: non uniforme, difetti). Prima: gola originale larga 3.0 (Z 60.5-78.5) + foro allargato a 3.6 solo sotto Y 69.0 (sbalzo delle pareti in Z 69-78), fondo con due pendenze, gradino 0.05 dove era stato tolto il soffitto, raccordo degli spigoli alti che non tagliava (segno invertito). Ora in `build_profiler.py`: riempita e ritagliata come una sola gola aperta in alto, larga 3.6 (X 20.42-24.02), spigoli del fondo R0.6, fondo a pendenza unica da Y 66.78 (Z 62.6, come l'originale: sotto restano >= 1 mm) a Y 65.30 (Z 83.43), invito 0.4 all'imbocco, spigoli alti R0.5 per tutta la lunghezza. Verifiche: 44 OK (linee Ø0.5/2/3 libere, piastrina TU OK), piastre CNC TUTTO OK, area sotto 0.98 mm 0.01 mm2. Immagine `gola_ingresso_uniforme.png`.
- **03/11/2026 (4): finestre ad arco della zona encoder rifatte** (Stefano: confronto foro Ø42 piastra CNC / pezzo). Foro Ø42 centrato sull'asse (scarto 0.00), encoder Ø38.2 con 1.9 di gioco: OK. Le 4 finestre originali r 20-26 (servono solo a risparmiare materiale) cadevano nel foro Ø42 solo per 1 mm -> da dietro 4 fessure a mezzaluna. Ora richiuse e rifatte r 21.5-27.3 (stessi settori, angoli R1, lontane 1 mm dalla base della mensola): nel foro Ø42 restano solo foro centrale Ø22 e 6 fori viti; davanti le finestre sono aperte e il fondo e' l'alluminio. Pezzo unico 121.83 cm3 (prima 121.91). 44 OK, CNC TUTTO OK. Immagine `foro_encoder_piastra_vs_pezzo.png`.

## 04/11/2026 - Controllo approfondito prima della stampa MJF
- Kit sul PC = sorgenti rigenerati (8 file + kit .stl/.3mf). STL tutti puliti. PolyD: pareti, spessori max, scritte, giochi, fessure: OK (eccezioni grafiche note).
- Correzioni nel pezzo unico (`build_profiler.py`): smusso 0.65 a filo sotto la radice delle guide dello sportellino (prima tacca 0.35, blocchi lato rullo e lato ruota, tratto basso e spalla alta); vecchio foro (Y 57.97, Z 18.67) richiuso tutto e sede della linguetta della slitta ritagliata (prima tasca cieca 1.5 e rialzo 0.19). Pezzo unico 121.84 cm3. 44 OK, CNC TUTTO OK.
- Rapporto: `integrazione_profiler/CONTROLLO_PRE_STAMPA_04-11.txt`. Aperti: vite del perno della piastrina; file obsoleti da cancellare sul PC.
- **05/11/2026: 8 fori di fissaggio pezzo unico -> piastra a Ø3.6** (prima 3.3-3.4), per la tolleranza MJF +/-0.4% oltre 100 mm (Stefano valuta JLC3DP: molto piu' economico, MJF PA12 solo grigio naturale). Pareti >= 1.19, 44 OK, CNC TUTTO OK, pezzo unico 121.76 cm3. Stampa in GRIGIO (scelta di Stefano): sportellino e coperchio eventualmente da tingere/verniciare di nero se la luce ambiente disturba. Inserti a caldo a mano (regole di inserimento JLC3DP non applicabili: parete >= 3, zona piana 14 x 14).
- **05/11/2026: perno della piastrina d'ingresso STAMPATO** (Stefano: niente vite a spalla). Braccio: borchia piena (tolto l'inserto), perno Ø4.0 alto 2.0 con raccordo alla base, foro Ø1.7 per vite M2 x 5 autofilettante + rondella M2 larga Ø6 stretta sulla testa del perno. Piastrina: foro Ø4.3 + smusso 0.4 sotto. Assieme: parte `vite_perno_piastrina` (era `vite_spalla_piastrina`); verifica K2 nuova. 44 OK, CNC TUTTO OK. Minuteria: 1 solo inserto (slitta), 4 viti M2 x 5, 1 rondella M2 Ø6. Scartato il rivetto filettato M4 sotto la slitta (sportellino subito sopra la vite; svasata M4 non entra nella slitta).
- **05/11/2026: sportellino, difetto nella gola del logo sotto la R** (segnalato da Stefano): nel PDF la linea curva ha una fessura bianca di ~0.07 mm dove si uniscono due tratti -> nella gola restava una lamella sottile di materiale. `build_sportello.py`: chiusura morfologica 0.1 solo sulle parti lunghe del logo (linea curva e trattini); lettere invariate. Volume invariato 6.87 cm3; S1-S5 OK, 44 OK. Immagine `sportello_logo_gola_R.png`.

## 05/11/2026 - PEZZI MJF ORDINATI (versione CONGELATA)
- Stefano ha ordinato la stampa MJF (PA12 grigio) dei file in `integrazione_profiler/kit_stampa_stl/`: pezzo_unico (3 080 284 byte, 121.85 cm3), coperchio, sportello_luce (108 984 byte), carrello, slitta_sensore, piastrina_ingresso (135 684 byte). Tappi guida gia' stampati in grigio.
- Da qui questi STL sono CONGELATI: nessuna modifica senza decidere esplicitamente una ristampa. Eventuali correzioni dopo il montaggio vanno annotate come "revisione 2".
- In attesa: pezzi MJF; chip C2802316 (15 pz, stato "purchasing" su JLCPCB) per l'ordine PCBA della scheda sensore (2 schede).

## 08/11/2026 - Scheda sensore: ordine PCBA
- Chip C2802316 arrivati in My Parts Lib (15). Verifica scheda vs pezzi MJF / assieme: tutto coerente (`scheda_sensore/verifica_scheda_vs_mjf_cnc_08-11.txt`).
- Ordine PCB + montaggio (2 schede) fatto con Remark su MSL 5a (cottura solo 60 C x 24 h). Nell'ordine era "Confirm Parts Placement: No" e "No bake": chiesta al supporto l'anteprima di posizionamento (U1/U2) prima del montaggio.
- Modello 3D della scheda (solo visualizzazione) corretto: linea di pixel sull'origine del footprint (asse laser), package centrato sulle piazzole. Produzione invariata.
- Dettaglio di montaggio scheda/slitta: `integrazione_profiler/montaggio_scheda_slitta.png`.
- PROSSIMO: arrivo pezzi MJF + schede -> montaggio -> FIRMWARE (note gia' presenti: bianco < ~2.3 V all'ADC, dark/ref dopo ogni estrazione della slitta, frame a laser spento alternati, ruota CNC Ø63.66 = 200 mm/giro).

## 11-19/11/2026 - Hardware (sessione Cowork): scheda sensore in produzione, disegno di assieme
- Ordine PCBA JLCPCB SMT026110862413 (2 schede): anteprima di posizionamento verificata sul .kicad_pcb e confermata a JLC.
  U1 TSL1401CL (rot 180) pin 1 in alto a destra, fila 1-4 verso i condensatori; U2 LMV321 pin 1 in basso a sinistra.
  Il contorno della libreria JLC di U1 sembra sovrapporsi a R1-R3/C1: e' solo grafica (corpo reale 3.0 mm, 0.78 mm dai pad).
- Collegamenti: encoder LPD3806-600BM-G5-24C su J4 (rosso +5V, nero GND, verde A, bianco B, calza SH);
  pulsanti con LED su J6 (SCAN/F_S/F_O + GND comune), LED da alimentare a parte secondo la tensione (da misurare).
- Firmware (ipotesi da verificare): ~500 frame/s, laser alternato acceso/spento -> ~250 misure valide/s;
  un punto ogni 1 cm (come i .flp) agganciato all'encoder (120 conteggi/cm), media di tutte le misure del cm;
  velocita' standard proposta 50 mm/s (prove a 25/50/100/150). Taratura lunghezza con 2 segni di nastro a ~10 m
  rilevati dal sensore stesso (fattore k su 0.08333 mm/conteggio, salvato in NVS).
- Nuovo disegno: integrazione_profiler/RazorGauge_assieme_slitta_sensore_ruota.pdf/.png (A3, esploso, vista frontale
  quotata, distinta, sequenza di montaggio). Il PDF e' versionato (eccezioni .gitignore del 19/11), il PNG no.
- 19/11 incidente 99fa94b: la scrittura di STATO_PROGETTO dalla sessione Cowork (via ponte col PC) ha consegnato una copia
  vecchia del file (08/11) invece di quella aggiornata -> cancellate le righe core + coating, ripristinate in 581491b.
  Da ora la sessione Cowork: rilegge il file dal disco subito prima, aggiunge solo la sua parte, scrive con controllo
  della data di modifica e RILEGGE il file dopo la scrittura confrontandolo (hash) con quello voluto.

## 24/11/2026 - PEZZI MJF ARRIVATI E MONTATI: tutto OK. REVISIONE 2 - elenco delle modifiche (da fare solo a una futura ristampa)
- Stefano: pezzi MJF (JLC3DP, PA12 grigio) arrivati e montati, tutto OK.
- R2-1 Sportellino: gli scatti (chiuso / aperto +13) NON si sentono -> denti piu' consistenti.
  Oggi: dente sul nottolino BUMP 0.45 oltre la lastra (X 39.75), gioco lastra-testa guida 0.25 -> interferenza nominale
  solo 0.20 mm; incavo nella testa della guida profondo 0.35 (fianchi 30 gradi). Con la tolleranza MJF (+/-0.3) lo scatto sparisce.
  Proposta: BUMP 0.45 -> 0.8 (interferenza ~0.55) e incavi 0.35 -> 0.6 di profondita' (stessi fianchi inclinati, nessuno spigolo vivo);
  nottolino FIN_T 1.0 e lungo 8 mm invariato (PA12 flette abbastanza); verificare la forza con S1-S5 e la parete residua della testa
  della guida (oggi 1.5 mm, resterebbe ~0.9: eventualmente testa 1.5 -> 1.8 verso il fronte). File: build_sportello.py (BUMP),
  build_profiler.py (SH_DET_Y / _x0 incavi, SH_HEAD_X).
- R2-2 Sede del laser: Stefano ha dovuto ALESARLA (poco) per infilare il laser Ø8.97. Oggi LAS_BORE = 9.03 sui piatti
  (gioco 0.03 per lato, cad/RazorGauge.scad): i fori MJF escono piu' piccoli del nominale. Proposta: LAS_BORE 9.03 -> ~9.20
  (gioco ~0.1 per lato; il laser si blocca comunque con epossidica dopo l'allineamento). Se Stefano sa il Ø dell'alesatore
  usato, mettere quello. Aggiornare anche il controllo del laser in verifica_finale_profiler.py (oggi atteso 9.03).

## 24/11/2026 - Firmware per le schede RazorSensor: master 1.0.2-alpha (G_PIX_FIRST=2), compilazione master e slave OK, documentazione corretta
- master_razorgauge 1.0.1-alpha -> 1.0.2-alpha: G_PIX_FIRST 16 -> 2 (TSL1401CL nuovo della scheda RazorSensor, montato da JLCPCB,
  tutti i pixel buoni; il 16 escludeva i pixel 0-13 morti del vecchio modulo Hiwonder). G_PIX_LAST invariato (125).
- Pin verificati, invariati. Master: USE_RAZORBOARD 1, encoder 32/33, SI 26, CLK 27, AO 34, LASER 25, WIFI_RESET 14, UART RX 16 / TX 17.
  Slave 0.6.7: PUL 25, DIR 26, ENA 27, BTN_FAST_O 34, UART RX 16 / TX 17.
- Compilazione arduino-cli (esp32:esp32:esp32), niente caricato sulle schede:
  master_razorgauge 1 083 951 byte (82% di 1 310 720), RAM 54 688 (16%); slave 1 083 075 byte (82%), RAM 51 396 (15%).
  Librerie gia' installate: WiFiManager 2.0.17, WebSockets 2.7.2, FastAccelStepper 2.0.1.
- Doc corretta: PROCEDURA_PRIMO_AVVIO (titolo, master_razorgauge.ino al posto di master/master.ino, ESP32 Dev Module non S3,
  librerie slave, BOOT, rete "RazorGauge_Slave_Setup", note Hiwonder, sezione 1.0.2-alpha), FIRMWARE.md (versione + riga
  di compilazione), README (1.0.2-alpha).

## 25/11/2026 - Diagnosi scheda RazorSensor: segnale zero = U2 (LMV321) collegato con la piedinatura sbagliata -> comparatore bloccato
- Sintomo: sensore collegato, /gauge raw = 142 mV (pavimento dell'ADC) su tutti i 128 pixel, gauge_ref sale a 20000 us con
  picco 0. Catena ADC della RazorBoard OK (J5-5 a 3V3 -> 3155 mV). AO col tester: prima 0 V, poi 3.2 V DC. Pin del firmware OK.
- CAUSA (dai file di progetto, da confermare al banco): in scheda_sensore/script/sens_def.py U2 e' collegato come se fosse
  1 OUT / 3 IN+ / 4 IN- (piedinatura tipo MCP6001), ma l'LMV321IDBVR (C7972) e il simbolo KiCad usato hanno
  1 IN+ / 2 V- / 3 IN- / 4 OUT / 5 V+. Sul PCB quindi: OUT (pin 4) sta sulla rete VN, IN+ (pin 1) su AO_BUF, IN- (pin 3) su VP.
  AO_BUF e' collegato all'uscita tramite R8 10k (e verso l'ADC c'e' solo alta impedenza) -> IN+ = OUT: reazione POSITIVA.
  L'operazionale e' un comparatore con isteresi a due stati fissi: 0 V oppure ~3.2 V, indipendenti dalla luce
  (VP resta tra 0.08 e ~1.4 V e non riesce a ribaltarlo). Spiega sia la prima misura (0 V) sia la seconda (3.2 V),
  e il segnale nullo anche con 20 ms di laser. Sensore e laser non sono ancora stati provati davvero: il segnale non arriva all'ADC.
- Verifica col tester (scheda alimentata): pin 1 e pin 4 di U2 alla stessa tensione (0 V oppure ~3.2 V, piena scala), pin 3 ~0.08 V,
  C3 (VREF) ~0.148 V. Se lo stato e' 0 V, il valore non cambia illuminando il sensore.
- SOLUZIONI per le schede gia' montate:
  A) (giusta, mantiene l'offset +0.15 V) sostituire U2 con un operazionale SOT-23-5 con piedinatura 1 OUT / 2 V- / 3 IN+ / 4 IN- / 5 V+,
     rail-to-rail, 3.3 V, ~1 MHz: MCP6001T-I/OT (Microchip). Il PCB e' gia' giusto per quella piedinatura: nessun'altra modifica.
     Verificare sul datasheet del pezzo comprato la piedinatura prima di saldarlo.
  B) (prova rapida senza ricambi) togliere U2 e fare un ponticello da AO_RAW (lato di R3/R4 verso U1) alla piazzola 1 di U2 (AO_BUF):
     AO arriva all'ADC tramite R10 100R, senza offset (il buio cade sul pavimento ~142 mV dell'ADC, come col vecchio modulo).
     Carichi residui trascurabili: R8+R9 20k a GND e R4+R7 verso VREF, in parallelo a R3 330R.
  Per le prossime schede (rev 1.2): correggere sens_def.py (U2 pins {1: VP, 3: VN, 4: AO_BUF} tenendo l'LMV321, oppure BOM -> MCP6001
  tenendo il PCB) e rigenerare schema/PCB/produzione.
- Laser: resta da controllare a parte. LFD650-1-12 vuole 3-12 V; con JP2 su 1-2 (3.3 V) e' al limite minimo. Dopo aver sistemato U2:
  se il picco resta basso, JP2 su 2-3 (5 V). La prova "torcia nella gola, 20 ms" serve solo DOPO la correzione di U2.
- Firmware: nessuna modifica necessaria. Utile in futuro un comando gauge_laser on|off per l'allineamento (non fatto).

## 25/11/2026 - Diagnosi RazorSensor CONFERMATA al banco: U2 (LMV321) bloccato dalla piedinatura sbagliata
- Piedinatura verificata su tre fonti: datasheet TI SLOS263Y (ago 2023) Table 5-2, LMV321 DBV/DCK: 1 IN+ / 2 GND / 3 IN- / 4 OUT / 5 VCC+;
  LCSC C7972 = TI LMV321IDBVR; gerber prodotti (attributi del rame): U2 pin 1 = AO_BUF, 3 = VP, 4 = VN. Uscita vera (pin 4) -> R8 ->
  ingresso + (pin 1) = reazione positiva.
- Letture del master 192.168.1.239 (/gauge): fino alla misura n. 6514 tutti i 128 pixel a 142 mV (uscita U2 a 0 V); poi, dopo apertura
  dello sportello / contatto col puntale, n. 8733+ tutti a 3155 mV piatti (= stesso valore del ponticello J5-5 -> 3V3). Mai valori intermedi.
  Un sensore buono col buffer progettato non supera ~2.84 V e non da' 128 pixel identici.
- Tester (Stefano): U2 pin 1 - pin 2 = 3.2 V, pin 4 - pin 2 = 3.2 V (uscita e ingresso + uguali, stato alto bloccato). Spiega anche la vecchia
  misura di 3.2 V su J5-5 / D34 e la prima a 0 V (stato basso).
- Conclusione: la causa e' U2 collegato con la piedinatura sbagliata (errore di progetto: la verifica del 02/11 controllo' U1 sul datasheet,
  per U2 solo la rotazione, con l'ipotesi errata "pin 1 = OUT" in NOTE_ORDINE_JLC.txt riga 66). Sensore e laser non ancora provati.
- Soluzione senza rifare le schede: A) togliere U2 + ponticello R4 (piazzola AO_RAW) -> U2 piazzola 1; B) U2 -> MCP6001T-I/OT
  (1 OUT / 2 V- / 3 IN+ / 4 IN- / 5 V+, NON le versioni R o U). Disegno: scheda_sensore/script/disegna_rilavorazione_u2.py
  (immagine rilavorazione_U2.png, non in git). Prossimi ordini: solo BOM U2 -> MCP6001T-I/OT, gerber e CPL invariati.
- 25/11/2026: ordinato MCP6001T-I/OT da RS Components (marcatura vista: AA39 = MCP6001 I-temp, corretta). Datasheet Microchip
  DS20001733L / DS21733J, Table 3-1: MCP6001 SOT-23-5 = 1 VOUT / 2 VSS / 3 VIN+ / 4 VIN- / 5 VDD (= PCB); 1R e 1U NO.
  Al montaggio: pin 1 verso R4, controllo pin 2 = GND e niente corto 5-2; acceso: pin 1 ~0.15 V al buio e sale con la luce,
  poi gauge_dark + gauge_ref. Esposizione oggi bloccata a 20000 us (salvata dal gauge_ref fatto con U2 bloccato): laser acceso ~80%.

## 25/11/2026 - Encoder con la ruota CNC: verso invertito (master 1.0.3-alpha) e PPC calibrato 29.9787
- Prima corsa (goto 1500 con 1.0.2-alpha): la linea avanzava nel verso giusto ma l'encoder contava all'indietro -> goto senza fine,
  motore fermato a mano via "motor stop" a -1586 cm. Lezione: il monitor della corsa deve fermare il motore appena il conteggio
  va nel verso sbagliato o supera la destinazione (fatto nella seconda corsa).
- Firmware 1.0.3-alpha: #define ENCODER_REVERSE 1 (scambia INC/DEC dei fronti di A in setupPCNT, decodifica invariata). Commit 0db6e5e.
  Caricato su COM8 dall'IDE (con esptool da riga di comando il modulo non entrava in download: "Wrong boot mode 0x13").
  Verifica: ruota girata a mano in avanti -> ticks da 84 a 1421 (+).
- Calibrazione: linea con due segni a 1500 cm, resetpos, goto 1500 -> arresto a 1499.93 cm (44 998 impulsi), lunghezza reale
  1501 cm (Stefano) -> PPC = 44998/1501 = 29.9787 impulsi/cm (199.86 mm/giro, nominale 200). Salvato con setppc:29.9787 (EEPROM).
  Ruota vecchia: 30.21. Da fare: corsa di verifica (resetpos + goto 1500, il segno deve cadere sul riferimento).
- Corsa di verifica (PPC 29.9787, primo segno sul riferimento): goto 1500 fermo a 1498.97 cm (44 937 impulsi), al secondo segno
  mancavano 4 cm -> linea percorsa 1496 cm -> 30.038 impulsi/cm. Le due corse NON concordano (29.979 vs 30.038, 0.2%) a parita' di
  procedura; Stefano: la linea non scivola sulla ruota. Ipotesi aperte: ruota che slitta sull'albero (grani M3), allungamento della
  linea sotto tensione, impulsi persi (prova: 10 giri a mano = 6000 impulsi). Su richiesta di Stefano PPC riportato a 30.0000 (setppc:30).
- goto fermo ~1 cm prima: lo slave 0.6.7 fa fase 1 e fase 2 a passi contati con STEPS_PER_ENC = 25; con la ruota CNC il rapporto
  reale e' ~26 -> fase 1 finisce ~60 cm prima (creep lento ~2 min) e la fase 2 si ferma a fine passi senza conferma dell'encoder.
  Correzione proposta (slave, non fatta): fase 2 fino a conferma dell'encoder + STEPS_PER_ENC misurato.
- Slave 0.6.8 (correzione del goto): STEPS_PER_ENC resta 25 (stima per difetto = mai oltre il bersaglio), ma il goto si
  ripianifica sull'encoder: a fine fase 1, se mancano piu' di 8 cm, altro tratto veloce fino a 4 cm dal bersaglio; a fine
  fase 2, se l'encoder non e' entro 3 impulsi, altro tratto in creep. Max 10 ripianificazioni per goto, stop se l'encoder non si
  e' mosso dall'ultima (encoder guasto o linea che slitta). Compilato (82%), da caricare dall'IDE e provare con goto sotto monitor.
- Slave 0.6.8, prima del caricamento: velocita' della fase veloce del goto ridotta da 8400 a 6600 Hz (GOTOPOS_MAX_HZ = FAST_HZ*0.55), richiesta di Stefano.
- Prova slave 0.6.8 (PPC 30.0000, resetpos, goto 1500 sotto monitor): fase 1 ripianificata a ~1430 cm, creep finale, arresto a 1499.97 cm (44 999 impulsi dal reset, ~200 s) -> il goto ora arriva sul bersaglio. Segno a 1500 ancora 2.8 cm prima del riferimento -> linea percorsa 1497.2 cm -> 30.055 impulsi/cm. Tre corse: 29.979 / 30.038 / 30.055; le ultime due concordano (0.06%), la prima e' fuori.
- Stefano conferma che segno di partenza e segno dei 1500 sono letti sullo stesso riferimento -> PPC impostato a 30.0500 (setppc:30.05, EEPROM). Posizione ricalcolata 1497.5 cm (reale 1497.2). Da fare: corsa di verifica (rimettere la linea, resetpos, goto 1500: il segno deve cadere sul riferimento).
- Corsa di verifica a PPC 30.05: resetpos, goto 1500 -> arresto a 1499.93 cm (45 072 impulsi dal reset); segno dei 1500 oltre il riferimento di ~1 cm -> linea percorsa ~1501 cm -> 30.028 impulsi/cm. Quattro corse: 29.979 / 30.038 / 30.055 / 30.028 (media 30.025, dispersione +/-0.13% = +/-2 cm su 15 m): non e' piu' un errore di taratura ma dispersione da corsa a corsa, causa da trovare (prova dei 10 giri a mano, tensione della linea, grani della ruota).
- Decisione di Stefano (25/11): si lascia PPC 30.05 cosi' com'e'; la dispersione +/-0.13% fra corse resta nota e non indagata per ora (prova dei 10 giri a mano rimandata).
- 27/11/2026, quinta corsa (PPC 30.05, slave 0.6.8, comandi via WebSocket ws://192.168.1.239:81 con monitor di stop): resetpos, goto 1500 -> arresto a 1499.9 cm in ~202 s (fase veloce fino a ~1415, poi creep), nessuno stop di sicurezza; ~45 071 impulsi. Segno dei 1500 OLTRE il riferimento di 2.5 cm -> linea percorsa 1502.5 cm -> 29.998 impulsi/cm. Cinque corse: 29.979 / 30.038 / 30.055 / 30.028 / 29.998 -> media 30.020, dev.std 0.031 (0.10%), escursione +/-0.13%. Con PPC 30.05 la misura e' in media ~0.1% corta (30.02 centrerebbe la media), ma l'errore dominante resta la dispersione da corsa a corsa (+/-2 cm su 15 m), non la taratura.
- Nota firmware: a fine goto il master manda goto_status "completed":false, "reason":"stopped" anche se e' arrivato sul bersaglio (goToEncoderReached non viene impostato quando e' lo slave a concludere). Solo l'etichetta, la posizione e' giusta.
- 27/11/2026, prova dei 10 giri a mano (senza motore). Il conteggio grezzo non e' leggibile via WebSocket (readenc solo su Serial, master non su USB): trucco temporaneo setppc:5 + resetpos + scan_on -> i messaggi {"cm":N} danno impulsi = 5N..5N+4. Prima prova 1080 = 5400 = 9 giri (Stefano: un giro in meno, contato male). Seconda prova, 10 giri: 1199 -> 5995..5999 impulsi su 6000 attesi (scarto <= 5 impulsi = 3 gradi di ruota, entro la precisione dell'allineamento a mano). => NESSUN IMPULSO PERSO: encoder, 74HC14 e PCNT a posto; la dispersione +/-0.13% fra le corse e' meccanica (linea sulla ruota: tensione/allungamento, slittamento ruota-albero, posizione della linea sulla ruota). Ripristinati setppc:30.05, scan_off e reset (ATTENZIONE: i punti registrati con scan_on restano in memoria e il goto li usa per cercare il bersaglio -> dopo una prova del genere va sempre dato reset).
- Durante la prova lo stato del motore alternava OFFLINE / STOP ogni 4 s (slave che non risponde a un'interrogazione su due?), mentre il goto delle 10:36 aveva funzionato: da tenere d'occhio, vedi guasto UART di ottobre.
- 27/11/2026, sesta corsa = corsa A della prova "due corse di fila senza toccare niente" (PPC 30.05): resetpos, goto 1500 -> 1499.9 cm in ~206 s (~45 071 impulsi). Segno dei 1500 OLTRE il riferimento di 3 cm -> 1503 cm -> 29.987 impulsi/cm. Novita': segno a matita sulla ruota allineato al segno 0 della linea; quando il segno dei 1500 della linea e' arrivato sulla ruota il segno della ruota coincideva ancora (75 giri interi, linea e ruota senza scorrimento relativo), poi il motore ha trascinato altri ~3.5 cm prima di fermarsi. 45 000 impulsi = 75 giri (prova a mano: 600/giro) -> con PPC 30.00 il goto si sarebbe fermato proprio li'. Le due corse di oggi (29.998, 29.987) stanno su ~30.00; quelle del 25/11 (30.028-30.055, tranne la prima) piu' alte.
- Corsa B, primo tentativo (11:29): anomalo, conteggio fermo a 3 cm per ~40 s, rallentamento a 1139-1269 e arresto a 1269.2 cm dopo ~40 s fermo (goto abbandonato dallo slave); Stefano l'ha fatta rifare. Causa non chiarita (linea toccata? slittamento? UART).
- Corsa B (11:38, linea riportata a mano al segno 0, freno invariato, PPC 30.05): regolare, 1499.9 cm in ~204 s (~45 071 impulsi). Segno dei 1500 oltre il riferimento di ~1.5 cm -> 1501.5 cm -> 30.017 impulsi/cm. A motore fermo il segno dei 1500 della linea e' ~1 cm avanti rispetto al segno sulla ruota (nella corsa A coincidevano al passaggio) -> scorrimento linea-ruota dell'ordine di 1 cm su 15 m (0.07%), non costante fra le corse.
- Esito A/B: due corse di fila senza toccare il freno danno 29.987 e 30.017 (1.5 cm di differenza su 15 m, 0.1%) -> la dispersione c'e' anche senza toccare niente, non dipende dal rimontaggio. Il segno sulla ruota indica uno scorrimento piccolo e variabile della linea sulla ruota come causa probabile (da verificare: pressione del rullino, tensione). Sette corse: media 30.015.
- Pressione del rullino non aumentabile (limite meccanico, Stefano) -> lo scorrimento resta; precisione accettata ~+/-0.1% (~+/-1.5 cm su 15 m), sufficiente per i profili (1 punto/cm).
- DECISIONE (27/11/2026, Stefano): PPC 30.05 -> **30.02** (setppc:30.02, EEPROM), media delle corse.
- Corsa di verifica a PPC 30.02 (11:50): regolare, 1499.9 cm in ~203 s (~45 025 impulsi). Segno dei 1500 ~1 cm PRIMA del riferimento -> 1499 cm -> 30.037 impulsi/cm; segno della linea ~2 cm indietro rispetto al segno sulla ruota (scorrimento nell'altro verso rispetto alla corsa B: varia di segno, +/-1-2 cm). Otto corse: 29.979 / 30.038 / 30.055 / 30.028 / 29.998 / 29.987 / 30.017 / 30.037 -> media 30.017, dev.std 0.027 (0.09%), escursione +/-0.13%. PPC 30.02 confermato, calibrazione encoder CHIUSA.
- App (commit eada791, Desktop 27/11 11:58): a fine goto la lunghezza viene da final_cm arrotondato al cm (1499.9 -> 1500; i messaggi {"cm":N} durante il moto restano troncati dal firmware) e lo stato e' "Target raggiunto" se final_cm e' entro 0.5 cm dal bersaglio (aggira completed:false del firmware 1.0.3). Provato da Stefano con GOTO 1500 dall'app (12:04-12:07, 1499.9 cm): lunghezza 1500, stato e log corretti.
- Attenzione operativa: riportare la linea a mano al segno 0 fa variare il conteggio (12:03: da 1499.9 a 1618.8, non a 0) -> Reset Posizione sempre DOPO aver rimesso la linea. Un GOTO lanciato senza reset da 1618.8 verso 1500 sarebbe andato all'indietro (la macchina non puo'): fermato dal monitor.
- Misura della sola lunghezza di una linea sconosciuta (domanda di Stefano, 27/11). Verificato nel codice: durante un GOTO il motore NON si ferma quando la ruota si ferma. Master: watchdog encoder 5 s soppresso in GOTOPOS (FW-10). Slave 0.6.8: la fase 1 fa tutti i passi pianificati senza guardare l'encoder; a fine fase 1 una ripianificazione veloce, poi fase 2 in creep (400 Hz, ~16 impulsi/s) per tutta la distanza mancante -> con GOTO 4000 su linea da 30 m decine di minuti a vuoto prima dello stop per stallo. Quindi col GOTO bisogna premere STOP (la lunghezza resta giusta: dopo l'uscita della coda la ruota non conta piu').
  Alternative: (1) Reset Posizione + scan_on + motor fast_s: fuori dal goto il watchdog di 5 s ferma il motore da solo; lunghezza in cm interi per difetto; registra punti fittizi -> reset prima del goto successivo; non ancora provata. (2) Proposta (non fatta): nel master watchdog dei 5 s attivo anche in GOTOPOS (in creep l'encoder avanza ~16 impulsi/s, nessun falso stop); da caricare dall'IDE.

## 26/11/2026 - RazorSensor: analisi dell'errore su U2, rimedio, JP2 e prevenzione (sessione Cowork)
- Analisi completa in `scheda_sensore/ANALISI_ERRORE_U2.md`: errore = U2 collegato per numero di pin con la piedinatura
  "1 OUT / 3 IN+ / 4 IN-" presa a memoria (TI LMV321 DBV: 1 IN+ / 3 IN- / 4 OUT) -> reazione positiva. Cause: piedinatura
  non presa dal datasheet del codice ordinato, collegamenti per numero e non per nome, controlli (ERC, DRC, anteprima JLC sul
  solo pin 1, nota "pin 1 (OUT)" scritta da noi) tutti coerenti con l'errore, nessuna simulazione della catena analogica.
- Rimedio confermato: U2 -> MCP6001T-I/OT (solo T-I/OT, marcatura AA..), nessun'altra modifica; rilavorazione con U1
  protetto (finestrella coperta, niente aria calda diretta, U2 a ~4 mm dal TSL1401CL). Ponticello senza U2 solo come prova.
- Da fare nel firmware: attesa per pixel in gReadFrame 1 -> 5 us (slew MCP6001 0.6 V/us, gradino ~2 V al bordo dell'ombra).
- JP2: dopo la riparazione gauge_ref con JP2 1-2 (3.3 V, 0.3 V sopra il minimo del laser); se l'esposizione sale verso il
  massimo o il picco e' basso/instabile -> JP2 2-3 (5 V). L'esposizione salvata (20000 us) viene dal riferimento con U2 bloccato.
- Prevenzione: skill `verifica-progetto-scheda` (nuova) e `jlcpcb-ordine-pcba` (aggiornata); lavoro per VS Code in
  `scheda_sensore/PROMPT_VSCODE_rev1.2.md` (pinout_datasheet.json, sens_def per nome di pin, verifica_elettrica_scheda.py con
  test di non regressione v1 = ERRORE, BOM rev 1.2 U2 MCP6001T-I/OT, note d'ordine, attesa 5 us). Regola: nessun ordine
  PCB/PCBA senza verifica elettrica tutto OK e revisione indipendente delle piedinature sul datasheet.

## 27/11/2026 - RazorSensor rev 1.2 (solo BOM) e verifica elettrica (eseguito PROMPT_VSCODE_rev1.2.md)
- `scheda_sensore/pinout_datasheet.json`: piedinature dai datasheet ufficiali, con documento e pagina:
  TSL1401CL (ams v1-01, fig. 3-4 p. 5), MCP6001T-I/OT (Microchip DS20001733L, tab. 3-1 p. 11, codici p. 47, slew 0.6 V/us p. 4);
  non compatibili col PCB: TI LMV321IDBVR (SLOS263Y tab. 5-2 p. 3), MCP6001RT-I/OT e MCP6001UT-I/OT (DS20001733L tab. 3-1).
- `sens_def.py`: nuova `ic()` che collega i circuiti integrati per NOME di funzione e ricava i numeri dal JSON (errore
  bloccante se un nome manca o un pin resta senza rete e non e' dichiarato NC). U1 e U2 convertiti; U2 = MCP6001T-I/OT
  (simbolo Amplifier_Operational:MCP6001-OT). Netlist identica al PCB v1 (U2: 1 AO_BUF, 2 GND, 3 VP, 4 VN, 5 VDD).
- `strumenti/verifica_elettrica_scheda.py`: pad -> funzione -> rete (sens_def == PCB), reazione degli operazionali con
  percorsi resistivi, ingressi non flottanti, alimentazioni, reti con un solo pad, simulazione DC nodale (A 1e5, AO 0..2 V).
  Test di non regressione (`--non-regressione`, esito in `scheda_sensore/verifica_elettrica_2026-11-27.txt`):
  v1 (LMV321IDBVR) = ERRORE (4: nessun percorso OUT->IN-, reazione positiva VN->R8->AO_BUF, dVdiff/dVout = +1, uscita
  bloccata a 0 V come al banco); rev 1.2 (MCP6001T-I/OT) = TUTTO OK (dVdiff/dVout = -0.5, AO_BUF = 0.958*AO + 0.154 V,
  scarto massimo 0.4 mV). ngspice non installato: solo calcolo nodale.
- BOM rev 1.2: U2 -> MCP6001T-I/OT **LCSC C116490** (verificato su lcsc.com/product-detail/C116490.html: MICROCHIP
  MCP6001T-I/OT, SOT-23-5). Aggiornate `produzione/RazorSensor_BOM_JLCPCB.csv` (solo la riga di U2) e `RazorSensor_BOM.csv`.
  Gerber e CPL invariati (U2 rotazione 270: pad 1 = angolo verso R4, fila 1-3 verso U1; nell'anteprima JLC controllare che
  il pallino del C116490 cada sul pad 1). `NOTE_ORDINE_JLC.txt` aggiornato (rev 1.2, controllo di OGNI pad, verifica prima dell'ordine).
- Schema: modifica puntuale di `RazorSensor.kicad_sch` (non rigenerato, UUID e legami col PCB invariati): simbolo incorporato
  LMV321 -> MCP6001-OT (stessa geometria, pin rinumerati 1 OUT / 3 + / 4 -), etichette di U2 scambiate (+ VP, - VN, uscita
  AO_BUF), cartiglio rev 1.2. Netlist dello schema (kicad-cli 10) identica pin per pin a prima. ERC: gli stessi 2 errori della v1
  (power_pin_not_driven su U1 4/6, manca PWR_FLAG: alimentazione dal cavo) + 1 avviso lib_symbol_mismatch (copia del simbolo nello
  schema diversa da quella della libreria KiCad 10, pin uguali). `RazorSensor_schema.pdf` rigenerato con kicad-cli.
  ATTENZIONE: `gen_sch_s.py` (pipeline Linux) con MCP6001-OT non funzionerebbe com'e': il simbolo e' derivato ("extends
  MCP6L91T-EOT") e raw_symbol/kiutils leggono solo la parte derivata -> da sistemare se si rigenera lo schema.
- Firmware: master_razorgauge **1.0.4-alpha**, gReadFrame attesa per pixel 1 -> 5 us (assestamento MCP6001). NON compilato:
  il core ESP32 installato sul PC e' passato a 4.0.0 (25/11 22:20) e `driver/pcnt.h` (PCNT legacy dell'encoder) non esiste
  piu' -> il master non compila nemmeno senza la modifica. Serve il core 3.3.x (prima 3.3.8) oppure il porting al driver
  PCNT nuovo (esp_driver_pcnt). FIRMWARE.md e README aggiornati a 1.0.4-alpha.
  AGGIORNAMENTO 27/11: decisione di Stefano, niente porting (l'encoder e' appena stato validato col driver legacy) ->
  core esp32 riportato a **3.3.8** (`arduino-cli core install esp32:esp32@3.3.8`; la prima estrazione aveva perso
  esp32-libs/3.3.8/bin, bootloader_*.elf mancanti -> core disinstallato e reinstallato). Compilati: master 1.0.4-alpha
  1 104 987 byte (84%), RAM 54 168 (16%); slave 0.6.8 1 099 887 byte (83%), RAM 50 876 (15%). Lo slave compila anche col
  4.0.0 (87%). NON aggiornare il core ESP32 dall'IDE finche' il master usa driver/pcnt.h.

## 27/11/2026 - RazorSensor rev 1.2: pacchetto di produzione pronto (NON ordinato)
- Richiesta di Stefano: preparare tutto per la produzione della versione funzionante. Condizione: ordinare solo DOPO che
  una scheda v1 riparata con l'MCP6001 funziona al banco (sensore e laser mai provati davvero finora).
- PCB: serigrafia sotto "RazorGauge TSL1401CL v1" -> "v1.2" (testo 1.75..19.25 mm, dentro i 24 mm); valore di U2 su F.Fab
  LMV321 -> MCP6001 (non va nei gerber). DRC KiCad 10: 0 errori, 0 non collegati, stessi 16 avvisi di libreria della v1.
- Gerber + foratura rigenerati con kicad-cli 10 (stesse opzioni di produzione_s.py) -> produzione/RazorSensor_gerber.zip
  (12 file). Confronto v1/v1.2 entrambi da KiCad 10: cambia SOLO B_Silkscreen (+ il .gbrjob). Confronto v1 KiCad 10 con lo
  zip originale (KiCad 7): stesse piazzole/tratti per livello, stessi 21 fori PTH + 3 NPTH.
- BOM JLCPCB e CPL rigenerati dal PCB con la logica di produzione_s.py (python di KiCad 10): identici ai file in produzione/
  (CPL = v1; BOM = v1 con U2 C116490). Verifica elettrica rifatta sul PCB aggiornato: v1 ERRORE, rev 1.2 TUTTO OK.
- NOTE_ORDINE_JLC.txt: rev 1.2, condizione per ordinare, checklist del giorno dell'ordine (verifica elettrica, piedinature,
  TSL1401CL ~13 in My Parts Lib, stock C116490 senza sostituti, pallino U2 sul pad 1, "v1.2" sotto, Remark MSL), comandi
  kicad-cli per rigenerare i gerber su Windows. Immagine del lato sotto: scheda_sensore/RazorSensor_rev1.2_lato_sotto.png.
- Regola: nessun ordine PCB/PCBA senza `python strumenti/verifica_elettrica_scheda.py` tutto OK e revisione indipendente
  delle piedinature sul datasheet del codice esatto.
