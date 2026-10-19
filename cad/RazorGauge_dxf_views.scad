include <RazorGauge.scad>
PART = "none";
VIEWSET = "tower";
module lbl(t, s=4) { text(t, size = s, font = "Liberation Sans"); }
module secZ(z) projection(cut = true) translate([0,0,-z]) children();
module secY(y=0) projection(cut = true) multmatrix([[1,0,0,0],[0,0,1,0],[0,1,0,-y],[0,0,0,1]]) children();
module secX(x=0) projection(cut = true) multmatrix([[0,1,0,0],[0,0,1,0],[1,0,0,-x],[0,0,0,1]]) children();
module P() { if (VIEWSET == "tower") tower(); else if (VIEWSET == "lid") lid(); else carriage(); }

if (VIEWSET == "tower") {
    translate([0, 0])   { secY(0) P();  translate([-22, 150]) lbl("SEZ. Y=0 (fronte a destra)"); }
    translate([80, 0])  { secX(0) P();  translate([-28, 150]) lbl("SEZ. X=0 (cavo lungo Y)"); }
    translate([160, 0]) { secY(23) P(); translate([-22, 150]) lbl("SEZ. Y=23 guida J"); }
    zs = [Z_LF + 2, Z_L1, Z_L2, 7, 2.75];
    nm = ["Z=122.2 perno laser", "Z=105.2 sede L1", "Z=24.5 asola L2", "Z=7 guida cavo", "Z=2.75 ponti scheda"];
    for (i = [0:4]) translate([i*75, -80]) { secZ(zs[i]) P(); translate([-28, 34]) lbl(nm[i], 3.2); }
}
if (VIEWSET == "lid")      { secY(0) P(); translate([0, 150]) lbl("COPERCHIO SEZ. Y=0"); translate([40,0]) { secX(10.5) P(); translate([-14,150]) lbl("VISTA FRONTE"); } }
if (VIEWSET == "carriage") { secY(0) P(); translate([-10, 10]) lbl("CARRELLO SEZ. Y=0"); translate([40,0]) { secZ(0) P(); translate([-10,12]) lbl("SEZ. Z=0 sede L2"); } }
