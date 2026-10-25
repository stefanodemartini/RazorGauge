# RazorGauge — procedura di primo avvio e prove al banco (master laser 1.0.1-alpha)

Obiettivo: diametro della coda di topo entro **±0.01 mm**. Le prove sotto dicono se ci siamo e, se no, dove sta il problema.
Annota i numeri (o fai screenshot della pagina /diag) e mandameli.

## 0. Compilazione e caricamento
- Arduino IDE con lo stesso core ESP32 usato finora per il master; scheda **ESP32 Dev Module**.
- Librerie: WiFiManager (tzapu), WebSockets (Markus Sattler) — le stesse del master attuale.
- Carica `master/master.ino` sul modulo MASTER e `slave/slave.ino` sul modulo SLAVE. La compilazione non l'ho potuta fare qui: se l'IDE dà errori, copiami il messaggio.
- Primo avvio: rete WiFi "DiametroLinea_Setup" (password 12345678) → scegli la tua rete. Leggi l'indirizzo IP sul monitor seriale (115200) o sul router; conviene una prenotazione DHCP.

## 1. Pagina di servizio
Apri **http://&lt;ip-del-master&gt;/diag** da PC o telefono. Mostra i 128 pixel in tempo reale:
blu = segnale, grigio = riferimento, nero = buio, rosso = normalizzato (1 = luce piena, 0 = ombra), verde = finestra di misura.
I pulsanti mandano gli stessi comandi `gauge_*` che si possono dare da seriale o dall'app.

## 2. Allineamento del laser (senza cavo, coperchio montato)
- Prima di montare: **LED del modulo Hiwonder coperto** (nastro nero/vernice) o dissaldato. Acceso aggiunge ~100 mV di luce continua (~5% del segnale, prova del 25/10/2026).
- Senza buio/riferimento la pagina mostra il frame grezzo ogni 0.2 s.
- La curva blu deve essere una campana centrata, che copre bene i pixel, senza tratti piatti in alto (saturazione).
- **I pixel 0–13 di questo sensore sono morti** (sempre 0, prova del 25/10/2026): è normale vederli a zero. Il firmware usa solo i pixel 16–125 (`G_PIX_FIRST` / `G_PIX_LAST`); la campana deve coprire bene quella zona.
- Ruota il laser nella sede (grani) finché la campana è più larga possibile: l'asse lungo dello spot va lungo la linea di pixel.

## 3. Buio e riferimento (senza cavo)
1. **Buio**: il laser resta spento. Atteso: "buio massimo" sotto ~400 mV.
2. **Riferimento**: auto-esposizione. Atteso: picco 1700–2300 mV, **saturi 0**, uniformità ≥ 30 % (minimo e uniformità sono calcolati solo sui pixel 16–125).
Prima del riferimento lascia il laser acceso qualche minuto: la lunghezza d'onda del diodo cambia mentre si scalda e sposta le frange d'interferenza.
Da rifare dopo ogni intervento su ottica o meccanica (e, se la prova 7 lo chiede, prima di ogni scansione).

## 4. Ripetibilità (spina ferma)
Spina da 2.0 mm nella gola, ferma. **Statistica N misure** con N = 200.
- Atteso: dev. std **≤ 3 µm**, escursione ≤ 15 µm, uniformità fuori ombra < 1 %.
- "Fronti 50 %" è solo un controllo: può differire dall'area di alcuni µm, è normale.

## 5. Calibrazione con le spine
Per ogni spina (0.5 / 1.5 / 2.0 / 2.5 / 3.0): inseriscila, scrivi il diametro nel campo, **Calibra con spina**.
- Atteso: residui ≤ ±3 µm. Se un punto stona, **Azzera calibrazione** e ripeti.

## 6. Collimazione e posizione (spina da 2.0)
- **Altezza**: misura la spina appoggiata sul fondo della gola, poi sollevata di ~1 mm (spessore sotto). Differenza attesa ≤ 5 µm.
  Se è maggiore: regola il carrello di L2 (vite frontale), poi rifai riferimento e calibrazione.
- **Laterale**: spingi la spina verso un fianco e poi l'altro della gola. Il "centro" cambia; il diametro deve restare entro ±3 µm.
- **Allineamento gola ↔ chip**: con la spina al centro della gola, "centro" (riferito al centro fisico del chip) dice di quanto è spostata la gola. Annota anche il **segno**: indica il lato fisico dei pixel morti. Verso quel lato la gola tollera ~1.0 mm di spostamento (1.9 mm dall'altro); oltre, le linee sottili spinte contro la parete danno "ombra al bordo del sensore".

## 7. Deriva (30–60 minuti)
Spina ferma, sistema acceso. Ogni 10 minuti **Statistica 200**: la media non deve spostarsi più di 5 µm e l'uniformità non deve crescere.
Se deriva: si rifà il riferimento prima di ogni scansione (lo automatizziamo nel firmware).
Annota anche **uniformità (`flat`)**: è l'indicatore della deriva ottica (frange che si spostano). Sotto ~1 % la deriva resta entro pochi µm.

## 8. Tempo di misura
Durante la **Statistica 200** cronometra la durata (o leggi il tempo se il firmware lo stampa): ~90 ms per misura sono attesi con 2 letture ADC per pixel. Serve per rifare la tabella velocità di scansione / rumore in `STATO_PROGETTO.md`.

## 9. Scansione vera
Stessa coda di topo col sistema nuovo, esportata da `/export`; confronto col profilo fatto col calibro (atteso rapporto calibro/laser ≈ 0.92–0.93 e **stabile** lungo la coda).

## 10. Verifica indipendente con Archimede (facoltativa)
Su spezzoni dritti (20–30 cm) di una linea già scansionata: peso in aria e immerso in etanolo, con ρ dell'etanolo misurata nella stessa sessione su un corpo di riferimento. Il volume di Archimede confrontato con quello dello scan dà l'errore reale del gauge (dettagli e precauzioni contro le bolle: `STATO_PROGETTO.md`, sezione 25 ottobre).

## Precisione attesa
Stima teorica: ripetibilità 1–3 µm, accuratezza ±3–5 µm dopo la calibrazione; il limite pratico è la stabilità ottica (indice `flat`), non il rumore dell'ADC. Bilancio completo in `STATO_PROGETTO.md`, sezione 25 ottobre.

## Cosa è cambiato nel firmware 1.0.1-alpha (rispetto a 1.0.0-alpha)
- Pixel usati per la misura limitati a 16–125 (`G_PIX_FIRST` / `G_PIX_LAST`) per i pixel 0–13 morti del sensore montato. Con un sensore sano: `G_PIX_FIRST` = 2.
- Il "centro" resta riferito al centro fisico del chip.

## Cosa è cambiato nel firmware 0.6.0 (rispetto a 0.5.5)
- ADC in **mV calibrati** (curva di fabbrica) e 2 letture per pixel; soglie di esposizione nella zona lineare dell'ADC.
- Il primo scarico del sensore non viene più letto (solo clock): luce ambiente nella posa da ~3 ms a ~30 µs, misura più veloce.
- Il buio si acquisisce con la stessa posa del laser e si rifà a ogni riferimento.
- Indici di qualità per ogni misura: energia k, uniformità fuori ombra, picco, pixel saturi, centro, diametro "a fronti" di controllo, motivo se non valida.
- Nuovo comando `gauge_stat [n]` (ripetibilità) e pagina `/diag` + dati `/gauge` (JSON). Protocollo dell'app WPF invariato.
- Buio e riferimento salvati dalle versioni precedenti (in LSB) vengono ignorati: al primo avvio vanno rifatti.
- Algoritmo provato su un simulatore del sensore (`strumenti/firmware_sim`): da 0.5 a 3 mm, errore < 0.5 µm e dev. std < 0.6 µm in condizioni ideali; il banco dirà quanto pesano gli effetti reali.
