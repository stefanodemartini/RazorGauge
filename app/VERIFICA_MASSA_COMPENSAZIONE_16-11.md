# Verifica compensazione e conservazione della massa — 16/11/2026

Revisione del codice (`ApplyZoneDensities`, `CompensateProfile`, `QuantizeCompensationToRealMaterials`,
`ApplyNozzleTransitions`, `BuildCompensatedSnapshotProject`, `ProjectSegment.MassG`,
`BuildEffectiveSegmentsForFamilySource`, `FlyLinePdfExporter.EffectiveMassG`, `LineDesignBuilder.Build`)
più misure numeriche sui file veri, con script indipendenti dall'app:
- `strumenti/verifica_massa_C.py <NC.flp> <C.flp>`: massa NC contro C (totale, 30 ft, peggiore finestra da 30 cm)
- `strumenti/verifica_massa_zone.py <NC.flp>`: replica di `ApplyZoneDensities(adapt=Yes)` con zone di prova

## 1. File C (Compensate): massa conservata entro lo 0.1 %, diametro continuo

La massa **non** è conservata esattamente per costruzione: il diametro resta quello della soluzione
continua, la densità viene quantizzata ai 2–4 ugelli (più le rampe da 30 cm). L'errore per slice è
ρ_ugello/ρ_ideale − 1, cioè al massimo metà della distanza fra due ugelli vicini.

| File C | totale | 30 ft (AFFTA) | peggiore 30 cm |
|---|---|---|---|
| Nautilus 0.5 C 0.50ips | +0.1 gr (+0.01 %) | −0.1 gr (−0.03 %) | −0.27 % |
| Nautilus 0.5 C 0.65ips | +0.1 gr | −0.1 gr | −0.37 % |
| Nautilus 1.5 C 1.50ips | +0.3 gr (+0.04 %) | −0.2 gr (−0.09 %) | −1.18 % (80–110 cm) |
| ST27-60 V.2 C 0.50ips | +0.0 gr | −0.1 gr | −0.22 % |
| Phantom ExtraHover V.2 C 0.51ips 3noz | +0.3 gr | −0.1 gr | −0.48 % |

Diametro: su 124–186 cambi di densità fra slice per file, nessun gradino; i cambi di pendenza più
forti sono ai nodi di taper (es. 1670 cm), non ai cambi di materiale.

Nota: il messaggio dopo il salvataggio dice "mass-conserving, same rule as a zone" — non è esatto
(vedi sopra: conserva entro ~0.1 % sul totale, non per costruzione).

## 2. Zone NC con densità propria (adatta diametri = Sì): la massa MOSTRATA è sbagliata

`ProjectSegment.MassG` = volume dei diametri **disegnati** × densità media delle slice. Con
l'adattamento i diametri prodotti sono più sottili (zona più densa), quindi la massa mostrata è
gonfiata di circa (ρ_zona/ρ_base − 1). Stesso errore in `BuildEffectiveSegmentsForFamilySource`
(diametri disegnati × densità zona).

Prova su Nautilus 0.5 (base 1.020), zona ρ 1.10:

| Zona | massa reale vs base | massa mostrata vs reale |
|---|---|---|
| 500–1200 cm (bordi a metà taper) | −0.68 % | **+3.15 % (+25 gr)** |
| 300–980 cm (bordi sui nodi) | −1.13 % | **+3.29 %** |
| 302–1200 cm | −0.45 % | **+3.53 %** |

Dove arriva: colonna Mass, totali in basso, CoM/Rg, grafico di analisi, badge AFFTA, sorgente di
Generate Family, e il PDF esportato dalla GUI (peso testa e totale: `EffectiveMassG` somma le slice
solo se la densità varia nel segmento, altrimenti usa `MassG`, quindi un segmento tutto dentro la
zona è sbagliato e uno a cavallo è giusto; il piè di pagina non coincide col totale della tabella
NOZZLES, che usa le slice vere).

Oggi nessun file NC in `Projects/` ha zone con densità diversa da M1 di più di 0.02: nessun PDF già
emesso è toccato. Il CLI (`LineDesignBuilder`) cuoce i diametri nei nodi, quindi lì `MassG` è giusta.

**CORRETTO il 16/11/2026.** `ApplyZoneDensities` passa a ogni segmento i tratti realmente prodotti
(`ProjectSegment.ProducedPieces`: posizioni, due diametri, densità); `MassG` ne è la somma esatta
dei tronchi di cono; `BuildEffectiveSegmentsForFamilySource` (AFFTA, Family) e `EffectiveMassG`
(PDF) li usano; totali, badge AFFTA e grafico pesi vengono ricalcolati subito dopo l'applicazione
delle zone (prima restavano vecchi fino al rebuild successivo della tabella). Anche le righe
raggruppate della tabella di un file C sommano le loro slice invece di un tronco fra i due estremi.
Verifica con harness sull'app vera (copia di Nautilus 0.5 + zona 500–1200 cm ρ 1.10): totale
804.7 gr (prima 830.1), segmenti 300–980 / 980–1420 = 14.067 / 12.492 g, identici allo script;
AFFTA 243.2 gr. File C Nautilus 1.5 C 1.50ips invariato (833.9 gr, righe tabella 834.1 gr).

## 3. Bordo zona a metà segmento: il tratto rimodellato ha lunghezza casuale

Il bordo zona diventa un punto risolto (diametro × √(ρ_base/ρ_zona)); il tratto **fuori** zona fra il
nodo precedente e il bordo resta materiale base ma va linearmente dal diametro disegnato a quello
scalato. Quindi:
- la massa è conservata solo dentro la zona, non nel tratto rimodellato;
- la lunghezza del tratto rimodellato dipende da dove cade il nodo precedente:
  - bordo 2 cm dopo un nodo (302 cm): −0.05 mm in 2 cm, pendenza 27× quella del taper: di fatto un gradino;
  - bordo su un nodo (300 cm): viene rimodellato tutto il taper vicino (30–300 cm, 270 cm), −4 % di massa lì;
  - bordo a metà taper (500 cm): rimodellati 200 cm, −0.9 % sul segmento.
- Uguale nel CLI (`EnsureNodeAt` + scala solo dei nodi dentro la zona).

Possibile correzione (da decidere): rampa di densità di lunghezza fissa (30 cm, come fra ugelli nei
file C) con d = d_disegnato·√(ρ_base/ρ(x)): massa esatta in ogni punto **e** diametro continuo.

## 4. Minori
- File C aperto: `BuildEffectiveSegmentsForFamilySource` dà alle slice di rampa dentro una zona la
  densità dell'ugello invece della propria (< 0.1 gr).
- Lo stesso metodo non applica `DensityMergeThreshold` (0.02): una zona quasi uguale alla base
  conta con la propria densità, mentre il profilo la tratta come base.
