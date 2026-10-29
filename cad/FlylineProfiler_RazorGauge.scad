// ============================================================
//  FlylineProfiler V3 + RazorGauge — piastra e torre in un pezzo unico (MJF PA12)
//  Base: FlylineProfiler_V3 (piastra 3 mm, encoder, rulli guida). Comparatore rimosso.
//  Vincoli (8/10/2026):
//   - il cavo resta sul piano attuale (sopra la ruota encoder, premuto dal rullo superiore): fondo cavo Y 66.91
//   - asse del cavo a 19.2 mm dalla faccia anteriore della piastra (X 22.22 dalla faccia posteriore)
//   - chip TSL1401 2.5 mm sotto il fondo del cavo (Y 64.41); scheda Hiwonder com'è (lato corto verso la ruota)
//   - punto di misura a Z 21.55: interasse ruota encoder <-> laser 28.00 mm (cifra tonda, 8/10/2026)
//   - rullo inferiore (cuscinetti 625, Ø16), il suo braccio e lo spintore spostati di 13 mm verso -Z,
//     piastra allargata di 13 mm su quel lato
//  Coordinate piastra (file STL originale): X fuori dalla piastra, Y verticale (in alto), Z lungo il cavo.
//  Coordinate torre (come RazorGauge.scad): z = asse ottico, y = lungo il cavo, x = fuori dalla piastra.
//  Uso: openscad -D 'VIEW="profiler"' -o FlylineProfiler_RazorGauge.stl FlylineProfiler_RazorGauge.scad
//       VIEW = profiler | lid | carriage | assembly
// ============================================================
include <RazorGauge.scad>      // parametri e moduli della torre v2 (L2 Ø19.95, sede laser corretta)
PART = "none";                 // spegne il rendering del file incluso
CAR_FRONT_SCREW = true;        // vite del carrello L2 dal davanti (asola nel coperchio): il fianco della colonna e' coperto dal blocco guida dello spintore
VIEW = "assembly";             // profiler | lid | carriage | assembly

PLATE_SRC = "../integrazione_profiler/FlylineProfiler_senza_comparatore.stl";

// ---- posizione della torre sulla piastra
XB = 22.22;                    // asse del fascio / del cavo: distanza dalla faccia posteriore della piastra
PLATE_T = 3;                   // spessore piastra
MD = XB - PLATE_T;             // 19.22: asse fascio <-> faccia anteriore della piastra
Y_LINE = 66.91;                // fondo del cavo (piano di scorrimento attuale)
YC = Y_LINE - CABLE_FLOOR;     // 64.41: faccia del chip
ZC = 21.55;                    // punto di misura lungo il cavo: 28.00 mm dall'asse della ruota encoder (Z 49.55)
DZ_ROLL = -16;                 // spostamento del rullo inferiore (braccio + spintore): centro Z -6.45, 28.00 mm dal laser

// ---- modifiche alla torre per il montaggio integrato
CAR_SCREW_X = -6;              // vite carrello: lontana dal perno dello spintore spostato
function lid_screws() = [ for (z = [40, 75, Z_TOP - 5]) for (s = [-1,1]) [s*(CI + BOSS_Y)/2, z] ];
function lid_windows() = [[18, 34], [46, 69], [81, Z_TOP - 11]];   // alleggerimenti del coperchio lontani 6 mm dalle viti a 40 e 75
// ---- SCHEDA SENSORE v2 (TSL1401CL SMD, scheda propria) + SLITTA RIGIDA SU MENSOLA PIENA (28/10/2026)
// Prima: slitta da 2 mm su una colonnina retta da una trave 2.5 x 5 mm lunga ~28 mm (cedeva ~1 mm con 6 N: segnalato
// dall'utente). Ora: MENSOLA PIENA fusa con la piastra sotto tutta la scheda; la slitta (3.5 mm) appoggia a piano sulla
// mensola (riferimento di quota del chip), linguetta posteriore nella piastra, 2 viti M3 verticali davanti.
S_CHIP_H = 1.2;                // TSL1401CL (datasheet fig. 10): package 9.4 x 3.0 x 1.2 ±0.2; pixel 0.22 sotto la faccia superiore (resina n 1.56)
S_PCB_T  = 1.6;
S_PCB_TOP = Z_CHIP - S_CHIP_H; // faccia superiore della scheda (chip a Z_CHIP = 0)
S_PCB = [[-12, 12], [-6, 12]]; // sagoma scheda (coordinate torre): x attraverso il cavo, y lungo il cavo (lato ruota = y negativo)
S_HOLES = [[-10.5, -2], [-10.5, 6], [10.5, -2.5]];     // M2 autofilettanti nella slitta (teste fuori dal fascio e dalle guide J)
S_CONN = [[7.75, 12], [1.5, 11.5], 4.3];             // connettore 6 poli a ingresso laterale sul bordo anteriore (x, y, altezza)
TR_T  = 3.5;                   // spessore slitta
TR_Z0 = S_PCB_TOP - S_PCB_T - TR_T;   // -6.3: faccia inferiore slitta = faccia superiore mensola (Y piastra 58.11)
TR_X  = [-14.8, 20.3];         // slitta: 0.2 dalla faccia della piastra (tx -15.0) fino a 1 mm oltre il fronte della mensola (31/10/2026: bordo attorno alla svasatura 1.36)
TR_Y  = [-3.8, 17.5];          // lungo il cavo (sotto); lato ruota smussato fino a y -6 in alto
TR_TONGUE = [[-17.4, -14.8], [-2, 10], 2.0];         // linguetta posteriore nella piastra (x, y, spessore)
TR_SCREWS = [[15.9, 9.0, 1], [16.0, 14.3, 0]];       // viti M3 verticali [x, y, svasata] nella mensola.
                                                     // 30/10/2026: quella a y -2.5 era sul percorso di montaggio della ruota encoder -> y 9 (Z 12.55, fuori
                                                     // dalla ruota e dal canale Ø6.5 del cacciavite), M3x12 a testa SVASATA a filo della slitta: sopra passa la
                                                     // spina del connettore (staccarla per svitare). x 15.9: cacciavite Ø3.2 fuori dal coperchio (X 36.2) di 0.3.
                                                     // 31/10/2026: l'altra da y 15.5 a 14.3 (il foro era a 0.3 mm dal bordo della slitta).
TR_SCR_D = 3.2;                // fori delle viti nella slitta (era 3.4): posizionamento ripetibile ±0.1 quando si rimette la slitta
// mensola (coordinate torre): da dentro la piastra fino a X 41.5; Z piastra 3.0 ... 30.0; Y piastra 47 ... faccia slitta
PED_X = [-MD - 0.2, 19.3];
PED_Y = [21.55 - 30.0, 21.55 - 3.0];                 // il rullo inferiore arriva a Z 1.55
PED_Z = [47.0 - YC, TR_Z0];
WHEEL_AX = [21.55 - 49.55, 35.0 - YC];               // asse ruota encoder in coordinate torre (y, z)
WHEEL_CLR_R = 200/(2*PI) + 1.5;                      // ruota Ø63.66 + 1.5 mm di gioco radiale
WHEEL_CUT_X = [12 - XB, 45 - XB];                    // scarico ruota PASSANTE fino al fronte della mensola (30/10/2026): la ruota si infila in asse dal davanti

module to_plate() { translate([XB, YC, ZC]) rotate([-90, 0, 0]) children(); }   // torre -> piastra

// ---------------------------------------------------------------- piastra modificata
module plate_mod() {
    arm    = [[3.01, 40, 3.0], [27.5, 25.5, 13.0]];     // braccio del rullo inferiore (Y 41-65)
    holder = [[3.01, 104, 3.0], [27.5, 14.5, 13.0]];    // supporto dello spintore sopra il rullo inferiore
    union() {
        difference() {
            import(PLATE_SRC);
            translate([3.01, 63.0, 15.0]) cube([27.3, 7.5, 24.0]);          // appoggio centrale (vecchia sede)
            translate(arm[0]) cube(arm[1]);
            translate(holder[0]) cube(holder[1]);
        }
        for (b = [arm, holder]) translate([0, 0, DZ_ROLL]) intersection() { import(PLATE_SRC); translate(b[0]) cube(b[1]); }
        // piastra allargata di 13 mm sul lato del rullo (Z 3.6 -> -9.4)
        hull() for (y = [41 + 2.5, 177.9 - 2.5]) for (z = [3.6 + DZ_ROLL + 2.5, 6]) translate([0, y, z]) rotate([0, 90, 0]) cylinder(r = 2.5, h = PLATE_T);
    }
}

// ---------------------------------------------------------------- colonna ottica (coordinate torre)
module column_v3() {
    difference() {
        union() {
            // pareti della colonna + riempimento fino alla piastra (fuso con la piastra)
            translate([-MD - 0.2, -CI - WT, Z_COL]) cube([MD + 0.2 - CI, 2*(CI + WT), Z_TOP - Z_COL]);
            for (s=[-1,1]) translate([-CI - WT, s > 0 ? CI : -CI - WT, Z_COL]) cube([2*CI + WT, WT, Z_TOP - Z_COL]);
            for (p = lid_screws()) translate([0, p[0] > 0 ? CI : -BOSS_Y, p[1] - 4]) cube([CI, BOSS_Y - CI, 8]);
            for (s=[-1,1]) translate([-CI, s > 0 ? CI - 1.5 : -CI, Z_COL]) cube([2*CI, 1.5, 1.5]);   // battute carrello
            // blocco L1 alleggerito: mozzo attorno alla sede + razza anteriore (inserimento lente e costola del coperchio) + 3 razze
            translate([0, 0, Z_L1 - 4]) cylinder(d = L1_D + 2*fit + 5.2, h = 8);
            translate([0, -(L1_D/2 + fit + 2.2), Z_L1 - 4]) cube([CI, L1_D + 2*fit + 4.4, 8]);
            translate([-CI, -3, Z_L1 - 4]) cube([CI, 6, 8]);
            for (s=[-1,1]) translate([-3, s > 0 ? 0 : -CI, Z_L1 - 4]) cube([6, CI, 8]);
            laser_block();                                                                              // sede laser v3 (29/10/2026)
            translate([-CI, -CI, Z_TOP - 2]) cube([2*CI, 2*CI, 2]);
            // --- mensola piena sotto la slitta del sensore (sostituisce sede + trave 2.5 x 5 + colonnina, 28/10/2026)
            pedestal();
        }
        lens_seat(Z_L1, L1_T, 9, L1_D, clear_h = 8.2);
        front_groove(Z_L1 - 4.1, Z_L1 + 4.1);
        laser_cuts();
        for (p = lid_screws()) translate([CI - 10, p[0], p[1]]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 10.01);
        // fori M3 autofilettanti per le 2 viti della slitta (10 mm in presa nella mensola)
        for (s = TR_SCREWS) translate([s[0], s[1], TR_Z0 - 10]) cylinder(d = M3_TAP, h = 10.01);
    }
}

module pedestal() {              // coordinate torre
    difference() {
        translate([PED_X[0], PED_Y[0], PED_Z[0]]) cube([PED_X[1] - PED_X[0], PED_Y[1] - PED_Y[0], PED_Z[1] - PED_Z[0]]);
        // gioco con la ruota encoder (1.5 mm radiali) nel tratto X 12 ... 34
        translate([WHEEL_CUT_X[0], WHEEL_AX[0], WHEEL_AX[1]]) rotate([0, 90, 0]) cylinder(r = WHEEL_CLR_R, h = WHEEL_CUT_X[1] - WHEEL_CUT_X[0], $fn = 180);
        // 30/10/2026: dove lo scarico della ruota esce dal piano della mensola restava un filo di 0.4 mm: gradino a 1.0 mm
        translate([WHEEL_CUT_X[0], PED_Y[0] - 1, TR_Z0 - 1.01]) cube([WHEEL_CUT_X[1] - WHEEL_CUT_X[0], (21.55 - 24.6) - (PED_Y[0] - 1), 1.2]);
        // spigoli verticali anteriori smussati 1 mm
        for (yy = PED_Y) translate([PED_X[1], yy, (PED_Z[0] + PED_Z[1])/2]) rotate([0, 0, 45]) cube([1.42, 1.42, PED_Z[1] - PED_Z[0] + 2], center = true);
    }
}

module sensor_tray() {          // coordinate torre; si stampa a parte
    difference() {
        union() {
            hull() {            // corpo: lato ruota smussato (y -3.8 sotto -> -6 sopra)
                translate([TR_X[0], TR_Y[0], TR_Z0]) cube([TR_X[1] - TR_X[0], TR_Y[1] - TR_Y[0], 0.01]);
                translate([TR_X[0], S_PCB[1][0], TR_Z0 + TR_T - 0.01]) cube([TR_X[1] - TR_X[0], TR_Y[1] - S_PCB[1][0], 0.01]);
            }
            translate([TR_TONGUE[0][0], TR_TONGUE[1][0], TR_Z0]) cube([TR_TONGUE[0][1] - TR_TONGUE[0][0] + 0.01, TR_TONGUE[1][1] - TR_TONGUE[1][0], TR_TONGUE[2]]);
        }
        for (h = S_HOLES) translate([h[0], h[1], TR_Z0 - 1]) cylinder(d = 1.7, h = TR_T + 2);        // M2 autofilettanti
        for (s = TR_SCREWS) translate([s[0], s[1], TR_Z0 - 1]) cylinder(d = TR_SCR_D, h = TR_T + 2);  // viti M3 nella mensola
        for (s = TR_SCREWS) if (s[2] == 1) translate([s[0], s[1], TR_Z0 + TR_T - 1.40]) cylinder(d1 = TR_SCR_D, d2 = 6.2, h = 1.41, $fn = 48);   // svasatura 90° (testa ISO 10642 M3, Ø6 reale)
        translate([-6, -2.5, TR_Z0 + TR_T - 0.6]) cube([12, 5, 1]);   // scarico 0.6 sotto il chip (niente appoggio sotto il package)
    }
}

module sensor_pcb() {           // ingombro della scheda v2 (coordinate torre), solo per assieme e verifiche
    translate([S_PCB[0][0], S_PCB[1][0], S_PCB_TOP - S_PCB_T]) cube([S_PCB[0][1] - S_PCB[0][0], S_PCB[1][1] - S_PCB[1][0], S_PCB_T]);
    translate([-4.7, -1.5, S_PCB_TOP]) cube([9.4, 3.0, S_CHIP_H]);                                   // TSL1401CL
    translate([S_CONN[0][0], S_CONN[1][0], S_PCB_TOP]) cube([S_CONN[0][1] - S_CONN[0][0], S_CONN[1][1] - S_CONN[1][0], S_CONN[2]]);
    translate([S_CONN[0][1], S_CONN[1][0] + 1, S_PCB_TOP + 0.3]) cube([9, S_CONN[1][1] - S_CONN[1][0] - 2, 3.6]);   // spina + uscita cavo
    for (h = S_HOLES) translate([h[0], h[1], S_PCB_TOP]) cylinder(d = 3.8, h = 1.6);                  // teste M2
}

module profiler() {
    union() {
        plate_mod();
        to_plate() column_v3();
    }
}

module lid_v3() { lid(); }      // coperchio v2 con le viti spostate (lid_screws ridefinita sopra)

module assembly_v3() {
    color("silver") profiler();
    to_plate() {
        color("slategray") translate([0,0,Z_L2]) carriage();
        color("gray", 0.35) lid_v3();
        color("red") translate([0,0,Z_LF]) cylinder(d = LASER_D, h = LASER_L);
        color("gray") laser_cap();
        color("green") sensor_pcb();
        color("orange") sensor_tray();
    }
    color("orange") translate([XB, Y_LINE + 1, -20]) cylinder(d = 2, h = 120);           // cavo Ø2
    color("green", 0.4) translate([PLATE_T + 0.5, 35, 49.55]) rotate([0,90,0]) cylinder(r = 200/(2*PI), h = 37); // ruota (ingombro)
    color("blue", 0.5) translate([17.22, 58.91, 9.55 + DZ_ROLL]) rotate([0,90,0]) cylinder(d = 16, h = 10);     // rullo 625 spostato
}

// NB: le booleane con lo STL importato mandano in errore CGAL: il pezzo unico si genera con
// strumenti/build_profiler.py (VIEW="column" + piastra modificata, unione con manifold).
if (VIEW == "profiler") profiler();
else if (VIEW == "column") to_plate() column_v3();
else if (VIEW == "tray") sensor_tray();
else if (VIEW == "tray_plate") to_plate() sensor_tray();
else if (VIEW == "pcb_plate") to_plate() sensor_pcb();
else if (VIEW == "pcb") sensor_pcb();
else if (VIEW == "lid") rotate([0,-90,0]) translate([-CI - LID_T, 0, 0]) lid_v3();
else if (VIEW == "carriage") carriage();
else if (VIEW == "laser_cap") laser_cap();
else if (VIEW == "laser_cap_plate") to_plate() laser_cap();
else if (VIEW == "laser_plate") to_plate() translate([0,0,Z_LF]) cylinder(d = LASER_D, h = LASER_L);
else if (VIEW == "assembly") assembly_v3();
