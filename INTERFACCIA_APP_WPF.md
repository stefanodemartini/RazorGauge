# RazorGauge — interfaccia master 0.6.0 per l'app WPF

Per la sessione che lavora sull'app WPF. Il protocollo esistente **non cambia**: tutti i messaggi e i comandi di prima restano identici.
Le aggiunte sotto sono facoltative: l'app funziona anche senza.

## WebSocket (porta 81) — comandi aggiunti
Testo semplice, come gli altri comandi:

| Comando | Effetto | Note |
|---|---|---|
| `gauge_dark` | acquisisce il buio (laser spento) | senza cavo |
| `gauge_ref` | riferimento con auto-esposizione | senza cavo; rifà anche il buio |
| `gauge_cal <mm>` | aggiunge un punto di calibrazione con una spina di diametro noto | es. `gauge_cal 2.000` |
| `gauge_calreset` | cancella la calibrazione | |
| `gauge_exp <us>` | esposizione manuale | poi rifare `gauge_ref` |
| `gauge_stat [n]` | n misure consecutive (default 200): media, dev.std, min/max | oggetto fermo; ~50 ms a misura |
| `gauge_status` | stato del sensore | |
| `gauge_profile` | profilo normalizzato su seriale | |

Risposta: **solo al client che ha mandato il comando**
`{"type":"gauge","msg":"<testo>"}`
Prima arriva `"RazorGauge: comando in esecuzione..."`, poi il risultato (dark/ref ~1–2 s, stat n×50 ms).
Se un comando è in corso: `"RazorGauge occupato: ..."`.

## HTTP (porta 80)
- `GET /gauge` → JSON dell'ultima misura (aggiornato ~20 volte al secondo):

| Campo | Significato |
|---|---|
| `fw` | versione firmware |
| `n` | contatore misure |
| `ok` / `why` | misura valida / motivo se non valida |
| `diam` | diametro grezzo (mm, metodo dell'area) |
| `cal` | diametro calibrato dell'ultima misura (mm) |
| `disp` | valore registrato nella scansione: mediana delle ultime 7, calibrata (mm) |
| `edge` | diametro "ai fronti 50 %" (mm), solo controllo |
| `center` | posizione dell'ombra rispetto al centro del sensore (mm) |
| `k` | energia del laser rispetto al riferimento (1 = come al `gauge_ref`) |
| `flat` | % scarto della luce fuori ombra: se cresce, rifare `gauge_ref` |
| `peak`, `sat` | picco (mV) e pixel saturi |
| `L`, `R` | finestra di integrazione (pixel) |
| `exp` | posa (µs) |
| `dark`, `ref` | buio / riferimento presenti |
| `ncal`, `calA`, `calB` | calibrazione: mm = calA × misura + calB |
| `busy` | comando gauge in corso |
| `msg` | ultima risposta a un comando |
| `raw[128]` | segnale (mV) |
| `norm[128]` | normalizzato × 1000 (1000 = luce piena, 0 = ombra) |
| `refmv[128]`, `darkmv[128]` | riferimento e buio (mV) |

- `GET /gauge/cmd?c=<comando>` → esegue un comando `gauge_*` (risposta poi nel campo `msg` di `/gauge`).
- `GET /diag` → pagina di servizio nel browser (grafico dei pixel + pulsanti).
- `GET /export`, `GET /encoder` → invariati.

## Idee per l'app (facoltative)
1. Pannello "Sensore": i 128 pixel (`raw`, `norm`) e gli indici `k`, `flat`, `peak`, `sat`, leggendo `/gauge` ogni 300–500 ms solo quando il pannello è aperto.
2. Procedura guidata: buio → riferimento → spine (`gauge_cal`) → `gauge_stat`, mostrando le risposte `{"type":"gauge"}`.
3. Avviso prima della scansione se `flat` > 1 % o `sat` > 0 o `dark`/`ref` mancano.
