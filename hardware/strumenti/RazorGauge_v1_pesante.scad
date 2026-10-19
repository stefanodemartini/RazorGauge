// ============================================================
//  Misuratore diametro cavo - VERSIONE VERTICALE
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
WT  = 5;
Z_COL = 12;                 // base della colonna
Z_TOP = Z_LF + LASER_L + 4; // 127.5
LID_T = 3;

// ---------- Guida cavo (profilo a "J": ingresso frontale, poi il cavo cade nella tasca) ----------
PW      = 1.75;             // tasca 3.5 mm: cavo 3 mm -> ±0.25, cavo 0.5 -> ±1.5  (cavo max 3 mm)
LIP     = CABLE_FLOOR + 3.5;  // bordo anteriore tasca
ENTRY_T = Z_COL;            // soffitto canale d'ingresso
CHEEK_Y1 = 18; CHEEK_Y2 = 28;
// ---------- Fissaggio a piano verticale (parallelo all'asse ottico, dietro la torre) ----------
MOUNT_DIST = 35.4;          // distanza piano di appoggio <-> asse del fascio
PLATE_T    = 6;             // spessore piastra di fissaggio
PLATE_W    = 56;            // larghezza piastra (lungo Y)
MOUNT_SCREW = 4.5;          // passanti M4
MOUNT_CB    = 8.5;          // lamatura testa M4 (lato torre)
X_BACK = -MOUNT_DIST + PLATE_T; X_FRONT = 16;
Z_FOOT = -14;               // fondo guance / piastra (connettore XH libero sotto la scheda)

M3_TAP = 2.5;  M3_CLR = 3.4;

module lens_seat(zc, t, clear_d, D = LENS_D) {   // lente inserita dal fronte, appoggiata sulla faccia inferiore
    translate([0,0,zc]) {
        cylinder(d = D + 2*fit, h = t + 2*fit, center = true);
        translate([0, -(D/2 + fit), -(t + 2*fit)/2]) cube([30, D + 2*fit, t + 2*fit]);
        cylinder(d = clear_d, h = 40, center = true);
    }
}
module front_groove(z1, z2) { translate([L1_D/2, -1.6, z1]) cube([10, 3.2, z2 - z1]); }

module j_cut() {
    rotate([90,0,0]) linear_extrude(height = 200, center = true)
        polygon([[-PW, CABLE_FLOOR], [PW, CABLE_FLOOR], [PW, LIP], [60, LIP], [60, ENTRY_T], [-PW, ENTRY_T]]);
}

function mount_holes() = [ for (z = [36, Z_TOP - 12]) for (s = [-1,1]) [s*21, z] ];
function lid_screws() = [ for (z = [18, 70, Z_TOP - 5]) for (s = [-1,1]) [s*(CI + WT/2), z] ];

module tower() {
    difference() {
        union() {
            // --- colonna: parete posteriore + pareti laterali
            translate([-CI - WT, -CI - WT, Z_COL]) cube([WT, 2*(CI + WT), Z_TOP - Z_COL]);
            for (s=[-1,1]) translate([-CI - WT, s > 0 ? CI : -CI - WT, Z_COL]) cube([2*CI + WT, WT, Z_TOP - Z_COL]);
            // blocco L1
            translate([-CI, -CI, Z_L1 - 4]) cube([2*CI, 2*CI, 8]);
            // blocco laser
            translate([-CI, -CI, Z_LF - 5.5]) cube([2*CI, 2*CI, Z_TOP - Z_LF + 5.5]);
            // --- telaio inferiore
            // guance con la guida cavo (fanno anche da piedi)
            for (s=[-1,1]) translate([X_BACK, s > 0 ? CHEEK_Y1 : -CHEEK_Y2, Z_FOOT]) cube([X_FRONT - X_BACK, CHEEK_Y2 - CHEEK_Y1, Z_COL + 4 - Z_FOOT]);
            // piastra di collegamento colonna-guance
            for (s=[-1,1]) translate([-CI - WT, s > 0 ? CI : -CHEEK_Y2, Z_COL]) cube([2*CI + WT, CHEEK_Y2 - CI, 4]);
            // traversa posteriore
            translate([X_BACK, -CHEEK_Y2, Z_FOOT]) cube([6, 2*CHEEK_Y2, Z_COL + 8 - Z_FOOT]);
            translate([X_BACK, -CI - WT, Z_COL]) cube([X_BACK*-1 - CI - WT + 0.01, 2*(CI + WT), 8]);
            // piastra di fissaggio al piano (faccia posteriore a MOUNT_DIST dall'asse)
            translate([-MOUNT_DIST, -PLATE_W/2, Z_FOOT]) cube([PLATE_T, PLATE_W, Z_TOP - Z_FOOT]);
            // due costole tra piastra e colonna (allineate alle pareti laterali)
            for (s=[-1,1]) translate([X_BACK - 0.01, s > 0 ? CI : -CI - WT, Z_COL]) cube([-CI - WT - X_BACK + 0.02, WT, Z_TOP - Z_COL]);
            // ponti porta-scheda (anteriore e posteriore), sotto la quota del cavo
            for (s=[-1,1]) translate([s > 0 ? 6 : -14, -CHEEK_Y2, 1.5]) cube([8, 2*CHEEK_Y2, 2.5]);
            // pad di appoggio scheda
            for (s=[-1,1]) hull() for (dy=[-3,3], dx=[0, -BOARD_HOLE_TOL/2]) translate([s*(BOARD_HOLE_SPACING/2 + dx), BOARD_HOLE_OFFSET + dy, PCB_TOP]) cylinder(d = 6, h = 1.5 - PCB_TOP + 0.01);
        }
        // --- canale interno aperto sul fronte sotto al blocco L1 e tra L1 e laser: già vuoto
        // --- L1
        lens_seat(Z_L1, L1_T, 9, L1_D);   // L1 biconcava
        front_groove(Z_L1 - 4.1, Z_L1 + 4.1);
        // --- laser: labbro Ø3 (battuta) / perno Ø4.3 / zona regolazione Ø5 aperta in alto
        translate([0,0,Z_LF - 6]) cylinder(d = 3.0, h = 6.01);
        translate([0,0,Z_LF]) cylinder(d = LASER_D + 2*fit, h = 4.01);
        translate([0,0,Z_LF + 4]) cylinder(d = 5.0, h = 20);
        // 3 grani M3 di puntamento a 120° (0° = fronte, accesso dal coperchio; gli altri dai fianchi)
        for (a = [0, 120, 240]) translate([0,0,Z_LF + LASER_L - 2.5]) rotate([0,0,a]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 40);
        // --- asola verticale per bloccare il carrello L2 (vite M3 dal fianco +Y)
        hull() for (dz=[-L2_TRAVEL, L2_TRAVEL]) translate([0, CI - 1, Z_L2 + dz]) rotate([-90,0,0]) cylinder(d = M3_CLR, h = WT + 2);
        hull() for (dz=[-L2_TRAVEL, L2_TRAVEL]) translate([0, CI + WT - 1.5, Z_L2 + dz]) rotate([-90,0,0]) cylinder(d = 6.5, h = 3);
        // --- guida cavo
        j_cut();
        // --- zona libera sopra la scheda (componenti fino a 2.5 mm) tra i ponti
        translate([-6, -CHEEK_Y1, PCB_TOP - 5]) cube([12, 2*CHEEK_Y1, 5 + CABLE_FLOOR - PCB_TOP - 0.01 + 0.0]);
        // --- asole scheda M2 (dado sopra il ponte): ±3 mm lungo Y per centrare il chip sul fascio
        for (s=[-1,1]) hull() for (dy=[-3,3], dx=[0, -BOARD_HOLE_TOL/2]) translate([s*(BOARD_HOLE_SPACING/2 + dx), BOARD_HOLE_OFFSET + dy, PCB_TOP - 1]) cylinder(d = BOARD_SCREW, h = 10);
        // --- fori coperchio (M3 autofilettanti)
        for (p = lid_screws()) translate([CI - 10, p[0], p[1]]) rotate([0,90,0]) cylinder(d = M3_TAP, h = 10.01);
        // --- alleggerimenti piastra (finestre passanti)
        translate([-MOUNT_DIST - 1, -CI + 1.5, 30]) cube([PLATE_T + 2, 2*CI - 3, Z_TOP - 60]);
        for (s=[-1,1]) translate([-MOUNT_DIST - 1, s > 0 ? CI + WT + 2 : -PLATE_W/2 + 3, 50]) cube([PLATE_T + 2, PLATE_W/2 - CI - WT - 5, Z_TOP - 12 - 64]);
        // --- fissaggio al piano: 4 fori M4 passanti con lamatura lato torre
        for (p = mount_holes()) translate([-MOUNT_DIST - 1, p[0], p[1]]) rotate([0,90,0]) {
            cylinder(d = MOUNT_SCREW, h = PLATE_T + 2);
            translate([0,0,PLATE_T + 1 - 3.5]) cylinder(d = MOUNT_CB, h = 20);
        }
    }
}

module carriage() {   // centrato in z = 0
    H = 12;
    difference() {
        translate([-CI + slide, -CI + slide, -H/2]) cube([2*CI - 2*slide, 2*CI - 2*slide, H]);
        lens_seat(0, L2_T_SEAT, 10);
        front_groove(-H/2 - 1, H/2 + 1);
        translate([0, CI - 7, 0]) rotate([-90,0,0]) cylinder(d = M3_TAP, h = 8);   // vite dal fianco +Y
    }
}

module lid() {
    difference() {
        union() {
            translate([CI, -CI - WT, Z_COL]) cube([LID_T, 2*(CI + WT), Z_TOP - Z_COL]);
            // costola: trattiene L1 e L2 (0.2 mm di gioco sul bordo lente)
            translate([L1_D/2 + 0.2, -1.4, Z_COL + 0.5]) cube([CI - L1_D/2 - 0.2 + 0.01, 2.8, Z_L1 + 4 - Z_COL - 0.5]);
        }
        for (p = lid_screws()) translate([CI - 1, p[0], p[1]]) rotate([0,90,0]) {
            cylinder(d = M3_CLR, h = 10);
            translate([0,0,LID_T - 0.5]) cylinder(d = 6.2, h = 5);
        }
        translate([CI - 1, 0, Z_LF + LASER_L - 2.5]) rotate([0,90,0]) cylinder(d = 3.5, h = 10);  // accesso grano anteriore
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
