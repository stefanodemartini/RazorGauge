# RazorGauge — procedura di primo avvio e prove al banco (master 0.6.0)

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
- Senza buio/riferimento la pagina mostra il frame grezzo ogni 0.2 s.
- La curva blu deve essere una campana centrata, che copre bene i 128 pixel, senza tratti piatti in alto (saturazione).
- Ruota il laser nella sede (grani) finché la campana è più larga possibile: l'asse lungo dello spot va lungo la linea di pixel.

## 3. Buio e riferimento (senza cavo)
1. **Buio**: il laser resta spento. Atteso: "buio massimo" sotto ~400 mV.
2. **Riferimento**: auto-esposizione. Atteso: picco 1700–2300 mV, **saturi 0**, uniformità ≥ 30 %.
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

## 7. Deriva (30–60 minuti)
Spina ferma, sistema acceso. Ogni 10 minuti **Statistica 200**: la media non deve spostarsi più di 5 µm e l'uniformità non deve crescere.
Se deriva: si rifà il riferimento prima di ogni scansione (lo automatizziamo nel firmware).

## 8. Scansione vera
Stessa coda di topo col sistema nuovo, esportata da `/export`; confronto col profilo fatto col calibro (atteso rapporto calibro/laser ≈ 0.92–0.93 e **stabile** lungo la coda).

## Cosa è cambiato nel firmware 0.6.0 (rispetto a 0.5.5)
- ADC in **mV calibrati** (curva di fabbrica) e 2 letture per pixel; soglie di esposizione nella zona lineare dell'ADC.
- Il primo scarico del sensore non viene più letto (solo clock): luce ambiente nella posa da ~3 ms a ~30 µs, misura più veloce.
- Il buio si acquisisce con la stessa posa del laser e si rifà a ogni riferimento.
- Indici di qualità per ogni misura: energia k, uniformità fuori ombra, picco, pixel saturi, centro, diametro "a fronti" di controllo, motivo se non valida.
- Nuovo comando `gauge_stat [n]` (ripetibilità) e pagina `/diag` + dati `/gauge` (JSON). Protocollo dell'app WPF invariato.
- Buio e riferimento salvati dalle versioni precedenti (in LSB) vengono ignorati: al primo avvio vanno rifatti.
- Algoritmo provato su un simulatore del sensore (`strumenti/firmware_sim`): da 0.5 a 3 mm, errore < 0.5 µm e dev. std < 0.6 µm in condizioni ideali; il banco dirà quanto pesano gli effetti reali.
