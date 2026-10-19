# Ultimo passo: rinominare la cartella

Il prodotto si chiama **RazorGauge** e il repo su GitHub pure. Resta da allineare la cartella
locale, che si chiama ancora `flylineprofiler`.

**Non si può fare da dentro**: con la cartella aperta in VS Code (o con una sessione che ci lavora)
la rinomina fallisce con `Device or resource busy`. Nemmeno `dotnet build-server shutdown` basta —
è la working directory stessa a tenerla.

## Procedura

1. **Chiudi VS Code** e ogni terminale aperto dentro la cartella
2. Da una finestra qualsiasi *fuori* dalla cartella:

```
cd C:\Users\Stefano\Documents\Arduino
ren flylineprofiler RazorGauge
```

3. Riapri VS Code su `C:\Users\Stefano\Documents\Arduino\RazorGauge`

## Cosa è già pronto

- Il remoto git punta già a `https://github.com/stefanodemartini/RazorGauge.git`
- La **memoria di progetto** è già stata copiata sul nuovo percorso: aprendo la cartella rinominata
  la sessione ritrova tutto. (La memoria è indicizzata sul percorso: senza la copia sarebbe
  ripartita vuota.)
- Il puntatore in `Documents/Claude/RazorGauge/LEGGIMI.md` cita il percorso **vecchio**: va corretto
  dopo la rinomina, è l'unico riferimento rimasto da aggiornare.

Fatto questo, **cancella questo file**: esiste solo per ricordare un passo che si fa una volta.
