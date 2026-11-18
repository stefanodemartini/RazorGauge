# Riempie le zone esistenti e scrive il report DRC (senza aggiungere vie: per le modifiche dopo add_zones_s.py)
import sys, pcbnew
path = sys.argv[1]; board = pcbnew.LoadBoard(path)
pcbnew.ZONE_FILLER(board).Fill(board.Zones()); board.BuildConnectivity(); pcbnew.SaveBoard(path, board)
rep = path.replace(".kicad_pcb", "_drc.rpt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True); print("report DRC:", rep)
