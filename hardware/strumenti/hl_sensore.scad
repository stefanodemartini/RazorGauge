include <cable_gauge_v.scad>
PART="none";
color([0.55,0.55,0.58,0.35]) tower();
color([0.55,0.55,0.58,0.25]) translate([0,0,Z_L2]) carriage();
color([1,0.35,0.1]) translate([-12.6, 15.5, 0.2]) rotate([180,0,0]) import("sensor.stl");
color("red") translate([0,0,-12]) cylinder(d=0.8, h=150);          // asse fascio
color("gold") translate([0, 0, CABLE_FLOOR + 1]) rotate([90,0,0]) cylinder(d = 2, h = 70, center = true);
