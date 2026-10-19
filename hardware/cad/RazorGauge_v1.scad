// ============================================================
//  RazorGauge - misuratore laser di diametro (versione verticale)
//  Laser in alto -> fascio verso il basso -> sensore in basso (chip verso l'alto)
//  Cavo orizzontale (asse Y), fila di pixel lungo X (avanti-dietro)
//  Stampa: HP Multi Jet Fusion (PA12)
//  Assi: Z = asse ottico (verso l'alto), origine = superficie del chip
//  Uso: openscad -D 'PART="tower"' -o tower.stl cable_gauge_v.scad
// ============================================================
PART = "assembly";   // "tower" | "lid" | "carriage" | "assembly" | "none"

fit   = 0.15;   // gioco sedi lenti / laser
slide = 0.20;   // gioco per lato carrello
$fn = 96;

// ---------- Quote ottiche (distanza dalla superficie del chip) ----------
Z_CHIP   = 0;
CABLE_FLOOR = 2.5;          // appoggio cavo: fondo cavo a 2.5 mm dal chip
Z_L2     = 24.5;            // ~20 mm sopra l'asse del cavo
L2_TRAVEL = 6;              // regolazione ± di L2
L1_F     = -19.3;           // L1 biconcava f = -19.3
L2_F     = 100;
Z_L1     = Z_L2 + L2_F + L1_F;  // 105.2  (L1-L2 = 80.7, collimazione)
Z_LF     = Z_L1 + 15;       // 120.2  faccia anteriore laser

// ---------- Componenti ----------
LASER_D = 4.0;  LASER_L = 14.0;
LENS_D  = 12.7;
L1_T    = 3.11;             // biconcava F12F-19.3: spessore al bordo misurato
L1_D    = 12.47;            // diametro misurato L1
L2_T_SEAT = 2.35;           // PCX: bordo 2.15 + sagitta a r=5
CHIP_H  = 1.9;              // da SensorAssembly.stl: package chip 1.9 mm sopra il PCB (PCB 1.6)
PCB_TOP = Z_CHIP - CHIP_H;  // faccia superiore PCB
BOARD_HOLE_SPACING = 21.2;  // da STL (misura manuale 20): fori medi, allineati al chip
BOARD_HOLE_TOL     = 1.2;   // asola lungo X: accetta interasse 20.0 ... 21.2
BOARD_HOLE_OFFSET  = 0;     // da STL: coppia di fori centrale in asse col chip
BOARD_SCREW = 2.3;          // viti M2 (fori scheda Ø2)

// ---------- Colonna ottica ----------
CI  = 9;                    // semi-luce interna canale (18 x 18)
WT  = 3;                    // pareti 3 mm (PA12 MJF: opaco e rigido)
Z_COL = 12;                 // base della colonna
Z_TOP = Z_LF + LASER_L + 4; // 138.2
LID_T = 2;
BOSS_Y = CI + 5.5;          // sporgenza borchie viti coperchio

// ---------- Guida cavo (profilo a "J": ingresso frontale, poi il cavo cade nella tasca) ----------
PW      = 1.75;             // tasca 3.5 mm: cavo 3 mm -> ±0.25, cavo 0.5 -> ±1.5  (cavo max 3 mm)
LIP     = CABLE_FLOOR + 3.5;  // bordo anteriore tasca
ENTRY_T = Z_COL;            // soffitto canale d'ingresso
CHEEK_Y1 = 22; CHEEK_Y2 = 26;   // guance sottili (4 mm) con la guida J
// ---------- Fissaggio a piano verticale (parallelo all'asse ottico, dietro la torre) ----------
MOUNT_DIST = 35.4;          // distanza piano di appoggio <-> asse del fascio
PLATE_T    = 5;             // spessore fasce di fissaggio
PLATE_W    = 52;            // larghezza fasce (lungo Y)
BAND_H     = 16;            // altezza fasce
MOUNT_SCREW = 4.5;          // passanti M4
X_BACK = -MOUNT_DIST;  X_FRONT = 16;
L2_DOWN = 5; L2_UP = 6;     // corsa carrello (sotto: battuta a fondo colonna)
CAR_SCREW_X = -4;           // posizione vite di blocco carrello (lungo X)

M3_TAP = 2.5;  M3_CLR = 3.4;

// clear_h: altezza del foro libero per il fascio. CORRETTO 7/10/2026: era fisso a 40 mm e per L1 (Z 105.2)
// arrivava a Z 125.2, asportando la battuta Ø3 e il perno Ø4.3 della sede laser (Z 117.7-124.2).
module lens_seat(zc, t, clear_d, D = LENS_D, clear_h = 40) {   // lente inserita dal fronte, appoggiata sulla faccia inferiore
    translate([0,0,zc]) {
        cylinder(d = D + 2*fit, h = t + 2*fit, center = true);
        translate([0, -(D/2 + fit), -(t + 2*fit)/2]) cube([30, D + 2*fit, t + 2*fit]);
        cylinder(d = clear_d, h = clear_h, center = true);
    }
}
module front_groove(z1, z2) { translate([L1_D/2, -1.6, z1]) cube([10, 3.2, z2 - z1]); }

module j_cut() {
    rotate([90,0,0]) linear_extrude(height = 200, center = true)
        polygon([[-PW, CABLE_FLOOR], [PW, CABLE_FLOOR], [PW, LIP], [60, LIP], [60, ENTRY_T], [-PW, ENTRY_T]]);
}

function mount_holes() = [ for (z = [36, Z_TOP - 12]) for (s = [-1,1]) [s*21, z] ];
function lid_screws() = [ for (z = [18, 70, Z_TOP - 5]) for (s = [-1,1]) [s*(CI + BOSS_Y)/2, z] ];

module tower() {
    difference() {
        union() {
            // --- colonna: parete posteriore + pareti laterali (3 mm)
            translate([-CI - WT, -CI - WT, Z_COL]) cube([WT, 2*(CI + WT), Z_TOP - Z_COL]);
            for (s=[-1,1]) translate([-CI - WT, s > 0 ? CI : -CI - WT, Z_COL]) cube([2*CI + WT, WT, Z_TOP - Z_COL]);
            // borchie per le viti del coperchio
            for (p = lid_screws()) translate([0, p[0] > 0 ? CI : -BOSS_Y, p[1] - 4]) cube([CI, BOSS_Y - CI, 8]);
            // battute di fondo per il carrello (fuori dal fascio)
            for (s=[-1,1]) translate([-CI, s > 0 ? CI - 1.5 : -CI, Z_COL]) cube([2*CI, 1.5, 1.5]);
            // blocco L1
            translate([-CI, -CI, Z_L1 - 4]) cube([2*CI, 2*CI, 8]);
            // sede laser alleggerita: fondo con battuta, boccola Ø13, tappo superiore (tenuta luce)
            translate([-CI, -CI, Z_LF - 2.5]) cube([2*CI, 2*CI, 2.5]);
            translate([0, 0, Z_LF - 0.01]) cylinder(d = 13, h = Z_TOP - Z_LF);
            translate([-CI, -CI, Z_TOP - 2]) cube([2*CI, 2*CI, 2]);
            // --- telaio inferiore
            // guance sottili con la guida cavo, fino al piano di fissaggio
            for (s=[-1,1]) translate([X_BACK, s > 0 ? CHEEK_Y1 : -CHEEK_Y2, 0]) cube([X_FRONT - X_BACK, CHEEK_Y2 - CHEEK_Y1, Z_COL + 4]);
            // solaio di collegamento colonna - guance - piano (z 12..16)
            for (s=[-1,1]) translate([X_BACK, s > 0 ? CI : -CHEEK_Y2, Z_COL]) cube([CI - X_BACK, CHEEK_Y2 - CI, 4]);
            translate([X_BACK, -CI - WT, Z_COL]) cube([-CI - WT - X_BACK + 0.01, 2*(CI + WT), 4]);
            // costole tra colonna e piano (allineate alle pareti laterali), alleggerite
            for (s=[-1,1]) translate([X_BACK, s > 0 ? CI : -CI - WT, Z_COL]) cube([-CI - WT - X_BACK + 0.01, WT, Z_TOP - Z_COL]);
            // fasce di fissaggio al piano
            for (z = [36, Z_TOP - 12]) translate([X_BACK, -PLATE_W/2, z - BAND_H/2]) cube([PLATE_T, PLATE_W, BAND_H]);
            // ponti porta-scheda (anteriore e posteriore), sotto la quota del cavo
            for (s=[-1,1]) translate([s > 0 ? 6 : -14, -CHEEK_Y2, 1.5]) cube([8, 2*CHEEK_Y2, 2.5]);
            // pad di appoggio scheda
            for (s=[-1,1]) hull() for (dy=[-3,3], dx=[0, -BOARD_HOLE_TOL/2]) translate([s*(BOARD_HOLE_SPACING/2 + dx), BOARD_HOLE_OFFSET + dy, PCB_TOP]) cylinder(d = 6, h = 1.5 - PCB_TOP + 0.01);
        }
        // --- finestre di alleggerimento nelle costole (esterne alla colonna, non fanno entrare luce)
        translate([X_BACK + 4, -50, 46]) cube([-CI - WT - X_BACK - 8, 100, Z_TOP - 12 - BAND_H/2 - 4 - 46]);
        // --- finestre nel solaio posteriore
        for (s=[-1,1]) translate([X_BACK + 4, s > 0 ? CI + WT + 2 : -CHEEK_Y1 + 1, Z_COL - 1]) cube([-CI - WT - X_BACK - 8, CHEEK_Y1 - CI - WT - 3, 6]);
        // --- L1
        lens_seat(Z_L1, L1_T, 9, L1_D, clear_h = 8.2);   // L1 biconcava: foro libero solo nel blocco L1 (Z 101.2-109.2)
        front_groove(Z_L1 - 4.1, Z_L1 + 4.1);
        // --- laser: labbro Ø3 (battuta) / perno Ø4.3 / zona regolazione Ø5 aperta in alto
        translate([0,0,Z_LF - 6]) cylinder(d = 3.0, h = 6.01);
        translate([0,0,Z_LF]) cylinder(d = LASER_D + 2*fit, h = 4.01);
        translate([0,0,Z_LF + 4]) cylinder(d = 5.0, h = 20);
        // 3 grani M3 di puntamento a 120° (0° = fronte, accesso dal coperchio; gli altri dai fianchi)
        for (a = [0, 120, 240]) translate([0,0,Z_LF + LASER_L - 2.5]) rotate([0,0,a]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 40);
        // --- asola verticale per bloccare il carrello L2 (vite M3 + rondella dal fianco +Y)
        hull() for (dz=[-L2_DOWN, L2_UP]) translate([CAR_SCREW_X, CI - 1, Z_L2 + dz]) rotate([-90,0,0]) cylinder(d = M3_CLR, h = WT + 2);
        // --- guida cavo
        j_cut();
        // --- zona libera sopra la scheda (componenti fino a 2.5 mm) tra i ponti
        translate([-6, -CHEEK_Y1, PCB_TOP - 5]) cube([12, 2*CHEEK_Y1, 5 + CABLE_FLOOR - PCB_TOP - 0.01]);
        // --- asole scheda M2 (dado sopra il ponte): ±3 mm lungo Y per centrare il chip sul fascio
        for (s=[-1,1]) hull() for (dy=[-3,3], dx=[0, -BOARD_HOLE_TOL/2]) translate([s*(BOARD_HOLE_SPACING/2 + dx), BOARD_HOLE_OFFSET + dy, PCB_TOP - 1]) cylinder(d = BOARD_SCREW, h = 10);
        // --- fori coperchio (M3 autofilettanti nelle borchie)
        for (p = lid_screws()) translate([CI - 10, p[0], p[1]]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 10.01);
        // --- fissaggio al piano: 4 fori M4 passanti
        for (p = mount_holes()) translate([X_BACK - 1, p[0], p[1]]) rotate([0,90,0]) cylinder(d = MOUNT_SCREW, h = PLATE_T + 2);
    }
}

module carriage() {   // centrato in z = 0
    H = 12;
    difference() {
        translate([-CI + slide, -CI + slide, -H/2]) cube([2*CI - 2*slide, 2*CI - 2*slide, H]);
        lens_seat(0, L2_T_SEAT, 10);
        front_groove(-H/2 - 1, H/2 + 1);
        translate([CAR_SCREW_X, CI - 7, 0]) rotate([-90,0,0]) cylinder(d = M3_TAP, h = 8);   // vite di blocco dal fianco +Y
        // alleggerimento: smussi degli spigoli posteriori (lontani da sede e vite)
        for (s=[-1,1]) translate([-CI, s*CI, 0]) rotate([0,0,45]) cube([5, 5, H + 2], center = true);
    }
}

module lid() {
    difference() {
        union() {
            translate([CI, -BOSS_Y, Z_COL]) cube([LID_T, 2*BOSS_Y, Z_TOP - Z_COL]);
            // costola: trattiene L1 e L2 (0.2 mm di gioco sul bordo lente)
            translate([L1_D/2 + 0.2, -1.4, Z_COL + 0.5]) cube([CI - L1_D/2 - 0.2 + 0.01, 2.8, Z_L1 + 4 - Z_COL - 0.5]);
        }
        for (p = lid_screws()) translate([CI - 1, p[0], p[1]]) rotate([0,90,0]) cylinder(d = M3_CLR, h = 10);
        translate([CI - 1, 0, Z_LF + LASER_L - 2.5]) rotate([0,90,0]) cylinder(d = 3.5, h = 10);  // accesso grano anteriore
        // nome inciso sul fronte (0.6 mm, leggibile dal basso verso l'alto)
        translate([CI + LID_T - 0.6, 0, 62]) rotate([90,0,90]) rotate([0,0,90])
            linear_extrude(height = 1) text("RazorGauge", size = 6, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
        // alleggerimento ai lati della colonna (fuori dalle pareti): il coperchio copre solo dove serve
        for (s=[-1,1]) for (z=[[24,64],[76,Z_TOP-11]]) translate([CI - 1, s > 0 ? CI + WT + 0.01 : -BOSS_Y - 0.01, z[0]]) cube([LID_T + 2, BOSS_Y - CI - WT, z[1] - z[0]]);
    }
}

module assembly() {
    color("dimgray") tower();
    color("slategray") translate([0,0,Z_L2]) carriage();
    color("gray", 0.3) lid();
    color("red") translate([0,0,Z_LF]) cylinder(d = LASER_D, h = LASER_L);
    color("lightblue", 0.8) for (z=[Z_L1, Z_L2]) translate([0,0,z]) cylinder(d = LENS_D, h = 2.5, center = true);
    color("orange") translate([0, 0, CABLE_FLOOR + 1.5]) rotate([90,0,0]) cylinder(d = 3, h = 90, center = true);
    // scheda reale (SensorAssembly.stl): chip in su, centro finestra chip in (0,0), faccia chip a z=0
    color("green") translate([-12.6, 15.5, 0.2]) rotate([180,0,0]) import("sensor.stl");
}

if (PART == "tower") tower();
else if (PART == "lid") rotate([0,-90,0]) translate([-CI - LID_T, 0, 0]) lid();
else if (PART == "carriage") carriage();
else if (PART == "assembly") assembly();
