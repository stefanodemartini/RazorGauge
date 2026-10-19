# RazorGauge — stato del progetto e punto di ripresa

> **Questo è il repository unificato** (`github.com/stefanodemartini/RazorGauge`): CAD, schede,
> app WPF, CLI, libreria fisica e firmware sono versionati insieme. Il firmware attivo è il master
> **0.4.22-RB2** col calibro e lo slave **0.6.1**, entrambi per ESP32 classico, nelle cartelle
> `master/` e `slave/`. Il master ottico **1.0.0-alpha** è in `master_razorgauge/`: preliminare,
> non ancora operativo.
>
> Le copie in `Claude outputs/` e `_archivio_NON_USARE/` non sono sorgenti attive.
>
> Indici: `README.md` per la struttura, `FIRMWARE.md` per firmware/versioni, `MANUALE.md` per l'app.


Aggiornato: 19 ottobre 2026 (verifica completa: vedi VERIFICA.md).

Documento di progetto (versione modificabile): https://claude.ai/code/artifact/2273b50c-6248-4ea4-96ce-31eaccdc175b
Copia PDF: `RazorGauge_documento_progetto.pdf` in questa cartella.

## Modifiche dal lato software — leggere qui cosa è cambiato

Software e hardware sono ora nello stesso repository. Le modifiche al progetto vanno annotate qui
quando cambiano decisioni o stato del banco; il dettaglio puntuale resta nel `git log`.

### 19 ottobre 2026 — dal lato software

- **Firmware e software sono riuniti in questo repository.** Le sorgenti canoniche sono
  `master/` (0.4.22-RB2, attivo), `slave/` (0.6.1, attivo),
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
- Punto di misura a Z 21.0 (8.55 mm dalla vecchia sede del comparatore verso il rullo) per non toccare la ruota (Ø63.7, circonferenza 200 mm): gioco scheda-ruota 0.9 mm, scheda-rullo 1.2 mm.
- Rullo inferiore (cuscinetti 625 Ø16), suo braccio e supporto dello spintore spostati di **13 mm** verso l'esterno; piastra allargata di 13 mm su quel lato (Z −9.4). Appoggio centrale con la vecchia sede rimosso.
- Torre = colonna v2 (L2 Ø19.95, sede laser corretta) fusa alla piastra; coperchio con viti a 40/75/133 mm dal chip; vite carrello a X −6 (lontana dal perno dello spintore).
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
- ~~Solo controllo di sintassi con g++ su librerie simulate: mai compilato con il core ESP32 reale~~ → **compilato davvero il 19/10/2026** con l'`arduino-cli` dentro l'IDE Arduino (core esp32 3.3.8): master laser 82% di flash, banco 23% e 25%, master calibro 85%, slave 26%. **Provato sull'hardware: ancora no.**
- Slave — **0.6.1**, porting su ESP32 classico per la scheda (solo pin cambiati). **Nel repo** in `slave/`. Sul classico i GPIO 6-11 sono la flash, quindi i pin S3 della 0.5.1 non possono funzionare: non è un riordino.

## Da fare / punti aperti
- [x] ~~Eliminare a mano `firmware/RazorGauge_esp32s3`~~ → **fatto 19/10/2026**: archiviato in `_archivio_NON_USARE/`, e la copia nel repo (`gauge_esp32s3/`) è conservata come variante S3, non come firmware attivo.
- [x] ~~Leggere dal vecchio ESP32 il PPC attivo e annotarlo~~ → **fatto 19/10/2026. PPC attivo letto: 30.2100 (calibrato).** Verificato su linea graduata al metro, 18 punti da 100 a 1798 cm: un solo errore di scala dello **0.087%** (il salto da −1 a −2 cm è il troncamento `(int)`, non due regimi). **PPC corretto da impostare: 30.1837** (`setppc:30.1837`). Niente slittamento, nessuna dipendenza dal diametro — conferma sperimentale della decisione "contatto tangente → nessuna correzione".
- [ ] Ricontrollare col calibro l'interasse dei fori della scheda sensore (20 mm a mano vs 21.2 mm nello STL — le asole accettano entrambi)
- [ ] Misurare lo spot del laser a 5–10 cm (serve ≥ ~1.3 mm per i cavi da 3 mm)
- [x] `MEAS_OFFSET_CM` = 2.800 cm da CAD nel master 0.5.5 — [ ] verifica al collaudo (segno sulla linea)
- [x] (master 0.6.0: corretto, slave invariato) Decidere se correggere nel master la conversione GOTOPOS verso lo slave (lo slave usa 30 impulsi/cm fissi; con PPC calibrato ≠ 30 il GOTOPOS si ferma nel punto sbagliato della stessa percentuale). Proposta: inviare `cm × PPC_attivo / 30`, solo nel master
- [ ] Acquistare: transistor, filtro ND OD 2–3 (solo se il sensore satura), passabanda 650 nm (~12×6×1 mm, sul chip), spine calibrate 0.5 / 1.5 / 2.0 / 2.5 / 3.0 mm
- [x] Ordinare la stampa MJF (stl/) — in stampa dal 4/10/2026
- [ ] Primo collaudo: compilare, flash, WiFiManager (AP "DiametroLinea_Setup", pwd 12345678), prenotazione DHCP, `gauge_dark` + `gauge_ref` senza cavo, collimazione, calibrazione con spine, verifiche al banco
- [ ] Collaudo laser vs calibro: stessa coda passata due volte (sistema vecchio 0.4.22 col calibro, poi sistema nuovo col RazorGauge), export CSV da `/export`, confronto per cm. Atteso rapporto calibro/laser ≈ 0.92–0.93 e STABILE lungo la coda (non uguaglianza)
- [ ] Confermare i diametri delle spine (domanda lasciata come commento nel documento)

## Sviluppi futuri (decisi di rimandare)
- **Velocità di scansione** (6/10/2026, non implementato per scelta): oggi 2 cm/s, limite ereditato dal calibro. Il firmware registra 1 punto/cm; il RazorGauge fa ~1 misura ogni 35 ms (8 letture) e il punto è la mediana delle ultime 7 misure (~0.25 s).
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
- Slave attivo 0.6.1 su ESP32 classico: PUL/DIR/ENA GPIO25/26/27, pulsanti GPIO32/33/34, UART GPIO16/17 → `slave/slave.ino`. La versione S3 precedente è storica e non va usata al posto dello slave attivo.
- Master laser (1.0.0-alpha): `#define USE_RAZORBOARD 1` (scheda, encoder 32/33). Per tornare al vecchio cablaggio volante (encoder 12/13) mettere 0.
- Da verificare: interasse file del nuovo slave CH340C (atteso 25.4 mm), dimensioni dei moduli per la serigrafia.
- Layout: moduli con USB sul bordo superiore, aree senza rame sotto le antenne, morsetti su bordo inferiore (encoder, RazorGauge, TB6600, pulsanti) e sinistro (24 V, 5 V ext), pulsanti a destra, fori M3 agli angoli; piste di potenza 1 mm, segnali 0.4 mm, piani GND su entrambi i lati. Sbroglio con Freerouting 1.9; pipeline rigenerabile con `scheda/script/run_all.sh` (KiCad 7 + Java).
- Viste 3D: `scheda/immagini/RazorBoard_3D_iso/top/morsetti/retro.png` (texture reale dei layer + modelli semplificati dei componenti; script `scheda/script/render3d.py`, pyvista). Ingresso fili dei morsetti verso il bordo scheda.
- Prossimo passo: revisione visiva (aprire RazorBoard.kicad_pcb in KiCad 7+), verifica del verso d ingresso fili dei morsetti, ordine PCB.

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
- ERRORE NOTO nel pezzo unico già stampato: parete encoder a X 4.2–7.2 (nell'originale X 0–3) → la ruota originale con mozzo resta 5 mm avanti. Soluzioni: ruota girata + Loctite 641, mozzo accorciato a 6 mm, oppure ruota su misura `RG_ruota_encoder` (Al, Ø63.66 ±0.10, disco pieno, mozzo Ø18×6.78, foro Ø6 6.01–6.03, 2 grani M3; montaggio 10.0 mm parete→cerchio, un grano sul piano dell'albero LPD3806). In una ristampa del pezzo unico riportare la parete a X 0–3.
- Vista 3D sede encoder: `integrazione_profiler/Ruota_encoder_3D.html`.
- RazorBoard SMD (già ordinata): U1 TRACO TSR 2-2450 da saldare a mano, pin 1 sul pad quadrato (corpo 14 mm, sporge ~1 mm dalla serigrafia TSR-1: ok). D2 SMBJ33CA protegge poco il TSR (max 36 V): eventuale sostituzione a mano con SMBJ28A (stesso SMB). Accendere dal lato 220 V con i 24 V già collegati, oppure aggiungere 22–47 µF/50 V elettrolitico sui poli di J1.
