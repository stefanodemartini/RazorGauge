# Allineamento guidato del laser — pagina `/align` (29/10/2026)

Modulo `master_razorgauge/gauge_align.inc` per il master col laser (file pronto nella cartella dello sketch, **non ancora incluso**).
Scritto sulla struttura della 0.6.0 (`gCapture`, `gAverage`, `gaugeTask`, `gaugeHttpSetup`, `server`, `gMux`,
`G_NPIX`, `G_MV_SAT`, `G_EXP_MIN/MAX`, `gExposureUs`) e verificato con un controllo di sintassi g++ sulla 0.6.0 e sulla **1.0.1-alpha** attuale (con le 3 righe sotto).
**Va integrato dalla sessione del firmware** e compilato con arduino-cli.

## Integrazione (3 righe)
1. `#include "gauge_align.inc"` dopo il codice del gauge e prima di `gaugeTask()`.
2. In `gaugeTask()`, come prima istruzione del `for(;;)`: `if (gAlignActive()) { gAlignStep(); continue; }`
3. In `gaugeHttpSetup()`: `gaugeAlignHttpSetup();`

`ALIGN_PIX_FIRST` / `ALIGN_PIX_LAST` (default 16 / 125, per il sensore attuale con i pixel 0–13 morti; con la
scheda TSL1401CL nuova: 2 / 125). La finestra usata è simmetrica attorno al centro fisico 63.5, così il baricentro
non è falsato dai pixel esclusi. Il protocollo WebSocket verso l'app WPF non cambia. Il modo allineamento è attivo
solo mentre la pagina è aperta (si spegne 5 s dopo l'ultima richiesta). L'esposizione si regola da sola (picco al
55–80% di G_MV_SAT) e alla fine resta quella trovata: **dopo l'allineamento rifare `gauge_dark` e `gauge_ref`**.

## Cosa vede l'utente (http://<ip-del-master>/align)
1. **Fascio**: controlla che arrivi luce e che non saturi.
2. **Ellisse**: "ruota il laser finché la larghezza è massima" (asse lungo della macchia lungo la fila di pixel).
3. **Verso del grano frontale** (una volta sola, poi ricordato dal browser): "stringi 1/8 di giro". La pagina misura
   il verso e quanti pixel si sposta il fascio per ogni ottavo di giro.
4. **Lungo la fila**: istruzioni continue, per esempio "Grano FRONTALE: STRINGI (orario) di circa 2 ottavi di giro",
   "ALLENTA … 1/16 di giro", "un tocco", fino a ±4 px (0.25 mm) stabili per 3 s.
5. **Di traverso** (il sensore non vede la posizione, solo quanta luce arriva): grano LATERALE a passi di 1/16 con
   il pulsante "Passo fatto". La pagina trova i due punti in cui il segnale scende all'80% del massimo e dice di
   quanti sedicesimi tornare indietro per stare a metà; controllo finale ≥ 95%.
6. **Stabilità**: 2 minuti senza toccare. Se il baricentro deriva ≤ 1 px e il segnale ≤ 3%: "PRONTO PER LA RESINA".

Grano FRONTALE = quello raggiungibile dal foro nel coperchio (sposta il fascio lungo la fila). Grano LATERALE =
quello sul fianco della torre verso il rullo (sposta il fascio di traverso). Chiave esagonale 1.5 mm.
Grani in **nylon**: l'involucro del laser è a +3.3 V.

`strumenti/allineamento_laser/simulazione_pagina.js` (node): simula un fascio con errori iniziali di 0.9° e 0.6° e un utente che esegue le
istruzioni. Risultato finale: 0.02 mm lungo la fila, 0.11 mm di traverso, poi "PRONTO PER LA RESINA".
`strumenti/allineamento_laser/pagina_align_esempio.png`: la pagina con dati simulati.
