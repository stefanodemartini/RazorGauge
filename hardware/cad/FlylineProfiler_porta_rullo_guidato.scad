// FlylineProfiler + RazorGauge — porta rullo degli spintori GUIDATO, v2 (stelo cilindrico come l'originale)
// Problema dell'originale: forcella appesa a una vite, libera di ruotare e inclinarsi -> rullo di traverso col cavo che scorre.
// v2: lo stelo resta CILINDRICO Ø8 (la molla dell'originale gli sta attorno, come prima). La guida la fa un
// CORPO RETTANGOLARE 16 x 12 x 8 sopra il rullo, che scorre in una sede rettangolare 16.3 x 12.3 del pezzo unico
// (gioco 0.15 per lato, imbocco 7-8 mm su tutta la corsa): la forcella puo solo salire e scendere.
// La molla appoggia sul corpo guida, attorno allo stelo, e spinge contro il cappello della sede.
// Vite M5 x 25 dall'alto: passa nel cappello e nella molla, si avvita nel foro Ø4.2 dello stelo (fine corsa regolabile).
// Rullo: 2 cuscinetti 625 (Ø16 x 5) su perno Ø5, larghezza 10 tra i distanziali.
// Coordinate di stampa: asse del rullo // X, stelo verso +Z, origine al centro del rullo.
$fn = 64;
R_ROLL  = 8;        // rullo Ø16
W_ROLL  = 10;       // larghezza rullo
ARM_T   = 2;        // spessore bracci
BOSS    = 1;        // distanziali Ø8 sui bracci
BOX_X   = 2*(W_ROLL/2 + BOSS + ARM_T);   // 16: larghezza forcella (asse rullo)
BOX_Y   = 12;       // larghezza forcella lungo il cavo
GUIDE0  = 9;        // corpo guida: da 9 a 17 mm sopra il centro del rullo
GUIDE_H = 8;
STEM_D  = 8;        // stelo cilindrico (come l'originale): la molla ci sta attorno
STEM_L  = 10;
M5_TAP  = 4.2;      // foro per la vite M5 (autofilettante nel PA12), per tutto stelo + corpo guida
AXLE    = 5.0;      // perno Ø5

module fork() {
    xo = W_ROLL/2 + BOSS;
    difference() {
        union() {
            for (s = [-1, 1]) {
                hull() {
                    translate([s*(xo + ARM_T/2), 0, 0]) rotate([0, 90, 0]) cylinder(d = BOX_Y, h = ARM_T, center = true);
                    translate([s*(xo + ARM_T/2), 0, GUIDE0 - 0.5]) cube([ARM_T, BOX_Y, 1], center = true);
                }
                translate([s*(W_ROLL/2 + BOSS/2), 0, 0]) rotate([0, 90, 0]) cylinder(d = 8, h = BOSS, center = true);
            }
            translate([-BOX_X/2, -BOX_Y/2, GUIDE0]) cube([BOX_X, BOX_Y, GUIDE_H]);                  // corpo guida
            translate([0, 0, GUIDE0 + GUIDE_H - 0.01]) cylinder(d = STEM_D, h = STEM_L + 0.01);      // stelo cilindrico
        }
        rotate([0, 90, 0]) cylinder(d = AXLE, h = 40, center = true);                               // perno
        translate([0, 0, GUIDE0 + 0.5]) cylinder(d = M5_TAP, h = GUIDE_H + STEM_L);                 // vite M5
        translate([0, 0, GUIDE0 + GUIDE_H + STEM_L - 0.6]) cylinder(d1 = M5_TAP, d2 = M5_TAP + 1.4, h = 0.61);
        translate([0, 0, GUIDE0 + GUIDE_H + STEM_L - 0.5]) difference() { cylinder(d = STEM_D + 1, h = 1); cylinder(d1 = STEM_D, d2 = STEM_D - 1, h = 0.51); }  // smusso stelo
        for (s = [-1, 1]) translate([s*BOX_X/2, 0, GUIDE0 + GUIDE_H]) rotate([0, 45, 0]) cube([0.8, BOX_Y + 1, 0.8], center = true);   // smussi d'imbocco
        for (s = [-1, 1]) translate([0, s*BOX_Y/2, GUIDE0 + GUIDE_H]) rotate([45, 0, 0]) cube([BOX_X + 1, 0.8, 0.8], center = true);
    }
}
fork();
