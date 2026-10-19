// FlylineProfiler V3 - piastra senza il supporto del comparatore (passo 1 integrazione RazorGauge)
// Rimossi: anello del comparatore, il suo foro nella piastra e la flangia circolare.
// Ricostruita la piastra piana (3 mm) nella stessa sagoma rettangolare, con i 4 fori Ø3 originali.
// Tutto il resto (supporto encoder, rulli guida, finestra, appoggio centrale) e invariato.
$fn = 64;
SRC = "FlylineProfiler_V3_1_originale.stl";
Y_CUT = 119;                 // sopra gli appoggi dei rulli (che arrivano a Y 117.8)
Y_TOP = 177.9; Z_MIN = 3.6; Z_MAX = 55.6; T = 3; R = 2.5;
HOLES = [[126.80, 6.55], [126.80, 52.54], [174.85, 6.53], [174.85, 52.53]];
union() {
    difference() {
        import(SRC);
        translate([-1, Y_CUT, -5]) cube([40, 70, 100]);
    }
    difference() {
        hull() {
            translate([0, Y_CUT - 1, Z_MIN]) cube([T, 1, Z_MAX - Z_MIN]);
            for (z = [Z_MIN + R, Z_MAX - R]) translate([0, Y_TOP - R, z]) rotate([0, 90, 0]) cylinder(r = R, h = T);
        }
        for (h = HOLES) translate([-1, h[0], h[1]]) rotate([0, 90, 0]) cylinder(d = 3.0, h = T + 2);
    }
}
