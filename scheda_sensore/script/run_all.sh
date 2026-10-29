#!/bin/bash
# Rigenera libreria, schema, PCB (piazzamento + Freerouting + piani GND + DRC) e file JLCPCB
set -e; cd "$(dirname "$0")"; export HOME=/tmp/kh
python3 gen_lib.py && python3 gen_sch_s.py && python3 gen_pcb_s.py
cd ../ && rm -f RazorSensor.ses && timeout 300 xvfb-run -a java -jar /tmp/freerouting.jar -de RazorSensor.dsn -do RazorSensor.ses -mp 40 > /dev/null 2>&1 || true
cd script && python3 import_ses.py ../RazorSensor.kicad_pcb ../RazorSensor.ses && python3 add_zones_s.py ../RazorSensor.kicad_pcb && python3 produzione_s.py
