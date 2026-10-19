# RazorGauge — verifica completa (6 ottobre 2026)

Esito: **nessun errore bloccante** su scheda SMD ordinata, firmware e pezzi in stampa. Corretta una cosa (firmware master impostato per la scheda), restano 3 rischi da gestire al collaudo e i punti aperti già noti.

## Esiti per area

| Area | Controllo | Esito |
| --- | --- | --- |
| Scheda SMD v0.2 | DRC KiCad | OK — 0 errori, 0 connessioni mancanti |
| | Netlist schema / PCB / sorgente | OK — identiche (81 componenti, 55 net) |
| | Pinout ESP32 DevKit V1 30 pin sugli zoccoli | OK — pin 1 = 3V3 lato USB, VIN in alto a destra; modulo con componenti in alto e USB verso il bordo superiore |
| | Pin master sulla scheda vs firmware | OK — SI 26, CLK 27, AO 34, laser 25, encoder A 32 / B 33, WIFI_RST 14, UART 16/17 |
| | Pin slave sulla scheda vs firmware | OK — PUL 25, DIR 26, ENA 27, SCAN 32, FAST_S 33, FAST_O 34, UART 16/17 (incrociata con il master tramite R10/R11) |
| | Polarità diodi, LED, TVS, 2N7002, Traco | OK — pin 1 = catodo su SS34/B5819W/1N4148W/LED; 2N7002 1G 2S 3D; Traco 1 Vin, 2 GND, 3 Vout |
| | 74HC14 (encoder) e 74HCT245 (TB6600) | OK — doppia inversione = polarità originale; 245 con DIR=5V (A→B), OE a GND, ingressi inutilizzati a GND |
| | Pin di avvio ESP32 (0, 2, 5, 12, 15) | OK — nessuno usato |
| | File produzione | OK — gerber completi (rame, maschera, pasta, serigrafia F/B, contorno, forature), BOM 23 righe, CPL 61 componenti |
| Firmware master | Sintassi (g++ con librerie simulate) | OK — compilazione reale non possibile da qui (server Espressif bloccati) |
| | Pin encoder | **CORRETTO** — `USE_RAZORBOARD` era 0 (vecchio cablaggio 12/13): ora 1, versione 0.5.3 |
| Firmware slave | Sintassi | OK |
| | Differenze dall'originale S3 | OK — cambiano solo i pin |
| | Logica ENA | OK — FastAccelStepper abilita con ENA basso; sulla scheda ENA alto (pull-up) = motore libero all'accensione |
| Torre (STL in stampa) | Integrità mesh | OK — tutti chiusi, un solo corpo: torre 58.2 cm³, coperchio 6.9, carrello 2.3 |
| | Quote ottiche | OK — L1–L2 = 80.7 mm (f −19.3 + 100), regolazione L2 −5/+6 mm, piano a 35.4 mm |
| Documenti | STATO_PROGETTO.md | aggiornato (firmware 0.5.3, file S3 da eliminare) |
| | Documento di progetto | pin corretti; **non descrive ancora la scheda RazorBoard** |

## Rischi da gestire

1. **Alimentazione 24 V collegata "a caldo".** Sull'ingresso ci sono solo condensatori ceramici. Se colleghi i fili a un alimentatore già acceso, la sovratensione momentanea può superare i 36 V massimi del Traco. Accendi sempre l'alimentatore dalla rete, a fili già collegati, oppure salda un elettrolitico 47–100 µF 50 V sui morsetti di J1.
2. **Senso di DIR e del conteggio encoder.** Il cablaggio originale del TB6600 non era noto. Se il motore gira al contrario, inverti DIR nel firmware dello slave (`setDirectionPin(DIR_PIN, false)`). Se la lunghezza conta all'indietro, scambia i fili verde e bianco su J4.
3. **Corrente sugli ingressi del TB6600.** Il 74HCT245 è garantito a 6 mA per uscita, mentre gli optoisolatori del TB6600 ne chiedono di solito 8–15. Funziona, con l'uscita un po' sotto i 5 V. Se il motore perde passi ad alta velocità, misura la tensione su PUL+ durante il movimento.

## Altri controlli al collaudo

- **Jumper JP2.** Parti con 1-2 (laser a 3.3 V). Passa a 5 V solo se il laser è previsto per 5 V e serve più luce.
- **ENA.** Se il motore non si eccita mai, scollega ENA+ dal TB6600 (motore sempre abilitato) e avvisami.
- **Laser.** Ruota il laser nella sua sede con i grani finché l'asse lungo dello spot ellittico è lungo la linea del sensore: copre più pixel.
- **Moduli ESP32.** Prima di inserirli, confronta le scritte del modulo (VIN, GND, 3V3) con la scheda: VIN in alto a destra, vicino all'USB.

## Punti aperti già noti

- [ ] PPC encoder dal vecchio ESP32, da reimpostare con `setppc:<valore>`
- [x] `MEAS_OFFSET_CM` (distanza ruota encoder ↔ punto di misura) = 2.800 cm da CAD (master 0.5.5, interasse 28.00 mm) — da confermare al collaudo
- [ ] GOTOPOS: lo slave usa 30 impulsi/cm fissi; con PPC calibrato diverso da 30 si ferma nel punto sbagliato (correzione proposta: inviare `cm × PPC / 30` dal master)
- [ ] Interasse fori della scheda sensore (20 mm a mano, 21.2 mm nel modello; le asole accettano entrambi)
- [ ] Spot del laser a 5–10 cm (serve almeno ~1.3 mm per i cavi da 3 mm)
- [ ] Prima compilazione reale e prova sull'hardware
- [ ] Eliminare `firmware/RazorGauge_esp32s3.ino` dalla cartella sul PC


## Verifica pre-stampa integrazione FlylineProfiler (8/10/2026)
Pezzi da stampare (MJF PA12): `integrazione_profiler/FlylineProfiler_RazorGauge_pezzo_unico.stl` (109.4 cm³: alleggerito e piastra allargata sotto i blocchi guida, 8/10), `_coperchio.stl` (8.20), `_carrello.stl` (3.86), `_slitta_sensore.stl` (1.16). Forcelle: originali dell'utente (non si ristampano).
- [x] STL rigenerati dai sorgenti = file in cartella
- [x] corpo unico, chiusi, nessun vuoto interno, entro il volume di stampa
- [x] spessori ≥ 0.8 mm (3 punti sottili corretti: foro carrello, linguetta slitta/colonnina, alette 0.1 mm)
- [x] nessuna interferenza statica; carrello, slitta, forcelle liberi su tutta la corsa
- [x] fascio ottico libero; linea Ø0.5–3 libera; chip ↔ linea 2.50 mm
- [x] tutte le viti raggiungibili (vite slitta spostata a tx 17)
- [ ] compilare il master 0.5.5 in Arduino IDE
- [ ] al collaudo: verificare MEAS_OFFSET_CM (2.800 cm) con un segno sulla linea
Minuteria: vedi STATO_PROGETTO.md.


## Verifica DEFINITIVA pre-stampa (8/10/2026, 4 giri) — sostituisce la precedente
Pezzi da stampare (MJF PA12), cartella `integrazione_profiler/`: `FlylineProfiler_RazorGauge_pezzo_unico.stl` (107.6 cm³), `_tappo_guida.stl` (**×2**, 2.83), `_coperchio.stl` (8.24), `_carrello.stl` (3.86), `_slitta_sensore.stl` (1.16). Forcelle: originali.
- [x] STL rigenerati dai sorgenti = file in cartella; corpo unico, chiusi
- [x] spessori ≥ 0.8 e fessure ≥ 0.5 ovunque, salvo spigoli originali (grani laser, invito guida originale, vertici finestre encoder)
- [x] fori misurati: piastra Ø3.30 ×10, fissaggi Ø3.40 ×4, encoder Ø22.0, sede encoder Ø53 / fondo 3.0, M3 Ø2.50 ×12 con profondità adeguate alle viti
- [x] nessuna interferenza statica; carrello, slitta, forcelle (con bulloni) liberi su tutta la corsa; forcelle inseribili dall'alto
- [x] fascio libero; linea Ø0.5–3 libera; chip ↔ linea 2.50; interasse 28.00 / 28.00
- [x] tutte le viti raggiungibili, compresi i 4 dei tappi
- Correzioni di questa verifica: tappi removibili (forcella lato misura non inseribile dal basso), gioco forcella 0.3/lato, sede linguetta slitta 0.25, labbro sede −0.5, J accorciate (giochi rotanti ≥ 0.78), vecchio foro chiuso del tutto, radice J. Dettagli in STATO_PROGETTO.md.
- Giochi stretti accettati (statici): scheda ↔ ruota 0.63, scheda ↔ fondo J 0.49. Da guardare al primo montaggio: la ruota non deve sfiorare la scheda.
- [ ] compilare il master 0.5.5 in Arduino IDE; al collaudo verificare MEAS_OFFSET_CM (2.800 cm)
