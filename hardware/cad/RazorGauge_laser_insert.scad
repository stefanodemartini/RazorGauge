// RazorGauge - inserto di riparazione della sede laser (torre stampata il 4/10/2026)
// Nella torre stampata il foro Ø9 del fascio di L1 ha asportato la battuta Ø3 e il perno Ø4.3
// della sede laser (Z 117.7 - 125.2). L'inserto si infila DA SOTTO (dal canale, a coperchio tolto)
// nel foro Ø9 fino alla battuta contro il foro Ø5 e si incolla (cianoacrilato o epossidica).
// Ricrea esattamente la sede originale: battuta Ø3 sotto la punta del laser, perno Ø4.3, invito Ø5.
// Uso: openscad -o RazorGauge_laser_insert.stl RazorGauge_laser_insert.scad
$fn = 96;
OD   = 8.7;    // foro nella torre Ø9 nominale (MJF spesso 8.8-8.9): gioco per la colla
H    = 7.5;    // da Z 117.7 (fondo del solaio) a Z 125.2 (scalino verso il Ø5)
LIP  = 2.5;    // spessore della battuta (Z 117.7 - 120.2)
PIV  = 4.0;    // altezza del perno Ø4.3 (Z 120.2 - 124.2)
fit  = 0.15;

difference() {
    cylinder(d = OD, h = H);
    translate([0, 0, -0.01]) cylinder(d = 3.0, h = LIP + 0.02);                 // passaggio fascio / battuta
    translate([0, 0, LIP]) cylinder(d = 4.0 + 2 * fit, h = PIV + 0.01);         // perno Ø4.3: punta del laser
    translate([0, 0, LIP + PIV]) cylinder(d = 5.0, h = H);                       // invito Ø5 (come la torre)
    translate([0, 0, H - 0.6]) cylinder(d1 = 5.0, d2 = 6.2, h = 0.61);           // smusso d'ingresso
    translate([0, 0, H - 0.5]) difference() { cylinder(d = OD + 1, h = 0.51); cylinder(d1 = OD, d2 = OD - 1, h = 0.51); }  // smusso esterno in alto (entra per primo)
}
