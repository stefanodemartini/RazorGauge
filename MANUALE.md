# FlyLine Profiler — Manuale Utente

**Versione**: corrente (giugno 2026)
**Piattaforma**: Windows 10/11 (x64), .NET 8

---

## Avvio

Aprire `FlyLineProfiler.exe` oppure fare doppio-clic su un file `.flp` per aprire direttamente un progetto.

La finestra si apre in **Modalità Design** (toggle "Design Mode" attivo in alto a destra).

---

## Interfaccia Principale

```
┌─────────────────────────────────────────────────────────────────┐
│ FlyLine Profiler — [NomeProgetto]                    [Design Mode]│
├─────────┬───────────────────────────────────────────────────────┤
│         │                                                         │
│ Pannello│              GRAFICO PRINCIPALE (ScottPlot)            │
│ Sinistra│                                                         │
│         │                                                         │
├─────────┴───────────────────────────────────────────────────────┤
│              GRAFICO ANALISI MASSA (solo Design)                 │
├─────────────────────────────────────────────────────────────────┤
│ Status Bar: info contestuali                        AFFTA badge │
└─────────────────────────────────────────────────────────────────┘
```

### Pannello sinistro (Design Mode)
- **Project**: gestione file, nomi, info
- **Design Tools**: disegno nodi, reverse, undo, clear
- **Nodes DataGrid**: tabella editabile dei nodi
- **Nozzles**: 4 ugelli (M1–M4) con colore e densità
- **Nozzle Zones**: assegnazione zone colore
- **Segments DataGrid**: tabella segmenti calcolata automaticamente
- **Sinking Tools**: fisica acqua, compensazione

---

## 1. Gestione Progetti

### Creare un nuovo progetto
1. Menu **File → New Project**
2. Inserire un nome nel dialogo
3. Il progetto parte vuoto

### Aprire un progetto
- **File → Open** → selezionare file `.flp`
- **File → Recent** → lista file recenti con popup
- **Doppio-clic** su un file `.flp` da Esplora File

### Salvare
- **File → Save** (`Ctrl+S`): salva sul file corrente
- **File → Save As**: sceglie un nuovo percorso; adotta il nome del file come nome del progetto
- Al salvataggio con serie importate attive, viene chiesto se includerle nel file

### Chiudere
- L'app avvisa se ci sono modifiche non salvate (Yes = salva, No = scarta, Cancel = annulla)

> **Bug corretto (2026-09-09)**: dopo File → Close, la tabella segmenti mostrava ancora le righe del
> progetto appena chiuso. La tabella è collegata a `DisplaySegments` (una vista separata da
> `ProjectSegments`, usata per raggruppare le zone materiale di uno snapshot C — vedi
> `RefreshDisplaySegments`), e `ClearProjectState()` svuotava solo `ProjectSegments`, mai
> `DisplaySegments`. Corretto aggiungendo `DisplaySegments.Clear()` a `ClearProjectState()`
> (`Views/MainWindow.xaml.cs`).

---

## 2. Modalità SCAN (acquisizione hardware)

Attivare **Design Mode OFF** con il toggle in alto a destra. Appaiono i pannelli di connessione e i controlli del motore.

### Connessione all'ESP32
1. Aprire **Settings** (ingranaggio) e verificare IP e porte:
   - Host: `192.168.1.50` (default)
   - WebSocket Port: `81`
   - HTTP Port: `80`
2. Premere **Connect** — il LED status diventa verde
3. Se **AutoConnect** è attivo nelle impostazioni, la connessione parte automaticamente all'avvio

### Avviare uno Scan
1. Premere **SCAN** — invia `motor scan` + `scan_on`
2. Il motore trasporta la linea attraverso il sensore laser
3. I punti appaiono in tempo reale sul grafico
4. Premere **STOP** per fermare il motore e disabilitare la ricezione

### Controlli Motore

| Pulsante | Comando inviato | Effetto |
|---|---|---|
| SCAN | `motor scan` + `scan_on` | Avvia scan completo |
| STOP | `motor stop` + `scan_off` | Ferma tutto |
| Fast → | `motor fast_s` | Avanzamento rapido stessa direzione |
| Fast ← | `motor fast_o` | Avanzamento rapido direzione opposta |
| GOTO | `goto X.X` | Va alla posizione X cm |
| Motor Status | `motor status` | Legge stato motore dal firmware |

### Calibrazione
- **Set Display Zero**: azzera il valore display attuale
- **Reset Offset**: azzera l'offset di misura
- **Set Offset**: imposta un offset manuale in mm
- **Read Raw**: legge il valore grezzo del sensore (output sulla seriale del dispositivo)

### Smoothing

- **EMA ON/OFF**: abilita/disabilita il filtro Exponential Moving Average
- **Alpha slider**: `0.00` = nessun filtro (raw), `1.00` = massimo livellamento; default `0.10`
- **Raw series**: mostra/nasconde la curva non filtrata in arancione

### Esportare i Dati Scan
- **Export CSV**: esporta i punti (cm, mm) in formato CSV
- **Export PNG**: salva il grafico come immagine

### Clear Scan
Cancella solo i dati di scan acquisiti (non il design). Utile per rieseguire uno scan.

---

## 3. Modalità DESIGN

Attivare **Design Mode ON**. Il pannello sinistro mostra i controlli di design; il pannello scan è nascosto.

### Disegnare un Profilo

#### Attivare la modalità di disegno
- Menu **Design → Draw Segments** oppure checkbox nella toolbar
- Il cursore diventa una croce `+`

#### Aggiungere nodi
- **Click sinistro** sul grafico → aggiunge un nodo
  - X = cm (arrotondato all'intero più vicino)
  - Y = diametro in mm (dalla posizione verticale del cursore)
- **Shift + Click**: segmento cilindrico — blocca il diametro al nodo esistente più vicino

#### Rimuovere nodi
- **Click destro** vicino a un nodo (in Draw mode) → rimuove il nodo più vicino

#### Spostare nodi (Drag)
- **Click e trascina** su un nodo esistente (anche senza Draw mode attivo)
- Il profilo si aggiorna in tempo reale; il nodo si fissa al rilascio

#### Editare un nodo con precisione
- **Doppio clic** sul nodo → dialogo "Edit Node"
- Inserire posizione esatta in cm e diametro in mm
- OK per confermare

#### Tabella Nodi
- La **Nodes DataGrid** mostra tutti i nodi in ordine
- Cliccare su una cella per editare posizione o diametro direttamente
- **Add Node** (pulsante "+") → aggiunge un nodo in fondo alla lista con valori di default
- **Delete** su una riga selezionata → rimuove il nodo

#### Undo
- **Ctrl+Z** — annulla l'ultima modifica ai nodi (max 100 step)
- Funziona per: aggiunta, rimozione, drag, edit, reverse, clear

#### Invertire il Profilo
- **Reverse** — specchia le posizioni X mantenendo i diametri
- Utile per impostare l'orientamento corretto (tip=0, reel=max)

#### Cancellare il Profilo
- **Clear Segments** — rimuove tutti i nodi (undoable)

---

## 4. Segmenti e Geometria

### Tabella Segmenti
Con almeno 2 nodi la tabella **Segments** si popola automaticamente:

| Colonna | Descrizione |
|---|---|
| # | Indice segmento (S1, S2…) |
| Name | Nome editabile |
| Start cm / End cm | Posizioni dei nodi |
| Start Ø / End Ø | Diametri in mm (editabili) |
| Length | Lunghezza in cm (editabile — sposta il nodo finale) |
| Shape | Cylinder / Taper (rilevato automaticamente) |
| Taper mm/m | Variazione diametro per metro |
| Sp.W. g/cm³ | Densità specifica |
| Sink m/s | Velocità di affondamento calcolata |

### Totali
Sotto la tabella appare la riga **Totals**:
- Volume totale (cm³) e massa totale (g) se la densità è impostata
- Volume/Massa della testa (se marcata con flag Head)
- **CoM** % e **Rg** % — Centro di Massa e Raggio di Girabilità
- Classificazione del taper (hover sul testo per la descrizione completa)

---

## 5. Ugelli e Colori (Nozzle System)

### Definizione degli Ugelli (M1–M4)
- **M1**: materiale di base — definisce il colore del profilo di design e la sua densità è sempre quella impostata in "Material ρ" (sezione 6). La cella densità di M1 nella griglia è di sola lettura: si modifica solo da "Material ρ" / From Weight / From Sink Speed, per evitare disallineamenti
- Ogni ugello ha: **colore** + **densità** (g/cm³) + **etichetta**
- **La griglia mostra solo gli ugelli realmente in uso**: con un solo materiale si vede solo M1; M2–M4 compaiono automaticamente solo quando servono davvero (densità propria, zona colore assegnata, o attivati manualmente)
- Pulsante **＋ Material** → attiva deliberatamente il prossimo ugello nascosto, per poterlo configurare prima di usarlo in una zona
- Il badge "x/4" indica quanti ugelli sono attivi

### Cambiare Colore
1. Cliccare il swatch colorato accanto a M1/M2/M3/M4
2. Popup con:
   - Palette di colori rapidi (swatches predefiniti)
   - Campo hex manuale (6 caratteri, Enter per applicare)
   - Pulsante "Pick Color" per il dialogo Windows completo

### Zone Ugello
- **Add Zone** → aggiunge una zona al profilo (start cm, end cm, ugello assegnato)
- La zona viene colorata con Lambert cylindrical shading (aspetto 3D solido)
- **Delete** su riga selezionata → elimina la zona
- Sopra la griglia è fissata una riga informativa **M1** (colore, densità, "default — fills where no zone below applies"): M1 non è mai una riga della griglia perché è il materiale base implicito, non una zona esplicita — questa riga evita che sembri "mancante" dalla tabella

### Zona con Densità Propria (materiale diverso da M1)
Se la zona appena aggiunta (o un ugello già assegnato a una zona) ha una densità che differisce da quella di M1 di più di 0.02 g/cm³, l'app considera la zona un materiale realmente diverso — non solo un colore — e chiede:

> *"Adjust the diameters in those zones to preserve their current mass?"*
> **Yes** (default) — i diametri della zona vengono ricalcolati per mantenere la massa attuale (formula a massa costante ρ·d² = cost.)
> **No** — i diametri restano quelli disegnati; il peso della zona cambia di conseguenza

Dopo la conferma:
- **Una zona con materiale proprio è parte del design, non una compensazione**: la finestra resta in NC (griglie editabili, pannello "Material ρ" visibile) e il file resta uno solo — non viene forkato nessun file C
- Il grafico disegna direttamente il profilo reale, con i colori scelti per ciascun ugello/zona (non il gradiente automatico della compensazione fisica)
- La colonna **Sink** della tabella segmenti mostra la velocità di affondamento reale di ogni segmento (non un target unico — ogni zona affonda alla propria velocità fisica)
- Accanto alle colonne di disegno compaiono anche **Comp. Start / Comp. End / ρ Start / ρ End**: con l'adattamento di massa i diametri da produrre non sono quelli disegnati, e servono al produttore
- Le colonne **Sp.W.** e **Mass** mostrano la densità e la massa **realmente applicate** in quel tratto: dentro una zona è quella della zona, non la densità base del design (che resta invariata nel campo sottostante ed è ciò che si modifica digitando nella cella)
- Il profilo viene ricostruito automaticamente anche riaprendo il file e a ogni modifica della geometria, riusando in silenzio la scelta sulla massa salvata nel progetto

### Il bordo della zona e il gradino di diametro
Con l'adattamento di massa attivo (**Yes**), un cambio netto di densità impone matematicamente un
salto di diametro sul bordo: la massa è proporzionale a ρ·d², quindi se ρ salta e la massa deve
restare quella, d salta con lei. Non è un difetto di calcolo — non esiste modo di avere insieme
densità esatta, massa esatta e diametro continuo attraverso un confine netto **usando un solo
segmento**. La soluzione (dal 2026-09-09): **il bordo della zona viene sempre trattato come un nodo**,
e il segmento appena fuori dalla zona viene *rimodellato* fino al suo nodo lontano per assorbire la
transizione:

- **Dentro la zona**: densità piena, nominale, per tutta la sua estensione — nessuna sfumatura.
  Il diametro al bordo della zona = disegnato × √(ρ_base/ρ_zona) (con floor a 0.94 g/cm³), la stessa
  identità usata ovunque per la massa costante.
- **Il segmento appena fuori dalla zona** (quello che la tocca) prende quello stesso valore esatto
  come proprio estremo vicino; il suo estremo lontano resta **esattamente quello disegnato**
  (invariato); resta una retta tra i due, solo con un'altra pendenza rispetto all'originale.
- La continuità al bordo è quindi strutturale (stesso numero, stesso identico calcolo, condiviso da
  entrambi i lati) — zero gradino per costruzione, non una rampa che lo nasconde.
- È lo stesso algoritmo già usato da `LineDesignBuilder` per la CLI (spec JSON → file), applicato ora
  anche alla modalità live delle Nozzle Zones nell'editor.
- **Caso limite**: due zone di densità diverse che si toccano bordo a bordo (senza un tratto M1 in
  mezzo) — quel nodo condiviso non può soddisfare esattamente entrambe. L'app applica la media dei
  due fattori su quel nodo e avvisa in fondo alla finestra ("Two adjacent zones... that node was set
  to the average of both"), senza bloccare.
- **Rinunciare alla massa costante** (**No**): il diametro resta quello disegnato — continuo per
  definizione — e a cambiare è il peso della zona; nessun rimodellamento del segmento adiacente in
  questo caso (non serve).

> **Storia del fix**: la prima versione usava una rampa di transizione di ~10 cm attorno al bordo
> (densità sfumata invece che netta). Il primo giro di correzioni (2026-09-09) ha eliminato l'errore
> di *lettura* del bordo (grafico/tabella/PDF leggevano il centro della fetta invece del bordo vero,
> poi lo leggevano per estrapolazione invece che con la formula esatta) — ma la rampa stessa lasciava
> comunque un gradino residuo minimo, perché proprio sul confine la densità non era mai esattamente
> quella nominale. Su proposta di Stefano, la rampa è stata rimossa del tutto e sostituita col
> rimodellamento del segmento adiacente descritto sopra (`ApplyZoneDensities` in
> `Views/MainWindow.xaml.cs`) — zero gradino per costruzione, non un'approssimazione più fine.
> Il resto del rendering (riempimento colore, Sink Map, `RigidBodySinkSpeed`) non ha dovuto cambiare:
> ogni tratto tra due punti risolti è ora esattamente lineare a densità costante, quindi ricampionarlo
> con le stesse fette fini da ~1cm di prima non introduce più nessun errore.
>
> **Bug correlato corretto lo stesso giorno**: le etichette dei nodi nel grafico a schermo (Ø/posizione,
> divisori, tag "S{n}"/"M{n}") in modalità compensata leggevano il diametro dal profilo **disegnato**
> (`sorted` = `_segmentNodes`) invece che da quello **compensato** (`GetCompNodes()`) — sembravano "non
> aggiornarsi" perché mostravano sempre il valore pre-rimodellamento. Il PDF/CLI (`ChartRenderer.cs`)
> non aveva questo problema, perché lì la variabile equivalente era già impostata al profilo giusto.
> Corretto in `RenderSegmentOverlay` (`Views/MainWindow.xaml.cs`): tutte le posizioni delle etichette
> in modalità compensata ora interpolano da `GetCompNodes()`.
>
> **Bug correlato corretto lo stesso giorno**: nella griglia Nozzles, premere Invio su una cella
> densità senza averla modificata faceva comunque comparire il dialogo "Adjust diameters?" e rilanciava
> il ricalcolo zona — comportamento standard del `DataGrid` WPF, che spara `CellEditEnding` con
> `EditAction.Commit` ogni volta che una cella esce dalla modifica, anche senza modifiche reali.
> Verificato con un log temporaneo (poi rimosso) che il calcolo stesso è corretto su un intero ciclo
> su/giù di densità (nessun accumulo, direzione sempre giusta) — il problema era solo il trigger
> spurio. Corretto in `NozzleDefsGrid_BeginningEdit`/`NozzleDefsGrid_CellEditEnding`
> (`Views/MainWindow.xaml.cs`): il valore viene confrontato prima/dopo l'edit, il dialogo/ricalcolo
> scatta solo se la densità è davvero cambiata.
>
> **Regressione e secondo fix, stesso giorno**: il primo tentativo confrontava il valore digitato
> leggendo `NozzleDefinitionVm.DensityGCm3` (il binding della griglia) dentro un `Dispatcher.InvokeAsync`
> — ma il commit del binding gira a priorità più bassa di `Normal`, quindi anche lì il valore letto era
> ancora quello *vecchio*: il confronto risultava sempre "non cambiato" e il dialogo non compariva più
> **mai**, nemmeno per un cambio vero. Il codice originale funzionava per puro caso: leggeva la densità
> solo *dopo* il dialogo modale di conferma, che pompando il proprio message loop dava al binding il
> tempo di arrivare. Corretto leggendo il testo digitato direttamente dalla `TextBox` di modifica
> (`e.EditingElement`) invece di aspettare il binding, con parsing a doppio tentativo (cultura corrente,
> poi invariante) per non confondersi tra punto e virgola decimale.
>
> **Terzo fix, stesso giorno — il diametro mostrato era sempre quello del passo precedente**: dopo i
> due fix sopra, cambiare densità mostrava un diametro coerente ma sfasato di un passo (a 1.10 il
> diametro mostrato era quello corretto per 1.05, a 1.15 quello di 1.10, ecc. — confermato passo per
> passo confrontando i valori riportati con quelli attesi dalla formula). Causa: `NozzleDefsGrid_CellEditEnding`
> chiamava `RefreshPlot()` **prima** di aprire il dialogo "Adjust diameters?", disegnando un frame con
> la compensazione ancora *vecchia* — chi guarda tabella/grafico mentre il dialogo è aperto (prima di
> cliccare Yes) vede quel frame stantio; il valore giusto arriva solo dopo, quando `ApplyZoneDensities`
> (chiamata dopo il click su Yes) fa il proprio `RefreshPlot()` con i dati nuovi. Corretto saltando il
> refresh intermedio quando sta per scattare un ricalcolo di zona: `ApplyZoneDensities` fa l'unico
> refresh, e lo fa con i dati già corretti.
>
> **Quarto fix, stesso giorno — vera race condition col binding della griglia**: rimuovendo il refresh
> del terzo fix è sparito anche il tempo "morto" che per caso lasciava al binding della griglia (una
> `TwoWay` che si aggiorna a priorità più bassa di `Normal`) il tempo di scrivere il valore digitato
> in `Nozzles[i].DensityGCm3` — così `ApplyZoneDensities`, chiamata subito dopo, tornava a leggere la
> densità **vecchia** anche dopo aver risposto Yes al dialogo (confermato dal log: `ApplyZoneDensities`
> vedeva ancora 1.1 anche dopo aver cambiato a 1.2). Non è un problema di ordine tra due `RefreshPlot()`
> ma una vera corsa critica sul timing del binding, sensibile a quanto lavoro sincrono capita di
> esserci prima della lettura. Fix definitivo: `NozzleDefsGrid_CellEditEnding` non aspetta più il
> binding della griglia per niente — scrive lei stessa il valore digitato (già letto dalla `TextBox`
> per il confronto "è cambiato?") dentro `editedNozzle.DensityGCm3`, sincrono, prima di qualunque cosa
> a valle legga quella proprietà. Il binding della griglia arriverà comunque più tardi e scriverà lo
> stesso valore, in modo innocuo.

---

## 6. Materiale e Fisica dell'Acqua

### Impostare la Densità

**Metodo 1 — Dalla pesatura:**
1. Pulsante **From Weight** → dialog
2. Scegliere scope: Intera linea / Solo testa / Segmenti personalizzati
3. Inserire il peso misurato in grammi (accetta `.` o `,` come decimale)
4. Densità calcolata mostrata in anteprima
5. OK per applicare

**Metodo 2 — Dalla velocità target:**
1. Pulsante **From Sink Speed** → dialog
2. Inserire la velocità target in in/s (es. `1.5`)
3. Il calcolo inverso determina la densità richiesta
4. Warning se superiore a 2.5 g/cm³ (limite pratico del tungsteno)
5. OK per applicare

**Metodo diretto:**
- Campo **Density (g/cm³)** nella sezione Sinking Tools → inserire il valore e premere Enter

### Parametri Acqua
- **Water type**: Fresh / Salt
- **Temperature**: 0–40 °C
- Modificare questi parametri ricalcola automaticamente tutte le velocità

### Floating / Neutral / Sinking

Tre tipi, non più due. Il selettore in testa al pannello Design Project ha ora anche **Neutral**.

**Il neutro non è un terzo stato fisico.** Sotto la densità dell'acqua una linea galleggia, sopra
affonda: non c'è altro. "Neutral" è una **banda di affondamento molto lento**, abbastanza lenta da
pescare come se la linea restasse sospesa. Dove finisce quella banda è una convenzione di prodotto,
non un confine misurato, e per questo sta in una sola costante con un nome:
`SinkingSpeedCalc.NeutralMaxIns`.

| | condizione |
|---|---|
| **Floating** | non affonda (densità ≤ quella dell'acqua) |
| **Neutral** | affonda, ma sotto **0.15 in/s** |
| **Sinking** | affonda più veloce |

0.15 in/s è circa un centimetro ogni due secondi e mezzo. La soglia è tarata sull'archivio: la linea
più lenta che hai davvero progettato come sinking esce a **0.23 in/s** (`ST27 - 65`, ρ 1.006), quindi
la banda neutra le sta sotto senza toccarla. In archivio c'è anche un buco coerente: le floating
arrivano a ρ 0.972, le sinking partono da 1.006 — il neutro sta esattamente nel mezzo.

- Il tipo **si aggiorna automaticamente in base alla fisica** appena una densità è impostata, come
  faceva il flag a due stati. **Decide la sezione più veloce**: una linea con un tratto affondante
  non è una linea floating
- Per linee floating gli strumenti di compensazione restano nascosti; per le **neutre no** — una
  neutra è ingegnerizzata in densità, è semmai il caso in cui servono di più

### Tipo per sezione

La tabella segmenti ha una colonna **Type** accanto a Sink, con il tipo di *quella* sezione, ricavato
dalla velocità già calcolata per essa. Su un taper decide l'estremo più veloce, quindi una sezione è
"Floating" solo se non affonda in nessun punto.

Serve perché **un sink tip è esattamente una linea le cui sezioni non concordano** — la cosa che un
tipo unico per tutta la linea non può dire. Il selettore in alto resta la sintesi (e per un sink tip
dirà "Sinking", perché la punta affonda); la colonna mostra com'è fatta davvero.

### Reset Posizione

Il pulsante **Reset Posizione** (toolbar strumenti) azzera la lunghezza a 0 **senza toccare i dati
della scansione** — manda `resetpos` al dispositivo. È diverso da **Clear Chart**, che azzera la
posizione *e* cancella tutto.

**Premilo subito prima di ogni corsa misurata.** La posizione è il riferimento a cui la corsa viene
rapportata: partendo da una posizione rimasta da prima la misura risulta corta esattamente di
quell'avanzo, e niente a schermo lo segnala. Un caso reale: una corsa di 100 cm letta 98 solo per
questo, mentre lo stesso banco su 1000 cm ha letto 1000 esatti.

Verifica a vista: **se la lunghezza viva non legge 0 prima di partire, premi Reset Posizione.**

### PPC — impulsi per centimetro

La card **PPC (impulsi/cm)** nella riga delle metriche mostra il valore che il dispositivo sta
**realmente** usando per convertire gli impulsi dell'encoder in centimetri, e da dove viene:

- **formula** (grigio) — ricavato da `ENCODER_PPR` e `WHEEL_CIRC_MM` nel firmware
- **calibrato** (arancio) — valore scritto in EEPROM con `calibrate:<cm>` o `Imposta PPC`, che
  sopravvive al riavvio e **sostituisce** quello di formula

È in evidenza quando è calibrato perché quel numero **scala tutte le lunghezze registrate**: una
calibrazione vecchia o fatta in condizioni diverse sposta ogni misura, e prima non c'era nulla a
schermo che lo dicesse. Il dato arrivava già via WebSocket ma veniva scartato.

> Se una scansione risulta lunga o corta di qualche percento, questa card è il primo posto da
> guardare. Da lì si risale alla pagina web dell'ESP32, dove il valore si azzera (`Ripristina
> formula`) o si ritara.

### Core (anima)

Il selettore **Core** nel pannello materiali elenca i core realmente a magazzino, con materiale,
carico di rottura e la gamma di diametro del fornitore:

| Materiale | lb | Ø |
|---|---|---|
| Polyester | 12 | 0.55–0.60 |
| Polyester | 17 | 0.65–0.72 |
| Polyester | 20 | 0.82–0.87 |
| Polyester | 25 | 0.90–0.95 |
| Polyester | 30 | 1.00–1.05 |
| Polyester | 35 | 1.15 |
| Kevlar | 60 | ≥ 0.90 |
| Kevlar | 80 | ≥ 0.90 |

- Il fornitore dà una **gamma**, non un valore. Scegliendo una voce il campo **Ø** si riempie col
  **punto medio**; la gamma resta scritta accanto, così la tolleranza non sparisce dietro un numero
  solo. Il Ø è sovrascrivibile a mano per usare un altro punto della gamma
- Restano in lista anche le vecchie descrizioni generiche ("Braided multifilament nylon"…): non
  hanno diametro, quindi un progetto che ne usa una si apre e si stampa come prima, semplicemente
  non disegna il core
- Il Kevlar è quotato solo come "sopra 0.90" per entrambi i carichi: il Ø registrato è quel **minimo**,
  non una misura. Da sostituire con i valori veri prima di fidarsi di un core Kevlar disegnato in scala

La spunta **Show** accanto al Ø è **un solo interruttore per entrambi i posti** in cui il core
compare, così non capita mai che sia disegnato nel grafico e assente dal foglio (o viceversa).
Spenta: niente banda nel grafico e **nessuna card Core nel PDF**, né tipo né diametro.

**Nel grafico** (solo in Design Mode) il core è disegnato dentro il rivestimento **alla sua
dimensione vera**, come banda a diametro costante nello stesso sistema ±d/2 del profilo. Dove il
core è più grosso del rivestimento **la banda esce dal profilo**: non è un difetto del disegno, è
il progetto che dice che lì non si può costruire — per questo non viene tagliata via.

**Nel PDF** il core non è disegnato: compaiono la voce scelta e il Ø usato nella card Core.

Nel `.flp`: `CoreType` (come prima) più **`CoreDiameterMm`** e **`ShowCore`**. Un file più vecchio del catalogo non ha
il diametro e lo recupera dalla voce che il suo `CoreType` nomina, se ne nomina una.

> Il Ø del core **non entra ancora nel calcolo della massa**. `MassLinearCalculator` sa già
> modellare anima + rivestimento, ma gli serve anche la **densità** del core, che il fornitore non
> ha dato — e la densità di una treccia non è quella del materiale pieno, perché la treccia ha aria
> dentro. Finché manca quel numero il calcolo resta a sezione piena, come prima.

### Full Line vs Shooting Head
- **Full Line**: attiva la colonna "Head" nella tabella segmenti
- Il CoM e i calcoli AFFTA usano solo i segmenti testa quando attivo

### Mappa Velocità Affondamento
- **Sink Map** toggle → sovrappone una heatmap colorata al profilo
- Colore = velocità locale relativa (blu=lento → rosso=veloce)

---

## 7. Compensazione del Profilo (NC → C)

La compensazione risolve il problema fisico: sezioni di diametri diversi affondano a velocità diverse. Il profilo Compensato (C) modifica i diametri affinché ogni sezione affondi alla stessa velocità target.

**Non esiste una "vista C" nella finestra di lavoro.** Compensare non trasforma il progetto aperto: calcola il profilo e lo **scrive subito in un file separato**, esattamente come fanno i generatori di famiglia. Il design NC aperto resta identico a prima (nemmeno il flag di modifica cambia). I toggle "Show C" / "Show NC" e lo slider Target in toolbar non esistono più.

### Workflow
1. Impostare la densità del materiale (sezione 6)
2. Verificare che la linea sia classificata come "Sinking"
3. **Salvare il progetto** — il file C prende il nome da quello del progetto
4. Cliccare **⚖ Compensate…**
5. Nel dialogo, scegliere la velocità target con lo slider (min/max mostrati come numeri ai lati) e premere **Create C file**
6. Conferma con il nome del file scritto; per vedere o stampare il profilo compensato si apre quel file

### Dialogo Compensate
- Il range dello slider è la velocità di affondamento più lenta e più veloce già raggiunta dalle sezioni attuali: qualsiasi target al suo interno è ottenibile cambiando solo la densità
- Il nome del file che verrà scritto è mostrato dal vivo mentre si muove lo slider: `NomeProgetto C X.XXins.flp`
- Se il file esiste già viene chiesta conferma di sovrascrittura
- Se il design ha **zone con materiale proprio** (sezione 5), il dialogo avvisa prima: la compensazione fisica risolve tutta la linea a partire dal materiale base M1 e dai diametri disegnati, quindi i materiali di zona **non** finiscono nel file C

### Compensazione vincolata a 4 materiali reali (non un continuo teorico)
La soluzione fisica pura vorrebbe una densità diversa a ogni centimetro — impossibile da
realizzare (nessun produttore ha un numero illimitato di ugelli). Il calcolo procede in due passi:
1. **Soluzione ideale continua**: densità e diametro risolti insieme, slice per slice (~1cm),
   per centrare esattamente la velocità target ovunque — è solo un passaggio interno, non quello
   che finisce nel file
2. **Vincolo ai materiali reali**: le densità ideali vengono raggruppate in **sempre fino a 4
   materiali reali** (mai meno per "semplicità" — i 4 ugelli sono comunque disponibili, usarne di
   meno peggiora solo la precisione). Ogni slice prende il materiale più vicino tra i 4, mentre il
   **diametro resta esattamente quello della soluzione continua ideale**: non viene mai ritoccato
   in funzione del materiale assegnato

Il diametro non viene corretto perché qualsiasi correzione legata al materiale (anche quella a
massa costante ρ·d² = cost. usata per le zone, §5) **salta** dove salta l'assegnazione del
materiale: la densità ideale è continua, ma il materiale più vicino cambia di colpo, e il diametro
con lui — producendo un gradino visibile proprio dove due materiali si incontrano. Lasciando il
diametro intatto il taper resta continuo ovunque, confine tra materiali compreso.

Risultato: **forma del taper perfettamente liscia**, e la velocità di affondamento diventa
un'**approssimazione** del target invece che un valore esatto ovunque — assorbe interamente
l'errore di discretizzazione. Lo scostamento peggiore viene mostrato nel messaggio di conferma
dopo il salvataggio. È il compromesso scelto deliberatamente: si accetta uno scarto di velocità
maggiore pur di non avere mai un salto di diametro.

### Ugelli nel file C
- M1–M4 del file C vengono popolati con le densità reali usate — sempre fino a 4, non un
  sottoinsieme "sufficiente"
- Colore corrispondente al gradiente densità; label `ρ X.XX`
- Gli ugelli del progetto NC aperto non vengono toccati: colori, label e densità tornano esattamente com'erano

### C e NC sono due file distinti
- Il file C ha la **propria geometria indipendente**, salvata alla **piena risoluzione di calcolo**
  (un nodo ogni ~1cm), ciascun nodo con la propria densità reale in `SegmentMetadata` — non la
  geometria NC con una "ricetta" da rieseguire. Riaprirlo non richiede il file NC di origine né
  alcun ricalcolo. La geometria salvata è esattamente quella calcolata: non viene mai semplificata
  o raggruppata prima di scriverla su disco
- Il **raggruppamento è solo una questione di visualizzazione**: la tabella Segments e il PDF
  mostrano una riga per zona di materiale (slice consecutive con la stessa densità reale unite in
  un'unica riga), quindi restano leggibili come una tabella NC normale invece di elencare centinaia
  di righe da 1cm. Il grafico, i totali e ogni calcolo continuano a leggere i dati completi
- Il file NC salva solo il proprio profilo, a densità unica (più le eventuali zone a materiale
  proprio) — resta sempre "puro" e ricompensabile. Salvare l'NC **non** genera più alcun file C
- Il file compensato è **bloccato** (`IsCompensatedDerivative`): il pulsante "⚖ Compensate…", i
  controlli densità e la cella densità di M1 sono disabilitati. Per cambiare la compensazione si
  torna al file NC originale e si ricompensa da lì

---

## 8. Grafico Analisi Massa

Visibile solo in Design Mode, sotto il grafico principale.

| Elemento | Significato |
|---|---|
| Barre **rosse** | Segmenti della testa |
| Barre **blu** | Segmenti di running line |
| **◆ diamante** | Centro di massa del singolo segmento |
| **Linea tratteggiata colorata** | Centro di massa totale (colore = taper character) |
| **Linea gialla tratteggiata** | Limite 30 ft AFFTA (914.4 cm) |
| **Curva verde** | Peso cumulativo scalato sull'asse |

---

## 9. Badge AFFTA

Mostrato nella status bar in basso a destra:

```
AFFTA  LW 5   142.3 gr   ✓
```

- **LW**: Line Weight AFFTA (1–14)
- **X.X gr**: peso dei primi 30 ft (914.4 cm) in grains
- **✓/✗**: entro ±6 gr dalla classe nominale
- Se è attiva una zona con densità propria (sezione 5), il peso tiene conto della vera densità di quella zona invece di assumere materiale uniforme su tutta la linea — stesso calcolo usato dalla generazione famiglia (sezioni 10-11)

---

## 10. Generazione Famiglia Pesi Linea (#1–#14)

Dato un profilo disegnato (o ricostruito da scan), è possibile generare automaticamente le varianti dello stesso profilo per le altre classi AFTMA (#1–#14), mantenendo la stessa forma di taper e lo stesso materiale.

### Come funziona
- Il pulsante **Generate Family…** (toolbar Design Tools) apre un dialogo con una checkbox per ciascuna classe #1–#14; la classe corrente del progetto è disabilitata
- Per ogni classe selezionata, **tutti** i diametri della linea (testa, transizione e running line) vengono scalati con lo stesso fattore, a parità di lunghezza — è quello che preserva la "forma" del profilo, running line inclusa
- Il fattore di scala si ricava in forma chiusa (la massa nei primi 30 ft scala esattamente come il quadrato del fattore, a parità di lunghezze), quindi **ogni classe è sempre raggiungibile**, per costruzione
- Nessuna posizione cambia (le lunghezze dei segmenti restano identiche), quindi zone ugello e laser mark non hanno bisogno di essere riposizionati
- La densità (materiale) non viene mai toccata — resta identica in ogni classe generata, zona a densità propria compresa (se presente, viene correttamente pesata invece di essere ignorata)

### File generati
Ogni classe selezionata produce un nuovo file `NomeProgetto #N.flp` accanto al progetto originale (che deve essere già stato salvato in precedenza). Il progetto originale non viene mai modificato.

---

## 11. Generazione Famiglia per Velocità di Affondamento

L'opposto della generazione per peso linea (§10): stessa geometria (stesso taper, stessa classe AFFTA), densità uniforme diversa per ogni velocità di affondamento target.

### Come funziona
- Il pulsante **Generate by Sink Speed…** (toolbar Design Tools) apre un dialogo con uno slider da **Floating** a **10.0 in/s**
- Si trascina lo slider sulla velocità desiderata e si preme **+ Add to list**; si ripete per ogni variante voluta, poi **Generate**
- Per ogni velocità, densità (uniforme) e diametro (fattore di scala uniforme su tutta la linea) vengono risolti **insieme**: la densità si ricava con lo stesso metodo del pulsante "⏬ From sink speed…" (`SinkingSpeedCalc.DensityForTargetSinkSpeed`), il diametro si scala per compensarla in modo che la **massa nei primi 30 ft resti identica a quella della linea sorgente** — nessuna compensazione per-slice, ma nemmeno densità libera di far variare il peso
- Risultato: tutte le varianti generate restano nella **stessa classe AFFTA** della sorgente, esattamente come nelle linee reali in famiglia (es. WF6F / WF6I / WF6S3 / WF6S5 sono tutte "WF6"). Per andare più veloci a parità di peso, il diametro si riduce (materiale più denso, meno volume); per la variante Floating (densità fissata a `RhoFloor` = 0.94 g/cm³, che galleggia), il diametro invece aumenta
- Se una velocità richiesta supera quella raggiungibile a ρ = 2.5 g/cm³ (limite pratico) a parità di massa, il file viene generato comunque alla densità limite e segnalato nel riepilogo come "non esattamente raggiungibile"

### File generati
Ogni velocità produce un file `NomeProgetto X.XXips.flp` (o `NomeProgetto Floating.flp` per lo 0) accanto al progetto originale (che deve essere già stato salvato).

---

## 11b. Generazione Famiglia per Densità

Lo specchio della §11: lì la **velocità** è l'ingresso e la densità viene risolta; qui le **densità sono l'ingresso** — i materiali che hai davvero in magazzino — e la velocità di affondamento è il risultato.

### Come funziona
- Il pulsante **Generate by Density…** (toolbar Design Tools) apre un dialogo con uno slider da **0.94** a **2.50 g/cm³**
- **+ Add to list** aggiunge la densità corrente; **+ Add my M1–M4** aggiunge in un colpo le densità degli ugelli già definiti nel progetto
- Si sceglie **cosa resta fisso**:
  - **la classe di peso** (default) — tutti i diametri vengono riscalati di `√(ρ_vecchia/ρ_nuova)` perché la massa dei primi 30 ft resti identica. Materiale più denso ⇒ linea più sottile, stesso peso. È la logica di famiglia: una WF6 resta WF6
  - **i diametri disegnati** — cambia solo il materiale, e massa e classe si muovono con la densità. È la domanda da banco: «e se estrudessi questo stesso profilo nel materiale più denso?»
- Per ogni variante la **velocità di affondamento viene calcolata** sulla geometria che ne esce, come **corpo rigido unico** (`RigidBodySinkSpeed`, campionando ogni segmento a 1 cm) — non fetta per fetta isolata, perché le sezioni di una linea vera sono unite e condividono una sola velocità di equilibrio
- Una densità ≤ 1.00 g/cm³ galleggia a qualsiasi diametro: il dialogo lo dice già mentre trascini lo slider

### File generati
Ogni densità produce `NomeProgetto 1.10gcm3 0.45ips.flp` — densità e velocità raggiunta sono entrambe nel nome, accanto al progetto originale (che deve essere già salvato).

---

## 11c. Cambiare la densità e vedere i diametri

Fuori dalla generazione famiglia, la stessa matematica è disponibile **dal vivo** mentre progetti.

Digitando una nuova densità nella casella **ρ g/cm³** (pannello materiale), l'app chiede se adattare i diametri per conservare la massa. Rispondendo sì, **ogni diametro viene moltiplicato per `√(ρ_vecchia/ρ_nuova)`** — la stessa costante per tutti, quindi la massa è conservata in **ogni punto**, non solo in media.

La barra di stato riporta la conseguenza:

```
ρ 0.96 → 1.10 g/cm³ · diameters ×0.9342 · mass held · sink 0.32 ips → 0.45 ips
```

Differenze dalle zone ugello (§5):
- una zona è un **overlay vivo**, ricalcolato a ogni caricamento, che non tocca mai i `DesignNodes`; questo invece **scrive nei nodi**, perché *è* il disegno. Per questo c'è l'undo e per questo viene chiesto
- non è reversibile ridigitando il numero vecchio: la riscalatura si applicherebbe una seconda volta. Usa **Ctrl+Z**
- la scelta è **sticky**: la risposta viene proposta come default alla modifica successiva

> I pulsanti **⚖ From weight…** e **⏬ From sink speed…** non innescano la riscalatura: lì la densità viene risolta *a partire da* un obiettivo, e riscalare i diametri sotto combatterebbe proprio ciò che si è appena risolto.

---

## 12. Confronto e Overlay

### Importare una Serie di Confronto
- **Import CSV** → selezionare file (2 colonne cm/mm, o formato Dataset)
- La serie appare sul grafico in colore diverso

### Overlay di un Progetto Esterno
- **Overlay Project** → selezionare un file `.flp`
- Se il progetto contiene sia design nodes sia scan points, viene chiesto quale/i importare: **Design profile only**, **Scan profile only** o **Both profiles**
- Se il progetto ha solo uno dei due tipi di dati, viene importato direttamente senza chiedere
- Le serie importate appaiono in legenda

### Gestire le Overlay
- **Clear Overlays** → rimuove tutte le serie importate (con conferma se più di una)
- In Design Mode le overlay restano visibili anche quando il layer scan è nascosto

### Show/Hide Scan
- **Show Scan / Hide Scan** → alterna la visibilità del layer scan
- In Design Mode il scan è nascosto di default

---

## 13. Prototipo da Pezzi Scansionati

Finestra separata (**🧩 Prototype…** nella toolbar) per costruire un prototipo di linea usando solo
pezzi reali già scansionati: si prendono dalla libreria, si sovrappongono sul grafico per confrontare
i diametri, si tagliano a una o entrambe le estremità e si ruotano di 180°. **Dove tagliare lo decide
l'utente** — la finestra mostra solo i diametri e segnala come combaciano le giunzioni. Non è una
progettazione: i diametri dei pezzi non si modificano mai, si tagliano e si posizionano soltanto.

### Libreria pezzi
- Pannello a sinistra: tutti i `.flp` con una scansione nella cartella libreria **e nelle sottocartelle**
  (i derivati C e i file senza scan sono esclusi). Ogni pezzo mostra sagoma, lunghezza, Ø min–max e ρ
  se il progetto sorgente ne ha una.
- La cartella si imposta in **Settings → Prototipi** oppure con **Folder…** nella finestra stessa.
  Vuota = cartella progetti predefinita (`Documenti\FlyLineProfiler\Projects`). **↻** la rilegge.
- Casella sopra la lista: filtro per nome o sottocartella.
- **Doppio clic** o **Add to prototype →**: il pezzo viene aggiunto subito dopo l'ultimo sul grafico.
- Pulizia automatica minima della scansione: si scartano solo le letture "senza linea" (< 0.10 mm) e le
  X ripetute (mediate). Loop saldati, picchi e punte sfilacciate alle estremità **restano** — si tagliano.

### Sul grafico
- Ogni pezzo è una banda colorata (solo la parte tenuta).
- **Original shape** (toggle nella toolbar, attivo di default): mostra per **ogni** pezzo la sua forma
  originale intera come contorno tratteggiato, nello stesso colore e orientamento — si vede cosa è stato
  tagliato (e lo si recupera trascinando la maniglia indietro) e, per una parte di uno split, l'intero
  pezzo da cui proviene. Disattivandolo restano solo le parti tenute.
- L'asse Y riporta il **diametro** (la sagoma è disegnata simmetrica ±raggio).
- **Trascinare il corpo** di un pezzo → lo sposta orizzontalmente (il diametro non cambia mai).
  Vicino all'estremità di un altro pezzo si aggancia testa-a-testa; **Shift** disattiva l'aggancio.
- **Trascinare una maniglia** (barra verticale alle estremità) → taglia quell'estremità, al cm.
- **Passando col mouse**, la barra di stato mostra il Ø di ogni pezzo sotto il cursore e, se sono due,
  la differenza Δ: serve a trovare il punto in cui i diametri coincidono.
- **Tasto destro:**
  - in una zona dove due pezzi si sovrappongono → **✂ Cut both here**: taglia la coda del pezzo di
    sinistra e la testa di quello di destra esattamente in quel punto (i due pezzi si toccano lì);
  - su un pezzo → **✂ Split here into two parts**, **✂ Cut here, keep the left/right part**, **🎨 Color**,
    **⇄ Flip 180°**, **Reset cuts**, **Remove piece**.

### Colore dei pezzi
Ogni pezzo — e ogni parte dopo uno split, anche se viene dallo stesso pezzo — ha il suo colore.
- **Tasto destro sul pezzo → 🎨 Color**: 13 colori (blu, rosso, verde, ambra, viola, ciano, rosa, marrone,
  giallo, arancio, bianco, grigio, nero) oppure **Custom…** (selettore colori di Windows).
- Oppure **clic sul quadratino colore** nella tabella pezzi: stesso menu.
- Per i colori chiari (bianco, giallo) contorno, maniglie ed etichetta vengono scuriti per restare
  leggibili sul grafico; il riempimento resta del colore scelto.
- Il colore si salva nel `.flproto` ed è annullabile con Ctrl+Z.
- Zona gialla tratteggiata = i pezzi si sovrappongono ancora (non ancora tagliati).
- Etichetta di giunzione `Ø sinistra|destra` e `Δ`: verde ≤ 0.03 mm, arancio ≤ 0.08 mm, rosso oltre.
  Se tra due pezzi c'è spazio sul grafico viene indicato `gap`: nella linea finita i pezzi sono comunque
  uniti testa-a-testa.

### Split — dividere un pezzo in più parti
Un pezzo si può dividere in 2 o più parti, ognuna poi indipendente (si sposta, si taglia e si capovolge
da sola) — per esempio per usare due tratti dello stesso cilindro in punti diversi del prototipo.
- **Tasto destro → ✂ Split here** oppure tasto **S** con il mouse sul punto: divide nel punto del cursore.
  Ripetendo si ottengono 3, 4… parti.
- **✂ Split…** nella toolbar: divide il pezzo selezionato in 2, 3, 4 o 5 parti uguali.
- Dopo lo split le parti restano a contatto (giunzione Δ 0.00): trascinarle per separarle.
- Le parti sono numerate **#1, #2, …** lungo il pezzo fisico partendo dall'estremità di inizio scansione,
  qualunque sia l'ordine in cui sono state divise. Nella lista di taglio ogni parte indica il tratto del
  pezzo originale, es. `(= 429–758 cm of Rossa)`.
- Se due parti dello stesso pezzo usano lo stesso tratto (es. dopo *Reset cuts* su una parte) compare
  l'avviso *"… both use x–y cm of the same scan"*: fisicamente non è possibile.
- Con **Original shape** attivo ogni parte mostra tratteggiato l'intero pezzo originale da cui proviene.

### Flip 180°
Capovolge il pezzo mantenendo la sua posizione sul grafico: cambia solo quale estremità sta a sinistra.
I tagli restano riferiti alle estremità fisiche del pezzo (vedi sotto).

### Giunzioni: 4 cm per estremità (splice con ago)
Per unire due pezzi si scopre l'anima togliendo il rivestimento e si esegue la giunzione con l'ago: ogni
pezzo deve avere **almeno 4 cm in più ad ogni estremità che si unisce** a un altro pezzo. Questo tratto
è nel pezzo tagliato ma **non** nella linea finita.
- Il valore si imposta nella toolbar: **Splice [4] cm / end** (salvato nel `.flproto`, default 4 cm).
- Il grafico mostra sempre la linea **finita** (giunzione = punto di contatto dei due pezzi).
- La **lista di taglio** invece dà i tagli **al banco**: ad ogni estremità unita si taglia 4 cm più
  all'esterno, quindi il pezzo tagliato è più lungo, es. `piece 502 cm = 498 in line + 4 splice`.
- Le due estremità libere della linea (punta e coda) non ricevono il margine.
- Avvisi:
  - *"only X cm of line beyond the joint … the splice needs 4 cm"* → il pezzo non ha abbastanza linea
    oltre il punto di giunzione (es. estremità non tagliata o tagliata a meno di 4 cm): spostare il punto
    di giunzione verso l'interno del pezzo;
  - *"X cm of line between them, their two splices need 8 cm"* → due parti dello stesso pezzo (split)
    hanno troppo poca linea tra loro per i rispettivi margini. Subito dopo uno split le parti si toccano
    (0 cm): accorciarle di almeno 4 cm ciascuna sul lato del taglio.

### Tabella pezzi e lista di taglio
- Ordine = ordine sul grafico (da sinistra). Colonne: direzione, lunghezza intera, **Trim scan-start** /
  **Trim scan-end** (tagli sul grafico, editabili, cm), **In line** (lunghezza nella linea finita),
  **Cut length** (lunghezza del pezzo tagliato al banco, margini splice inclusi), Ø alle due estremità
  tenute, **ρ** (editabile) e massa.
- I tagli sono sempre espressi rispetto alle **estremità della scansione** del pezzo: *scan-start* =
  l'estremità entrata per prima nel sensore (X = 0 nel file sorgente), *scan-end* = l'altra. Così la
  lista si legge uguale al banco qualunque sia l'orientamento nel prototipo.
- **CUT LIST** — il foglio per il banco, nell'ordine in cui si lavora:
  1. **CUTTING** — un blocco per ogni pezzo fisico (le parti di uno split stanno sotto il loro pezzo).
     Ogni riga è un tratto misurato **dall'estremità marcata** (quella entrata per prima nello scanner):
     `da – a – lunghezza` e la destinazione — `discard` (scarto) oppure `→ position N` nella linea, con
     `(in linea + splice)`. I margini splice sono già inclusi. Problemi (parti che si sovrappongono,
     linea insufficiente per lo splice) compaiono con ⚠ subito sotto la riga interessata.
  2. **ASSEMBLY** — dalla punta alla coda: posizione, pezzo, lunghezza nella linea, Ø lato punta → lato
     coda e **da che parte va l'estremità marcata** (`at tip` / `at back`). Tra un pezzo e l'altro la riga
     `↓ splice` con i due Ø e il gradino (⚠ oltre 0.03 mm, *big step* oltre 0.08 mm).
  3. **FINISHED LINE** — lunghezza, numero di pezzi e di splice, massa (se tutte le ρ sono note).
  la copia negli appunti.
- La massa totale compare solo se tutti i pezzi hanno una densità (ρ = 0 → "density missing").
  Nota: la massa è calcolata sul diametro scansionato — la verifica vera è la bilancia.

### Tasti
| Tasto | Azione |
|---|---|
| Ctrl+Z | Undo (anche Undo nella toolbar) |
| Canc | Rimuove il pezzo selezionato |
| F | Flip 180° del pezzo selezionato |
| S | Split del pezzo sotto il cursore, nel punto del cursore |

### Salvare ed esportare
- **Save / Save As…** → file `.flproto` (default `Documenti\FlyLineProfiler\Prototypes`). Contiene una
  copia di ogni scansione usata, quindi resta modificabile anche se il `.flp` sorgente viene spostato.
- **Close gaps** → fa scorrere i pezzi verso sinistra in modo che ognuno inizi dove finisce il precedente.
- **Export .flp…** → la linea finita come progetto normale: la sua *scansione* è il profilo assemblato
  (pezzi uniti testa-a-testa da X = 0; a ogni giunzione il salto di Ø è registrato con due punti alla
  stessa X). Le Notes contengono la lista di taglio. Se tutti i pezzi hanno la stessa ρ, diventa la
  densità del progetto.
- **Open in Profiler** → esporta e apre subito il risultato nella finestra principale (chiede prima di
  salvare il progetto aperto, se modificato).
- Se al momento dell'export ci sono ancora sovrapposizioni viene chiesta conferma: le parti sovrapposte
  finirebbero due volte nella linea.

### CLI
`flyline assemble <in.flproto> [-o <out.flp>]` stampa la lista di taglio e, con `-o`, scrive il `.flp`
assemblato. Un `.flproto` scritto a mano può omettere le scansioni: basta `SourcePath`, `Flipped`,
`TrimStartCm`, `TrimEndCm`, `OffsetCm` per pezzo.

---

## 14. Export

| Funzione | Formato | Come accedere |
|---|---|---|
| Export Scan CSV | `.csv` | Menu File → Export CSV |
| Export Design Segments | `.csv` | Menu File → Export Segments |
| Save Nodes | `.nodes.csv` | Menu File → Save Nodes |
| Load Nodes | `.nodes.csv/.csv` | Menu File → Load Nodes |
| Export Chart PNG | `.png` | Menu File → Export PNG |
| Export PDF | `.pdf` | Menu File → Export PDF |

### Export PDF — Contenuto
1. **Header**: nome progetto, data, tipo profilo (NC o C)
2. **Grafico profilo** (3200×600 px) con etichette nodi e segmenti
3. **Tabella segmenti** completa
4. **Card informazioni**: tipo core, laser mark, **Note**
5. **Nozzle swatches**: colori materiali con densità
6. **Badge AFFTA + CoM/Rg + classificazione taper**

### La casella Note

Era "Color note" ed era limitata al colore. Adesso è una **nota libera per il produttore** — colori, finitura, imballo, qualunque cosa valga la pena stampare sul foglio.

- La casella nel pannello materiali è più alta (il blocco che la contiene è passato da 160 a 210 px, e la casella ha `MinHeight` 90): ci stanno comodamente quattro o cinque righe
- **Gli a capo che digiti vengono mantenuti nel PDF**: ogni riga è emessa separatamente, non riflusso in un unico paragrafo
- Nel PDF la nota ha un **riquadro a tutta larghezza** tutto suo, sotto il laser mark (che a sua volta ha ora la propria riga). Prima i due si dividevano la stessa riga, stretto, il che andava bene per "rosso/bianco/verde" e non per una nota vera

> Nel file `.flp` la chiave resta **`ColorNote`**: rinominarla avrebbe reso illeggibile la nota di tutti i progetti già salvati e delle spec CLI esistenti. È solo il nome della chiave — il campo è a tutti gli effetti generico.

Non viene più chiesto se esportare NC o C: il PDF documenta **quello che il file aperto è davvero**. Un file C (o un design NC con zone a materiale proprio) esporta il profilo per-slice con densità reali; un design NC a materiale unico esporta il profilo disegnato. Il nome del file include automaticamente il suffisso `_NC` o `_C`.

---

## 15. Impostazioni

**Settings** (pulsante ingranaggio) → finestra modale.

### Backend (Connessione)

| Campo | Default | Descrizione |
|---|---|---|
| Profile Name | ESP32 Lab | Nome descrittivo del profilo |
| Host | 192.168.1.50 | IP dell'ESP32 |
| WebSocket Port | 81 | Porta WebSocket |
| HTTP Port | 80 | Porta HTTP |
| Auto-Connect | ON | Connette all'avvio |
| Reconnect (s) | 3 | Secondi tra tentativi automatici |
| Connect Timeout (s) | 5 | Timeout connessione iniziale |
| Load Params on Connect | ON | Legge `getparams` alla connessione |
| Load Motor Status on Connect | ON | Legge `motor status` alla connessione |

### Chart

| Campo | Default | Descrizione |
|---|---|---|
| Show Filtered Series | ON | Mostra curva filtrata (EMA) |
| Show Raw Series | OFF | Mostra curva raw |
| Auto Fit | ON | Adatta automaticamente gli assi |
| Smoothing Alpha | 0.10 | Fattore EMA |
| Line Width | 2 | Spessore linea scan |
| Filtered Opacity | 1.0 | Opacità serie filtrata |
| Raw Opacity | 0.65 | Opacità serie raw |

### Prototipi

| Campo | Default | Descrizione |
|---|---|---|
| Cartella libreria pezzi | (vuoto) | Cartella letta, con le sottocartelle, dalla finestra Prototype. Vuoto = `Documenti\FlyLineProfiler\Projects` |

---

## 16. Interazione con il Grafico

### Navigazione
- **Scroll mouse**: zoom in/out
- **Click e trascina** (fuori dai nodi): pan
- **Fit** button: riadatta la vista ai dati

### Hover Readout
Muovendo il mouse sul grafico, la status bar mostra:

```
S3  Design Ø 3.40 mm   |   Scan Ø 3.35 mm   |   Δ -1.5%   @   245.0 cm
```

Un'annotazione contestuale appare anche sul grafico (soppressa durante Draw mode).

### Drag Etichette
In Design Mode è possibile trascinare il box dell'etichetta di ogni nodo. La posizione viene salvata nel file `.flp`.

### Quote di Lunghezza
Sopra il profilo, ben distanziata dai tag "S{n}"/"M{n}" che restano attaccati al bordo, corre una catena continua di quote in stile disegno tecnico: un tick a 45° a ogni confine di taper fisico reale, una linea di quota fra due tick consecutivi e il numero (lunghezza in cm, senza unità di misura e senza zeri decimali inutili — es. "30" non "30.0") scritto orizzontale appena sopra la linea. Le quote seguono sempre e solo i tapers fisici reali (`GetTaperShapeBoundaries`), mai i cambi di materiale/colore — stesso principio delle etichette "S". Presente sia a schermo sia nel PDF esportato (stessa funzione condivisa `ChartGeometry.DrawLengthDimensionChain`).

Le etichette Ø/posizione dei nodi restano sotto il profilo — le due catene non si sovrappongono mai.

---

## 17. Shortcut Tastiera

| Shortcut | Azione |
|---|---|
| **Ctrl+Z** | Undo (solo Design Mode, non durante edit testo) |
| **Shift + Click** | Aggiungi nodo livellato (segmento cilindrico) |
| **Delete** su riga DataGrid | Elimina il nodo / la zona ugello selezionata |
| **Enter** | Conferma in dialoghi e field input |
| **Escape** | Chiude i popup colore |

---

## 18. Analisi fisica — Livello 2 (`flyline analyze`)

```
flyline analyze <in.flp> -a <accel m/s2>
                [--csv <out.csv>]
                [--tail-d <mm>] [--tail-rho <g/cm3>] [--tail-len <cm>]
                [--kind auto|shootinghead|fullline]
```

Calcola massa lineare m(s), massa cumulata M(s), Reynolds, drag normale e tangenziale, Π e
l'indice di continuità C, campionati ogni cm. Con `--csv` accoda le righe per segmento a
precisione piena (il testo a video arrotonda troppo per calibrare).

### Testa vs linea completa

Le due famiglie sono **strutturalmente diverse nel file** e non sono confrontabili fetta per fetta:

- **Linea completa** — la running line è dentro il profilo (in archivio: 960÷1475 cm di tratto
  costante finale a 0.75÷1.19 mm).
- **Shooting head** — il profilo si ferma alla coda della testa, e quello che segue è un
  **monofilo che nel file non c'è**.

L'analisi quindi appende alla testa la shooting line che traina, così le due famiglie vengono
valutate come lo stesso tipo di oggetto. Il default è il riferimento di Stefano: **0.40 mm nylon
(ρ 1.14), 40 m**.

La shooting line **non è salvata nel `.flp`**: descrive come la linea viene pescata, non la linea.
È un parametro di analisi con default globale, sovrascrivibile con `--tail-*`.

Il riconoscimento è automatico dal tratto costante finale (soglia 300 cm: in archivio le linee
complete ne hanno ≥ 960, le teste ≤ 30, quindi il margine è ampio). `--kind` forza la scelta.

### ρ·d — il "taper inerziale"

Nel range reale (d 0.4÷2.0 mm, v 15÷35 m/s) la parte di drag dipendente da Re vale solo il 2÷11%
del totale, quindi

```
Π ≈ 1.31 · ρ[g/cm³] · d[mm] · a / v²     (entro ~5%)
```

Tre conseguenze pratiche:

1. **Diametro e densità si scambiano 1:1.** −10% di diametro con +10% di densità lascia il
   carattere balistico invariato.
2. **Velocità e accelerazione sono solo fattori di scala**: spostano il *livello* di Π, non la sua
   *forma* lungo s. Siccome castabilità e turnover dipendono dalla forma, `ρ·d` porta
   l'informazione di progetto senza bisogno di indovinare né v né a.
3. Resta una correzione del second'ordine: a parità di ρ·d un tratto sottile-e-denso è ~3% peggio
   di uno grosso-e-leggero (più drag per unità di massa). Non si può assottigliare all'infinito
   compensando in densità.

### Lo scalino alla giunzione

Per una testa viene riportato il salto di ρ·d fra coda della testa e shooting line. Non è un
difetto — è il prezzo della shooting head — ma la sua **entità** conta, ed è controllata dal back
taper. La leva di progetto è quella.

Valori misurati sulle 30 teste in archivio: **da 1.32× a 2.66×, mediana 2.08×**. Le copie della
SA MED stanno a 1.47÷1.65×, le ST Rossa / Rosa ST27 a 2.33÷2.66×.

Con un mono nylon fisso il ranking dello scalino coincide con quello del ρ·d di coda; la metrica
diventa indipendente quando la densità varia (linee compensate, sink tip) o cambia la shooting
line. Esempio: **fluorocarbon 0.40 mm** (`--tail-rho 1.78`) ha ρ·d = 0.712, quasi identico a una
running line coated 0.75 mm (0.701) — porta lo scalino di `ST27 - 60` da 2.11× a 1.35×, al costo
di 3.2 g di traino in più.

### Metriche di forma su ρ·d

Calcolate sul **design** (la scansione è solo traccia di riferimento, non entra nella valutazione).
Tutte adimensionali e indipendenti da v e a.

| Metrica | Cosa dice | Range in archivio (52 linee) |
|---|---|---|
| **front backup** | quanto ρ·d *risale* andando verso la punta, in frazione della discesa picco→punta. 0 = scende monotono | 0 su 49 linee, poi 5.7% / 28% / 35% |
| **spikiness** | p99/mediana di \|Δ(ρ·d)/Δs\|/(ρ·d) — quanto l'evento locale più brusco spicca sul fondo della linea stessa | 1.1 ÷ 105, mediana 12.6 |
| **junction step** | scalino ρ·d testa → shooting line | 1.32 ÷ 2.66, mediana 2.08 |

**Front backup** è il difetto non opinabile: un punto dove la linea davanti è inerzialmente più
pesante di quella dietro, cioè dove un loop può incernierare o fermarsi. Viene riportata anche la
**posizione**, perché serve.

**Spikiness** è scale-free di proposito: un taper ripido non è un difetto, un *gradino* su un taper
regolare sì.

> **Zone di densità: come funziona davvero l'adattamento.** Con `ZoneDensityAdaptDiameters = true`
> il bordo della zona è un **nodo esatto** e il segmento **appena fuori** dalla zona viene
> rimodellato: il suo estremo vicino prende il valore scalato della zona
> (`d·√(ρ_base/ρ_zona)`), l'estremo lontano resta il diametro disegnato, lineare in mezzo
> (`MainWindow.ApplyZoneDensities`, stesso algoritmo di `LineDesignBuilder.Build`). Quindi:
>
> - **il diametro è continuo per costruzione** — un nodo, un valore, condiviso dai due lati;
> - **la massa è conservata dentro la zona** — più densa e più sottile a pari massa;
> - **la differenza di massa la paga il segmento adiacente rimodellato**, che resta più sottile del
>   disegnato su tutta la sua lunghezza. È il costo accettato, non un errore.
>
> `ProfileAnalyzer` replica questo: insieme dei breakpoint (nodi + bordi zona interni), diametro
> risolto in ogni breakpoint con test **chiuso** ai bordi (media dei fattori su un nodo condiviso da
> due zone), interpolazione lineare fra breakpoint, densità di ogni pezzo letta al **punto medio**.
> Siccome i bordi zona sono breakpoint, ogni pezzo sta tutto dentro o tutto fuori: la domanda "da
> che parte del bordo sta questo campione" non si pone.
>
> Due divergenze deliberate: la densità **base** non è clampata a `RhoFloor` (l'app clampa ogni
> pezzo, ma `RhoFloor` è il limite di fabbricazione del solutore di compensazione, mentre una
> densità condivisa impostata a mano è un dato di progetto — diversi file reali stanno a
> 0.917÷0.92); e una zona che punta a un ugello non definito (ρ = 0) ricade sulla base invece di
> azzerare la massa di quel tratto.

> **A parità di massa, più denso = più sottile = meno drag.** Verificato sul modello per
> 0.96 → 1.10 g/cm³ **dentro la zona**: diametro **−6.6%** (`√(0.96/1.10)`), drag normale
> **−6.4%**, Π **+6.9%**, uniforme a 15/25/35 m/s e su tutti i diametri. Il drag cala un filo meno
> del diametro per il termine di Reynolds.
>
> Al bordo però, siccome il diametro è continuo, **l'intero salto di materiale finisce in ρ·d e
> nella massa lineare** — il rapporto pieno `ρ_zona/ρ_base`, non la sua radice. Su `STD 27g 60` a
> 310 cm, andando verso la punta: diametro −0.08% (continuo), massa lineare **+14.4%**, ρ·d
> **+14.5%**.
>
> Le tre linee con front backup > 0 sono queste: `ST27-60 (2nd version)` 29.0% a 499 cm,
> `STD 27g 60` 23.5% a 309 cm, `STD 27g 60 (Italian Flag) - Front Taper Density` 5.5% a 309 cm
> (frazione della discesa picco→punta, non il gradino). L'aumento di Π nel front taper **è
> l'effetto voluto**, non un difetto.

> ⚠️ **Progetti senza densità** (`SharedDensityGCm3 = 0`, nessuna zona, nessun SpecWeight) vengono
> segnalati esplicitamente invece di riportare massa 0.0 g: in archivio sono `SA MED Original #5
> (New)`, `SA MED #5 Fake 2nd 2 of 3`, `Leader 15m`.

### Tasso di taper per segmento — `k`

La metrica su cui si legge l'effetto di una modifica. Per ogni intervallo fra due nodi di design:

```
k = ln(ρ·d_out / ρ·d_in) / L      [per 100 cm]
```

Positiva dove la linea ingrossa verso il codino (front taper, ventre), negativa lungo il back
taper, ~0 su un tratto cilindrico. È un **tasso**, quindi confrontabile fra un tip di 20 cm e un
ventre di 600, e fra progetti diversi. È agganciata ai **nodi**, non a `SegmentMetadata`: se i
metadati sono sfasati si perde solo il nome, non la geometria.

**Perché questa e non le altre.** Le metriche globali (spikiness, front backup, junction step) non
rispondono a una modifica di progetto, o rispondono col segno sbagliato. Misurato su `ST27 - 60`:

| modifica | segmento 20–310 | segmento 310–fine | spikiness globale |
|---|---|---|---|
| front taper 630 → 930 cm | 0.088 invariato | 0.074 → **0.038** | 9.3 → 17.1 (peggiora) |
| Ø nodo 310: 1.06 → 1.26 | 0.056 → **0.116** | 0.063 → **0.030** | 11.4 → 22.0 |
| Ø punta: 0.80 → 1.00 | 0.128 → **0.051** | 0.046 invariato | 14.5 → 14.6 |

La spikiness si muove solo perché si muove la sua mediana — il p99 è inchiodato dal back taper, che
queste modifiche non toccano — quindi allungare il front taper la fa *peggiorare*. `k` invece è
monotona, localizzata (si muove solo il segmento toccato) e mostra il compromesso: alzare il nodo
intermedio irripidisce la prima metà e addolcisce la seconda.

### Inviluppo di riferimento (misurato, non scelto)

345 intervalli su 52 progetti. |k| per 100 cm:

| | p10 | p25 | mediana | p75 | p90 |
|---|---|---|---|---|---|
| segmenti in **salita** (front taper, ventre) | 0.016 | 0.037 | **0.074** | 0.093 | 0.125 |
| segmenti in **discesa** (back taper) | — | 0.045 | 0.126 | 0.371 | — |

**Banda commerciale** — segmenti in salita delle copie di linee commerciali: **0.065 ÷ 0.103**. Le
sei della SA MED stanno dentro 0.073÷0.103, abbastanza strette da sembrare una regola di progetto
deliberata. La famiglia ST27/STD27 ha mediana **0.046** — circa la metà — con dispersione
0.007÷0.644.

> È un **riferimento, mai un verdetto**: un front taper fuori banda può essere esattamente quello
> che si voleva. Le costanti stanno in `TaperReference`.

> ⚠️ Lo **score 0-100 per segmento è stato rimosso**: su 363 segmenti reali stava fra 70 e 75 per il
> 94% di essi, perché la penalità sul livello di Π assumeva Π≈1 come ideale mentre le linee vere
> stanno a Π≈0.05, saturandola ovunque. Anche `ScanDesignDeltaMm` non torna in un indice di qualità:
> misura se l'estrusore ha fatto quello che era disegnato — controllo di produzione — non se il
> disegno è buono. Resta come lettura separata.

---

## 19. Formati File

### `.flp` (FlyLine Project)

JSON con i campi principali:

```json
{
  "Version": 1,
  "Name": "Nome Progetto",
  "ScanPoints": [...],
  "DesignNodes": [...],
  "NozzleDefinitions": [...],
  "NozzleZones": [...],
  "SharedDensityGCm3": 1.25,
  "IsSinking": true,
  "LineType": "Neutral",
  "IsFullLine": false,
  "WaterType": "fresh",
  "WaterTempC": 15.0,
  "CompTargetSpeedMs": 0.042,
  "ShowCompProfile": true,
  "IsCompensatedDerivative": false
}
```

> **`LineType` e `IsSinking` convivono.** `LineType` ("Floating" / "Neutral" / "Sinking") è il campo
> vero; `IsSinking` viene comunque scritto come *"tutto tranne floating"*, così una versione
> precedente dell'app continua a mostrare gli strumenti di compensazione su una linea neutra invece
> di nasconderli. Un file scritto prima che `LineType` esistesse non lo ha: viene letto da
> `IsSinking`.


### `.flproto` (Prototipo da pezzi)

JSON: `Name`, `Notes`, `JointAllowanceCm` (margine splice per estremità unita, default 4) e `Pieces`, ognuno con `Name`, `SourcePath`, `ColorHex`, `DensityGCm3`,
`PartNumber` (0 = pezzo intero, 1…n = parte dopo uno split), `Xs`/`Ds` (copia pulita della scansione, cm/mm), `Flipped`, `TrimStartCm`, `TrimEndCm`, `OffsetCm`
(posizione sul grafico dell'estremità sinistra del pezzo intero).

### `.nodes.csv`

```
Position cm,Diameter mm
0.0,2.850
120.0,3.100
...
```

---

## Appendice — Terminologia

| Termine | Significato |
|---|---|
| **NC** | Non Compensato — profilo originale di design |
| **C** | Compensato — profilo modificato per velocità uniforme |
| **CoM** | Centro di Massa (% dalla punta della testa) |
| **Rg** | Raggio di Girabilità (% della lunghezza testa) |
| **AFFTA LW** | Line Weight AFFTA (classe standard peso linea da mosca) |
| **Nozzle / Ugello** | Estrusore con cui viene prodotto il tratto di linea |
| **Sink speed** | Velocità terminale di affondamento in acqua |
| **EMA** | Exponential Moving Average — filtro digitale smoothing |
| **Frustum** | Tronco di cono — forma geometrica di un segmento conico |
| **ρ (rho)** | Densità del materiale in g/cm³ |
| **Snapshot compensato** | File `.flp` scritto dal pulsante ⚖ Compensate…, con geometria e densità proprie — non ricompensabile |
