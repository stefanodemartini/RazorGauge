# ============================================================================================
# SUPERATO (19/11/2026) — NON USARE.
# Script delle stime core + coating del 18-19/11, fatte quando l'app trattava la linea come corpo
# unico. Dal 19/11 l'app fa questo calcolo da sola (app/Models/LineCore.cs) e i .flp contengono la
# densita' del COMPOUND, non della linea: questo script la legge come densita' di linea e sui file
# convertiti da' risultati sbagliati. Tenuto solo come documentazione delle stime in STATO_PROGETTO.
# ============================================================================================
# Stima 18/11/2026: velocita' di affondamento dei profili esistenti con modello core + coating
# (coating non penetra nella treccia). Densita' del file = densita' del COATING; core = densita'
# apparente (aria compresa) in 3 scenari finche' non arriva il dtex dal fornitore. Vedi STATO_PROGETTO.md.
import json, glob, math, os, sys, csv

G = 9.80665
ROOT = r'C:\Users\Stefano\Documents\FlyLineProfiler\Projects'
OUT = os.path.join(os.environ.get('TEMP', '.'), 'core_sink_nodes.csv')

def kin_visc_fresh(t):
    T = [0,5,10,15,20,25,30,35,40]
    N = [1.7916e-6,1.5182e-6,1.3063e-6,1.1385e-6,1.0034e-6,0.8927e-6,0.8007e-6,0.7234e-6,0.6578e-6]
    if t <= T[0]: return N[0]
    if t >= T[-1]: return N[-1]
    for i in range(8):
        if T[i] <= t <= T[i+1]:
            return N[i] + (N[i+1]-N[i])*(t-T[i])/(T[i+1]-T[i])

def water_rho_fresh(t):
    return (999.842594 + 0.06793952*t - 0.00909529*t**2 + 0.0001001685*t**3
            - 0.000001120083*t**4 + 0.000000006536332*t**5)

def water(salt, t):
    return (1027.0-0.2*t, 1.07*kin_visc_fresh(t)) if salt else (water_rho_fresh(t), kin_visc_fresh(t))

def residual(v, dm, rhoL, rhoW, nu):
    re = max(abs(v)*dm/nu, 1e-12)
    cd = 1.0 + 10.0/re**(2/3)
    return math.pi/4*dm*dm*G*(rhoL-rhoW) - 0.5*cd*abs(v)*v*dm*rhoW

def cyl_speed(salt, t, dmm, rho):
    """Port of SinkingSpeedCalc.CylinderSinkSpeed, returns in/s."""
    rhoL, dm = rho*1000, dmm/1000
    rhoW, nu = water(salt, t)
    lo, hi = (0.0, 3.0) if rhoL >= rhoW else (-3.0, 0.0)
    flo = residual(lo, dm, rhoL, rhoW, nu)
    mid = 0
    for _ in range(100):
        mid = (lo+hi)/2
        f = residual(mid, dm, rhoL, rhoW, nu)
        if abs(f) < 1e-12: break
        if flo*f <= 0: hi = mid
        else: lo, flo = mid, f
    return mid/0.0254

def A(d): return math.pi/4*d*d   # mm²

# Core bulk density scenarios (g/cm3 of the core's own envelope, air included).
# Solid PET 1.38 x braid packing 0.50 / 0.65 / 0.80 -> 0.69 / 0.90 / 1.10
SCEN = {'light': 0.69, 'mid': 0.90, 'heavy': 1.10}

def density_at(d, x):
    zones = d.get('NozzleZones') or []
    noz = d.get('NozzleDefinitions') or []
    base = d.get('SharedDensityGCm3') or (noz[0]['DensityGCm3'] if noz else 0)
    for z in zones:
        if z['StartCm'] <= x <= z['EndCm']:
            r = noz[z['NozzleIndex']]['DensityGCm3']
            if r and abs(r-base) > 0.02: return r, base
    return base, base

def main():
    rows = []
    summary = []
    for p in sorted(glob.glob(os.path.join(ROOT, '**', '*.flp'), recursive=True)):
        d = json.load(open(p, encoding='utf-8-sig'))
        nodes = sorted(d.get('DesignNodes') or [], key=lambda n: n['X'])
        dc = d.get('CoreDiameterMm')
        if not nodes or not dc or d.get('IsCompensatedDerivative'): continue
        salt = bool(d.get('IsSaltWater')); t = d.get('WaterTempC') or 20
        adapt = d.get('ZoneDensityAdaptDiameters', True)
        name = os.path.relpath(p, ROOT)
        pts = []
        for n in nodes:
            rho, base = density_at(d, n['X'])
            D = n['Y']
            if rho != base and adapt and d.get('NozzleZones'):
                D = D*math.sqrt(base/rho)
            pts.append((n['X'], D, rho))
        if not pts[0][2]: continue
        for x, D, rho in pts:
            v_old = cyl_speed(salt, t, D, rho)
            row = {'file': name, 'X_cm': x, 'D_mm': round(D,3), 'core_mm': dc,
                   'core_frac_%': round(100*A(dc)/A(D),1), 'rho_file': round(rho,4),
                   'v_now_ips': round(v_old,3)}
            for k, rc in SCEN.items():
                if dc >= D:
                    row[f'rho_eff_{k}'] = ''; row[f'v_{k}_ips'] = 'core>D'; continue
                reff = (rc*A(dc) + rho*(A(D)-A(dc)))/A(D)
                row[f'rho_eff_{k}'] = round(reff,4)
                row[f'v_{k}_ips'] = round(cyl_speed(salt, t, D, reff),3)
            rows.append(row)

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=';')
        w.writeheader(); w.writerows(rows)

    # compact print: tip node, thinnest node, thickest node per file
    from itertools import groupby
    for fname, grp in groupby(rows, key=lambda r: r['file']):
        g = list(grp)
        picks = {'tip': g[0], 'min': min(g, key=lambda r: r['D_mm']), 'max': max(g, key=lambda r: r['D_mm'])}
        print(f"\n{fname}  core {g[0]['core_mm']} mm  rho {g[0]['rho_file']}")
        seen = set()
        for lab, r in picks.items():
            if id(r) in seen: continue
            seen.add(id(r))
            print(f"  {lab:4} X={r['X_cm']:7.1f} D={r['D_mm']:.3f} core%={r['core_frac_%']:5.1f}  "
                  f"now {r['v_now_ips']:+.3f} | light {r['v_light_ips']} mid {r['v_mid_ips']} heavy {r['v_heavy_ips']}")
    print('\nCSV:', OUT)

if __name__ == '__main__':
    main()
