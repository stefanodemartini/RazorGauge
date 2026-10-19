# Il firmware non sta più qui

È tutto nel repo git, **unica casa**:

`C:/Users/Stefano/Documents/Arduino/flylineprofiler/`  → vedi `FIRMWARE.md` lì dentro

| cartella nel repo | cos'è |
|---|---|
| `master/` | **0.4.22-RB2 — ATTIVO**, col calibro |
| `slave/` | **0.6.1 — ATTIVO**, ESP32 classico |
| `master_razorgauge/` | 0.6.0 preliminare, col RazorGauge ottico |
| `gauge_esp32/`, `gauge_esp32s3/` | sensore ottico |

## Perché

Esistevano **tre copie di `master.ino` con tre contenuti diversi** fra questa cartella,
`Claude outputs/` e il repo, e nessuna sotto controllo di versione. Si è letta quella sbagliata per
giorni mentre si diagnosticava un errore di lunghezza. Una casa sola, con la storia, toglie la
classe di errore invece di documentarla.

Le vecchie copie sono in `../_archivio_NON_USARE/`: tenute per sicurezza, **non sono attive**.
Se serve modificare il firmware, si modifica nel repo.
