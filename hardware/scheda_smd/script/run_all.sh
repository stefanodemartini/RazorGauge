#!/bin/bash
set -e
cd /home/claude/board_smd
export HOME=/tmp/kh KICAD7_FOOTPRINT_DIR=/usr/share/kicad/footprints
python3 gen_sch.py > /dev/null
python3 gen_pcb.py | tail -2
python3 fix_dsn.py RazorBoard/RazorBoard.dsn
cd RazorBoard && rm -f RazorBoard.ses
timeout 560 xvfb-run -a java -jar /tmp/freerouting.jar -de RazorBoard.dsn -do RazorBoard.ses -mp ${PASSES:-40} > /tmp/fr.log 2>&1 || true
cd ..
python3 import_ses.py RazorBoard/RazorBoard.kicad_pcb RazorBoard/RazorBoard.ses
python3 add_zones.py RazorBoard/RazorBoard.kicad_pcb
grep -E "^\[" RazorBoard/RazorBoard_drc.rpt | grep -v lib_footprint | sort | uniq -c
grep "Found" RazorBoard/RazorBoard_drc.rpt
