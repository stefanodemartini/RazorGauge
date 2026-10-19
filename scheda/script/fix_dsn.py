import re, sys
p = sys.argv[1]; t = open(p).read()
PWR = ["+24V_IN", "+24V_F", "+24V", "+5V_BUCK", "+5V", "+5V_EXT", "M_VIN", "S_VIN", "GND"]
S3 = ["+3V3_M", "+3V3_S", "LASER_P", "LASER_SEL", "LASER_N"]
m = re.search(r'\(class kicad_default ""(.*?)\(circuit', t, re.S)
names = m.group(1).split()
keep = [n for n in names if n not in PWR + S3]
t = t[:m.start(1)] + " " + " ".join(keep) + "\n      " + t[m.end(1):]
t = t.replace("(class Power\n", "(class Power " + " ".join(PWR) + "\n", 1)
t = t.replace("(class Supply3V3\n", "(class Supply3V3 " + " ".join(S3) + "\n", 1)
open(p, "w").write(t)
print("classi DSN aggiornate:", len(keep), "default,", len(PWR), "power,", len(S3), "3v3")
