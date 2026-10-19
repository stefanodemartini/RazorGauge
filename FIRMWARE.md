# Firmware — dove sta, e quale gira

**Questa è l'unica casa del firmware.** Non esistono copie altrove: quelle che c'erano in
`Documents/Claude/RazorGauge/` sono state archiviate, perché tre copie dello stesso file con tre
contenuti diversi hanno già portato a leggere quella sbagliata per giorni.

| cartella | versione | board | stato |
|---|---|---|---|
| `master/` | **0.4.22-RB2** | ESP32 classico | **ATTIVO** — col calibro centesimale |
| `slave/` | **0.6.1** | ESP32 classico (DevKit V1 30p, RazorBoard) | **ATTIVO** — controllo motore |
| `master_razorgauge/` | 0.6.0 | ESP32 classico | preliminare — sostituisce il calibro col RazorGauge ottico, web UI rimossa |
| `gauge_esp32/` | — | ESP32 classico | sensore ottico RazorGauge |
| `gauge_esp32s3/` | — | ESP32-S3 | sensore ottico, variante S3 |

Si resta sulla **0.4.22-RB2 finché c'è il calibro**; si passa alla 0.6.0 quando si implementa il
laser. Le due non sono intercambiabili: la 0.6.0 non legge il calibro e non serve la pagina web.

## Compilare

L'`arduino-cli` è dentro l'IDE, non serve installarlo:

```
"C:/Users/Stefano/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe" \
    compile --fqbn esp32:esp32:esp32 master/master.ino
```

`gauge_esp32s3` vuole `--fqbn esp32:esp32:esp32s3`. Occupazione flash all'ultima verifica: master
85%, slave 26%, master_razorgauge 82%, gauge 23% e 25%.

## Lo slave non è un riordino

La 0.5.1 era per **ESP32-S3**. Sul classico i **GPIO 6-11 sono cablati alla flash**, quindi i pin
di allora — ENA su 6, pulsanti su 10 e 11 — non possono funzionare. La 0.6.1 è il porting, non una
pulizia: non tornare indietro.

## Il banco sta altrove

Meccanica, scheda, ottica e CAD sono in `C:/Users/Stefano/Documents/Claude/RazorGauge/`, e il suo
**`STATO_PROGETTO.md` è la fonte autorevole** per come è fatto il banco — leggerlo prima di
ragionare su encoder, calibro o geometria. Due decisioni già prese che da qui non si deducono:

- **contatto tangente con rullo di contrasto → nessuna correzione della lunghezza in base al
  diametro.** L'accumulatore `actualPositionCm` e il commento su `C_eff = 20 - π·d/10` ancora nel
  master sono i resti morti di un approccio che qui non si applica
- **il calibro legge ~7-8% in meno del reale** (il PVC si deforma sotto la molla), e nulla lo
  compensa: l'offset nel firmware è additivo, non un guadagno
