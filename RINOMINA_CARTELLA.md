# Ultimo passo: spostare la cartella

Il prodotto si chiama **RazorGauge**, il repo su GitHub pure
(`github.com/stefanodemartini/RazorGauge`, il vecchio URL reindirizza). Resta da spostare la
cartella locale, che si chiama ancora `flylineprofiler` e sta sotto `Documents/Arduino`.

**Destinazione: `C:\Users\Stefano\Documents\Claude\RazorGauge`** — il percorso da cui lavora già
l'altra sessione Claude. Spostando lì, **i suoi percorsi non cambiano**: `cad/`, `scheda/`,
`STATO_PROGETTO.md` restano esattamente dov'erano per lei.

**Non si può fare da dentro.** Con la cartella aperta in VS Code (o con una sessione che ci lavora)
l'operazione fallisce con `Device or resource busy` — è la working directory stessa a tenerla, e
nemmeno `dotnet build-server shutdown` cambia niente.

## Procedura

1. **Chiudi VS Code** e ogni terminale aperto dentro la cartella
2. In `Documents\Claude\RazorGauge` è rimasto solo un `LEGGIMI.md` e un vecchio `.git` con due
   commit: **cancella quella cartella**
3. Da una finestra qualsiasi fuori:

```
move "C:\Users\Stefano\Documents\Arduino\flylineprofiler" "C:\Users\Stefano\Documents\Claude\RazorGauge"
```

4. Riapri VS Code su `C:\Users\Stefano\Documents\Claude\RazorGauge`

## Cosa è già pronto

- Il remoto git punta a `https://github.com/stefanodemartini/RazorGauge.git`
- **La memoria di progetto è già copiata** sul percorso di destinazione
  (`c--Users-Stefano-Documents-Claude-RazorGauge`): è indicizzata sul percorso, senza la copia la
  prima sessione nella nuova cartella ripartirebbe vuota
- CAD e documenti sono **alla radice**, non più sotto `hardware/`: così i percorsi che l'altra
  sessione conosce restano quelli

## Due cose da sapere

**Il firmware esce dallo sketchbook Arduino.** Lo sketchbook è `Documents/Arduino`, e gli sketch
andranno aperti da *File → Apri* invece che dall'elenco. Compilare continua a funzionare: le
librerie restano risolte dallo sketchbook configurato, indipendentemente da dove sta lo sketch.

**"Claude" nomina lo strumento, non il progetto.** È il prezzo di non rompere i percorsi dell'altra
sessione. Se un giorno quella sessione non serve più, `Documents/RazorGauge` sarebbe più pulito —
spostare allora costa quanto costa adesso.

Fatto questo, **cancella questo file**.
