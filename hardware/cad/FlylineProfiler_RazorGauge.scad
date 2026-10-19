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
BH = [0, 6.5];                 // fori della scheda usati (lungo il cavo): i fori a -6.5 sono troppo vicini alla ruota
BX = 10.6;                     // fori della scheda lungo X (±), asola fino a 10.0 (interasse 20 ... 21.2)
// slitta del sensore (pezzo separato): la scheda si avvita alla slitta al banco, la slitta entra da davanti
TR_T  = 2.0;                   // spessore slitta
TR_Z0 = PCB_TOP - 1.6 - TR_T;  // -5.5: faccia inferiore della slitta (il PCB appoggia sopra)
TR_TW = 14;                    // larghezza linguetta posteriore
TR_TY = 3.5;                   // linguetta spostata verso il lato rullo (lontana dalla ruota)
TR_SX = 17.0; TR_SY = 16.65;   // vite M3 di bloccaggio (linguetta anteriore oltre il bordo scheda, fuori dalla spina XH)
// connettore XH 5 poli VERTICALE (B5B-XH-A) sotto la scheda: fila pin a ty ~9.1 (stessi fori del 90 gradi originale)
XH_TY = 9.7;                   // fila dei 5 fori dei fili (misurata: 5.8 mm dal bordo scheda) (fili saldati direttamente, uscita verso il basso)
TIE_W = 18; TIE_H = 6;         // aletta antistrappo: larghezza e altezza sotto la slitta

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
            translate([-CI, -CI, Z_LF - 2.5]) cube([2*CI, 2*CI, 2.5]);                                 // fondo sede laser
            translate([0, 0, Z_LF - 0.01]) cylinder(d = 13, h = Z_TOP - Z_LF);
            translate([-CI, -CI, Z_TOP - 2]) cube([2*CI, 2*CI, 2]);
            // --- slitta del sensore: blocco con sede sul lato piastra (la linguetta della slitta entra da davanti)
            translate([-MD - 0.2, TR_TY - TR_TW/2 - 1.5, TR_Z0 - 2]) cube([MD + 0.2 - 13.3, TR_TW + 3, TR_T + 0.2 + 2 + 2]);   // fino a tx -13.3: 0.7 mm dal bordo posteriore della scheda
            // --- appoggio anteriore della slitta: colonnina sotto la linguetta anteriore + trave verso la piastra
            translate([13, 13.9, -16]) cube([6.8, 5.5, TR_Z0 + 16]);                  // oltre la spina XH (ty <= 12.6): la slitta si sfila con la spina inserita
            translate([-MD - 0.2, 13.9, -16]) cube([MD + 0.2 + 18.8, 2.5, 5]);        // trave a fianco della spina, sopra il rullo inferiore
        }
        lens_seat(Z_L1, L1_T, 9, L1_D, clear_h = 8.2);
        front_groove(Z_L1 - 4.1, Z_L1 + 4.1);
        translate([0,0,Z_LF - 6]) cylinder(d = 3.0, h = 6.01);
        translate([0,0,Z_LF]) cylinder(d = LASER_D + 2*fit, h = 4.01);
        translate([0,0,Z_LF + 4]) cylinder(d = 5.0, h = 20);
        for (a = [0, 120, 240]) translate([0,0,Z_LF + LASER_L - 2.5]) rotate([0,0,a]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 40);
        for (p = lid_screws()) translate([CI - 10, p[0], p[1]]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 10.01);
        // sede della linguetta posteriore della slitta: gioco 0.1 sotto (riferimento di quota del chip), 0.25 sopra e ai lati (MJF: si infila senza limare)
        translate([-17.4, TR_TY - TR_TW/2 - 0.25, TR_Z0 - 0.1]) cube([30, TR_TW + 0.5, TR_T + 0.35]);
        // foro M3 autofilettante nella colonnina anteriore (vite verticale dall'alto, attraverso la slitta)
        translate([TR_SX, TR_SY, -14.5]) cylinder(d = M3_TAP, h = 22.5);   // 9 mm filettabili: vite M3 x 10 (2 linguetta + 8 in presa)
    }
}

module sensor_tray() {          // coordinate torre; si stampa a parte
    difference() {
        union() {
            translate([-12.6, -5.5, TR_Z0]) cube([25.2, 21, TR_T]);                 // sagoma della scheda, accorciata sul lato ruota
            translate([-17.3, TR_TY - TR_TW/2, TR_Z0]) cube([4.8, TR_TW, TR_T]);            // linguetta posteriore (battuta in fondo alla sede)
            translate([12.5, 13.9, TR_Z0]) cube([7.3, 5.5, TR_T]);                   // linguetta anteriore (sporge 3.9 mm oltre il bordo scheda; >= 1 mm attorno al foro M3)
            // aletta antistrappo sotto la slitta: i fili saldati scendono a fianco e una fascetta da 2.5 mm li stringe all'aletta
            translate([-TIE_W/2, XH_TY + 1.0, TR_Z0 - TIE_H]) cube([TIE_W, 1.6, TIE_H + 0.01]);
        }
        translate([-6.5, XH_TY - 1.8, TR_Z0 - 1]) cube([13, 2.8, TR_T + 2]);        // passaggio dei 5 fili saldati direttamente (fila a XH_TY)
        for (sx = [-1, 1]) translate([sx*6.7 - 0.8, XH_TY + 0.9, TR_Z0 - 4.6]) cube([1.6, 1.8, 3.1]);   // asole fascetta nell'aletta
        translate([-6, -3.5, TR_Z0 - 1]) cube([12, 5.4, TR_T + 2]);                  // alleggerimento sotto il chip
        for (y = BH, s = [-1, 1]) hull() for (dx = [0, 0.6]) translate([s*(BX - dx), y, TR_Z0 - 1]) cylinder(d = BOARD_SCREW, h = TR_T + 2);   // M2 + dado sotto
        translate([TR_SX, TR_SY, TR_Z0 - 1]) cylinder(d = M3_CLR, h = TR_T + 2);    // vite M3 di bloccaggio
    }
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
        color("green") translate([-12.6, 15.5, 0.2]) rotate([180,0,0]) import("sensor.stl");
    }
    color("orange") translate([XB, Y_LINE + 1, -20]) cylinder(d = 2, h = 120);           // cavo Ø2
    color("green", 0.4) translate([PLATE_T + 0.5, 35, 49.55]) rotate([0,90,0]) cylinder(r = 200/(2*PI), h = 37); // ruota (ingombro)
    color("blue", 0.5) translate([17.22, 58.91, 9.55 + DZ_ROLL]) rotate([0,90,0]) cylinder(d = 16, h = 10);     // rullo 625 spostato
}

// NB: le booleane con lo STL importato mandano in errore CGAL: il pezzo unico si genera con
// strumenti/build_profiler.py (VIEW="column" + piastra modificata, unione con manifold).
if (VIEW == "profiler") profiler();
else if (VIEW == "column") to_plate() column_v3();
else if (VIEW == "tray") sensor_tray();     // solo colonna (unita alla piastra con lo script Python)
else if (VIEW == "lid") rotate([0,-90,0]) translate([-CI - LID_T, 0, 0]) lid_v3();
else if (VIEW == "carriage") carriage();
else if (VIEW == "assembly") assembly_v3();
