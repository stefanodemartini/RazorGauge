# Firmware — dove sta, e quale gira

**Questa è l'unica casa del firmware.** Non esistono copie altrove: quelle che c'erano in
`Documents/Claude/RazorGauge/` sono state archiviate, perché tre copie dello stesso file con tre
contenuti diversi hanno già portato a leggere quella sbagliata per giorni.

| cartella | versione | board | stato |
|---|---|---|---|
| `master/` | **0.4.22-RB2** | ESP32 classico | **ATTIVO** — col calibro centesimale |
| `slave/` | **0.6.1** | ESP32 classico (DevKit V1 30p, RazorBoard) | **ATTIVO** — controllo motore |
| `master_razorgauge/` | **1.0.0-alpha** | ESP32 classico | preliminare — sostituisce il calibro col RazorGauge ottico, web UI rimossa |
| `gauge_esp32/` | — | ESP32 classico | **banco di collaudo** del RazorGauge: laser pulsato + CCD TSL1401, comandi seriali |
| `gauge_esp32s3/` | — | ESP32-S3 | lo stesso, per la scheda S3 precedente |

I due `gauge_*` **non girano nel sistema finito**: sono firmware di banco, sugli stessi pin del
master, per provare la testa di misura (laser + CCD) prima di flashare il master vero. Si comandano
da seriale — `d` dark, `r` riferimento senza cavo, `m` misura, `p` profilo — e non parlano WebSocket.
Quando il RazorGauge entra in produzione è la **1.0.0** a leggere il sensore, non questi.

Si resta sulla **0.4.22-RB2 finché c'è il calibro**; si passa alla **1.0.0** quando si implementa il
laser. Le due non sono intercambiabili: la 1.0.0 non legge il calibro e non serve la pagina web.

**Perché 1.0.0 e non 0.6.0** (come si chiamava): il laser non è un passo avanti sulla linea col
calibro, è un **ramo diverso** — principio di misura diverso, hardware diverso. Numerate in fila,
`0.6.0` accanto a `0.4.22` diceva "più nuova quindi da usare", mentre quella che gira è la 0.4.22.
Così invece **0.x = era calibro, 1.x = era laser**, e la distanza fra i numeri dice che non sono la
stessa cosa. `-alpha` perché compila ma non è ancora stata provata sul banco.

## Compilare

L'`arduino-cli` è dentro l'IDE, non serve installarlo:

```
"C:\Users\Stefano\AppData\Local\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn esp32:esp32:esp32 master/master.ino
```

`gauge_esp32s3` vuole `--fqbn esp32:esp32:esp32s3`. Occupazione flash all'ultima verifica: master
85%, slave 26%, master_razorgauge 82%, gauge 23% e 25%.

Il firmware attivo del master è stato compilato per ESP32; per la scheda e la configurazione
correnti, il target del master è il classico ESP32. Anche lo slave attivo usa il classico ESP32.
Il master regola in retroazione la velocità di scansione; `SCAN_HZ = 1500` sullo slave è il valore
iniziale, non una frequenza fissa garantita durante tutta la scansione.

## Lo slave non è un riordino

La 0.5.1 era per **ESP32-S3**. Sul classico i **GPIO 6-11 sono cablati alla flash**, quindi i pin
di allora — ENA su 6, pulsanti su 10 e 11 — non possono funzionare. La 0.6.1 è il porting, non una
pulizia: non tornare indietro.

## Il banco sta altrove

Meccanica, scheda, ottica e CAD sono **in questo stesso repo** — `cad/`, `scheda/`,
`integrazione_profiler/` — e **`STATO_PROGETTO.md` è la fonte autorevole** per come è fatto il banco — leggerlo prima di
ragionare su encoder, calibro o geometria. Due decisioni già prese che da qui non si deducono:

- **contatto tangente con rullo di contrasto → nessuna correzione della lunghezza in base al
  diametro.** L'accumulatore `actualPositionCm` e il commento su `C_eff = 20 - π·d/10` ancora nel
  master sono i resti morti di un approccio che qui non si applica
- **il calibro legge ~7-8% in meno del reale** (il PVC si deforma sotto la molla), e nulla lo
  compensa: l'offset nel firmware è additivo, non un guadagno
