# Prompt per la sessione VS Code — prevenzione errori di piedinatura e rev 1.2 RazorSensor (preparato il 26/11/2026)

Da incollare nella sessione VS Code. Contesto e motivazioni: `scheda_sensore/ANALISI_ERRORE_U2.md`.

```
CONTESTO
Errore di progetto sulla scheda sensore RazorSensor v1 (diagnosi in STATO_PROGETTO.md, 25/11/2026; analisi in
scheda_sensore/ANALISI_ERRORE_U2.md): in scheda_sensore/script/sens_def.py U2 e' collegato per NUMERO di pin con la
piedinatura "1 OUT / 3 IN+ / 4 IN-", presa a memoria, mentre il TI LMV321IDBVR (C7972) ha 1 IN+ / 2 V- / 3 IN- / 4 OUT /
5 V+ -> reazione positiva, uscita bloccata. Il PCB v1 e' corretto per un operazionale 1 OUT / 2 V- / 3 IN+ / 4 IN- / 5 V+
(MCP6001T-I/OT), gia' ordinato da Stefano per rilavorare le schede.
Obiettivo: rendere questo errore impossibile in futuro e preparare la rev 1.2 (solo BOM).

REGOLE OBBLIGATORIE (piu' sessioni sullo stesso repository)
1. git pull; rileggi ogni file dal disco subito prima di modificarlo.
2. Solo modifiche puntuali (Edit). Mai riscrivere un file intero da una copia in memoria.
3. Prima del commit: git diff --stat e git diff; se compaiono righe tolte non richieste, fermati e avvisami.
4. Dopo il commit: git push.
5. NON rigenerare PCB, gerber, CPL ne' i file in scheda_sensore/produzione/ salvo dove indicato: il PCB v1 resta valido.

COMPITO 1 - Tabelle dei pin dal datasheet (unica fonte di verita')
Crea scheda_sensore/pinout_datasheet.json con, per ogni circuito integrato, il codice ESATTO (MPN con suffisso, package,
produttore, codice LCSC) e la tabella numero -> funzione presa dal datasheet ufficiale, con fonte (documento, revisione,
tabella/pagina). Minimo:
- U1 TSL1401CL (ams, package CL, C2802316): datasheet ams v1-01 gia' nel repo.
- U2 rev 1.2: MCP6001T-I/OT (Microchip, SOT-23-5 "OT", DS20001733): 1 VOUT, 2 VSS, 3 VIN+, 4 VIN-, 5 VDD.
  Voci "NON compatibili con questo PCB": TI LMV321IDBVR (1 IN+, 2 V-, 3 IN-, 4 OUT, 5 V+), MCP6001R, MCP6001U.
Nessuna piedinatura a memoria: aprila dal datasheet e cita la pagina. Se non trovi il datasheet, fermati e chiedimelo.

COMPITO 2 - Collegamenti per NOME di pin in sens_def.py
add() deve accettare per i circuiti integrati i collegamenti per nome di funzione, es.
  U2: {"OUT": "AO_BUF", "V-": "GND", "IN+": "VP", "IN-": "VN", "V+": "VDD"}
e ricavare i numeri da pinout_datasheet.json (errore bloccante se un nome manca o un pin resta non assegnato senza essere
dichiarato NC). R, C e J1 restano per numero. U2 -> MCP6001T-I/OT (valore, MPN, simbolo Amplifier_Operational:MCP6001-OT
se disponibile) con il codice LCSC CORRETTO verificato sul sito LCSC (Microchip, SOT-23-5, suffisso T-I/OT). Non inventarlo:
se non lo trovi, lascialo vuoto e segnalamelo. La netlist di U2 deve restare identica al PCB v1 (1 AO_BUF, 2 GND, 3 VP,
4 VN, 5 VDD).

COMPITO 3 - strumenti/verifica_elettrica_scheda.py
Legge sens_def.py, pinout_datasheet.json e scheda_sensore/RazorSensor.kicad_pcb (rete di ogni pad). Esito OK/ERRORE per
riga, codice di uscita != 0 se c'e' un errore:
a) per ogni IC: numero pad -> funzione (datasheet) -> rete voluta (sens_def) == rete del pad nel PCB;
b) operazionali: uscita chiusa sull'ingresso INVERTENTE (percorso resistivo OUT -> IN-); nessun percorso resistivo
   OUT -> IN+ senza percorso verso IN-; ingressi non flottanti; alimentazioni su VDD/GND;
c) nessuna rete con un solo pin; nessuna uscita su rete di alimentazione;
d) simulazione DC dalla netlist (calcolo nodale in Python, operazionale guadagno ~1e5 limitato tra 0 e VDD; ngspice se
   installato): AO_RAW 0..2.0 V a passi di 0.1 V, confronto con Vout = 0.958*AO + 0.154 V (tolleranza 10 mV), segno della
   reazione negativo (dVdiff/dVout < 0). Stampa la tabella.
TEST DI NON REGRESSIONE (obbligatorio): con la definizione v1 (TI LMV321IDBVR, 1 AO_BUF / 3 VP / 4 VN) lo script DEVE dare
ERRORE; con MCP6001T-I/OT DEVE dare tutto OK. Mostrami entrambe le uscite. Esito in scheda_sensore/verifica_elettrica_<data>.txt.

COMPITO 4 - BOM e note d'ordine rev 1.2
- scheda_sensore/produzione/RazorSensor_BOM_JLCPCB.csv: SOLO la riga di U2 -> MCP6001T-I/OT con il codice LCSC verificato.
  Gerber e CPL invariati: verifica che la rotazione di U2 nel CPL resti valida per il footprint MCP6001 su JLC (pin 1 = VOUT)
  e annota cosa controllare nell'anteprima.
- scheda_sensore/NOTE_ORDINE_JLC.txt: correggi "U2 LMV321 (SOT-23-5): pin 1 (OUT) verso il chip" -> MCP6001T-I/OT,
  pin 1 = VOUT; aggiungi: "Nell'anteprima controllare per OGNI pad la funzione (datasheet) e la rete del PCB, non solo il
  pin 1. Prima di ordinare: python strumenti/verifica_elettrica_scheda.py deve dare tutto OK."
- Se KiCad e' disponibile sul PC, aggiorna lo schema (simbolo MCP6001-OT) e rigenera il PDF con i nomi dei pin visibili;
  altrimenti scrivi in STATO_PROGETTO che schema/PDF restano da aggiornare.

COMPITO 5 - STATO_PROGETTO.md
Rileggilo dal disco subito prima; aggiungi SOLO in fondo una sezione con: pinout_datasheet.json, sens_def per nome di pin,
verifica_elettrica_scheda.py (v1 = ERRORE, rev 1.2 = OK), BOM rev 1.2 U2 MCP6001T-I/OT (LCSC ...), versione firmware del
compito 6. Regola: nessun ordine PCB/PCBA senza verifica_elettrica_scheda.py tutto OK e revisione indipendente delle
piedinature sul datasheet.

COMPITO 6 - master_razorgauge: tempo di assestamento per pixel
In gReadFrame() porta delayMicroseconds(1) prima di gAdcMv() a delayMicroseconds(5), con commento:
"assestamento del buffer U2 (MCP6001, slew 0.6 V/us: gradino di 2 V al bordo dell'ombra ~3.5 us)".
FIRMWARE_VERSION -> versione successiva (+ riga in FIRMWARE_FEATURES). Nessun'altra modifica. Compila e riporta la flash.

ALLA FINE dimmi: le due uscite dello script (v1 = ERRORE, rev 1.2 = OK); codice LCSC del MCP6001T-I/OT e dove l'hai
verificato; file modificati con righe aggiunte/tolte; hash del commit pushato.
```
