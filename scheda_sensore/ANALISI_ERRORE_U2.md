# RazorSensor v1 — analisi dell'errore su U2, rimedio e prevenzione (26/11/2026)

Documento della sessione Cowork (hardware). Diagnosi al banco: `STATO_PROGETTO.md`, sezioni del 25/11/2026.

## 1. In cosa consiste l'errore di progetto

Circuito voluto: buffer **non invertente** con offset, `Vout = 0.958·AO + 0.154 V`.
Segnale (AO_RAW + VREF tramite R4/R7) sull'**ingresso +**, uscita riportata sull'**ingresso −** dal partitore R8/R9
(reazione **negativa**).

`scheda_sensore/script/sens_def.py` collegava U2 per **numero** di pin con una piedinatura presa a memoria:

| Pin | Rete collegata | Funzione supposta | Funzione reale TI LMV321IDBVR (SLOS263, tab. 5-2, DBV) |
|---|---|---|---|
| 1 | AO_BUF (ADC, R8) | OUT | **IN+** |
| 2 | GND | V− | V− |
| 3 | VP (segnale + offset) | IN+ | **IN−** |
| 4 | VN (R8/R9) | IN− | **OUT** |
| 5 | VDD | V+ | V+ |

Uscita vera (pin 4) → R8 → ingresso + (pin 1): **reazione positiva**. L'operazionale diventa un comparatore con isteresi,
bloccato a 0 V oppure a ~3.2 V, indipendente dalla luce. Spiega tutte le misure del 25/11 (0 V, poi 3.2 V; 142 / 3155 mV
piatti su tutti i pixel; segnale nullo anche con 20 ms di laser).

## 2. Perché è successo (cause)

1. **Piedinatura a memoria.** "1 OUT / 3 IN+ / 4 IN−" è la disposizione più comune degli operazionali SOT-23-5
   (MCP6001-OT, molti cloni "LMV321"); il TI LMV321 in DBV usa l'altra. Il datasheet del codice ordinato non è stato aperto.
2. **Collegamenti per numero, non per nome.** Il simbolo KiCad `Amplifier_Operational:LMV321` era giusto
   (1 "+", 3 "−", 4 uscita); lo script assegnava le reti ai numeri senza confrontare i nomi. Nello schema "AO_BUF" stava
   sul pin "+", ma lo schema a sole etichette di rete non è stato riletto pin per pin.
3. **Controlli tutti coerenti con l'errore:** ERC (uscita su rete passiva = lecito), DRC (PCB = schema), verifica
   scheda/MJF/CNC (solo meccanica), anteprima JLC controllata **solo sul pin 1**, partendo dalla nota "pin 1 (OUT)" scritta
   da noi in `NOTE_ORDINE_JLC.txt` → verifica circolare.
4. **Nessuna simulazione della catena analogica** ricavata dalla netlist (simulato solo l'algoritmo del firmware).
5. **Controllo diseguale:** U1 verificato sul datasheet, U2 considerato "banale".

## 3. Rimedio sulle schede v1

**A — giusto: U2 → MCP6001T-I/OT** (Microchip DS20001733, SOT-23-5 "OT": 1 VOUT / 2 VSS / 3 VIN+ / 4 VIN− / 5 VDD
= piedinatura del PCB). Nessun'altra modifica. Solo suffisso **T-I/OT**, marcatura **AA..**; NO MCP6001R / MCP6001U.
Adatto: 1.8–6 V, ingressi e uscita rail-to-rail (offset +0.15 V e bianco ~2.8 V nel campo), 1 MHz, Vos ≤ 4.5 mV
(tolto dal buio), stabile con R10 100 Ω + 1 nF della RazorBoard. Ordinato il 25/11 (RS, marcatura AA39).

Rilavorazione:
- U2 è a ~4 mm dal TSL1401CL (plastica trasparente, sensibile a calore e fumi): saldatore a punta fine + pinzette
  (o due saldatori); se aria calda, U1 protetto con Kapton + alluminio, temperatura e tempo bassi.
- Finestrella di U1 coperta col nastro; poco flussante, pulizia con isopropilico lontano dalla finestrella.
- Prima di alimentare: pin 1 verso R4; niente corto pin 5–pin 2; pin 2 a GND.
- Dopo: pin 1 ~0.15 V al buio e sale con la luce; poi `gauge_dark` + `gauge_ref` da `/diag`.

**B — solo prova rapida:** togliere U2 e ponticello AO_RAW (lato R3/R4) → piazzola 1 di U2. Senza offset il buio cade sotto
il pavimento dell'ADC (~0.15 V, zona non lineare): fondo dell'ombra tagliato, bordi meno precisi. Non per misurare.

## 4. Firmware: tempo di assestamento per pixel (da fare)

`gReadFrame()` legge ogni pixel 1 µs dopo il fronte del clock. Al bordo dell'ombra il gradino è ~2 V; MCP6001 sale a
0.6 V/µs → ~3.5 µs (anche l'LMV321, 1 V/µs, sarebbe stato al limite). Portare l'attesa a **5 µs** (+0.5 ms per frame).

## 5. Laser e JP2

LFD650-1-12: 3–12 V, 15–30 mA, potenza regolata internamente. JP2 1-2 = 3.3 V (attuale, 0.3 V di margine), 2-3 = 5 V.
Partiti da 3.3 V per prudenza (involucro in ottone al positivo). Dopo la riparazione di U2: `gauge_ref` con JP2 1-2;
se picco 1700–2300 mV a esposizione breve (centinaia di µs) e stabile → resta; se l'esposizione sale verso il massimo,
picco basso o uniformità instabile → spegnere, JP2 su 2-3, rifare buio e riferimento. L'esposizione salvata oggi
(20000 µs) viene dal riferimento con U2 bloccato e non dice nulla sul laser.

## 6. Prevenzione (regole da ora in poi)

Skill salvate: `verifica-progetto-scheda` (nuova) e `jlcpcb-ordine-pcba` (aggiornata). Nessun ordine PCB/PCBA senza:
1. piedinatura di ogni IC dal datasheet del codice ESATTO (MPN con suffisso, package, LCSC dello stesso produttore),
   con fonte e pagina (`scheda_sensore/pinout_datasheet.json`);
2. collegamenti degli IC per NOME di funzione, numeri ricavati dalla tabella, errore se non corrispondono;
3. script `strumenti/verifica_elettrica_scheda.py`: datasheet ↔ netlist ↔ PCB, reazione degli operazionali sull'ingresso −,
   reti con un solo pin, simulazione DC della catena analogica contro la formula di progetto; test di non regressione:
   la configurazione v1 deve dare ERRORE;
4. revisione indipendente (agente separato che NON legge le nostre note) delle piedinature sul datasheet;
5. anteprima JLC: funzione di OGNI pad, non solo il pin 1.

Rev 1.2: solo BOM, U2 = MCP6001T-I/OT (LCSC da verificare); gerber e CPL invariati.
Lavoro da fare in VS Code: compiti 1–6 nel prompt preparato il 26/11 (pinout_datasheet.json, sens_def per nome di pin,
verifica_elettrica_scheda.py, BOM e note d'ordine rev 1.2, STATO_PROGETTO, attesa 5 µs in gReadFrame).
