"""Faithful replica of MainWindow.ApplyZoneDensities(adaptDiameters: true) + ProjectSegment.MassG,
on a real NC geometry with a synthetic zone whose edges fall mid-segment.
Core-aware since 19/11/2026 (densities are the compound, the core is inside)."""
import json, math, sys

# ── Core + coating (19/11/2026) ─────────────────────────────────────────────────────────────
# Since 19/11 every density in a .flp is the COMPOUND's and the line is core + coating
# (app/Models/LineCore.cs). Core: the file's CoreDiameterMm, its density from CoreDensityGCm3 or
# from the catalogue (copy of app/Models/CoreCatalog.cs: g/m over the nominal section).
CATALOG = {'Polyester 12 lb': (0.60, 0.29), 'Polyester 17 lb': (0.72, 0.43),
           'Polyester 20 lb': (0.82, 0.57), 'Polyester 25 lb': (0.90, 0.61),
           'Polyester 30 lb': (1.00, 0.80)}

def core_of(j):
    """(diameter mm, density g/cm3) of the file's core, or None: same rule as LineCore.FromProject."""
    ct = (j.get('CoreType') or '').strip()
    cat = next((v for k, v in CATALOG.items() if ct.startswith(k + ' ')), None)
    d = j.get('CoreDiameterMm') or (cat[0] if cat else None)
    rho = j.get('CoreDensityGCm3') or (cat[1] / (math.pi / 4 * cat[0] ** 2) if cat else None)
    return (d, rho) if d and rho else None

def core_correction_g(core, d0, d1, L, rho):
    """Mass to add to volume x compound for a piece L cm long: (rho_core - rho) x core section x L."""
    if not core or L <= 0 or rho <= 0: return 0.0
    dc = min(core[0], min(d0, d1))
    return (core[1] - rho) * math.pi / 4 * dc * dc / 100.0 * L

GR = 15.4323584
EPS = 1e-6

CORE = None   # set per file in run()

def frustum_g(d0, d1, L, rho):
    r1, r2 = d0 / 20.0, d1 / 20.0
    return math.pi * L / 3.0 * (r1 * r1 + r1 * r2 + r2 * r2) * rho + core_correction_g(CORE, d0, d1, L, rho)

def run(path, zones, label):
    global CORE
    j = json.load(open(path, encoding='utf-8-sig'))
    CORE = core_of(j)
    base = j['NozzleDefinitions'][0]['DensityGCm3'] or j['SharedDensityGCm3']
    nodes = sorted(((n['X'], n['Y']) for n in j['DesignNodes']))
    segs = [(a[0], b[0], a[1], b[1]) for a, b in zip(nodes, nodes[1:]) if b[0] > a[0]]
    lo, hi = segs[0][0], segs[-1][1]

    def hard(x):
        z = next((z for z in zones if z[0] <= x < z[1]), None)
        return z[2] if z else base
    def factor_for(r, d):
        # same final mass per length, core inside (MainWindow.ApplyZoneDensities since 19/11)
        r = max(r, 0.94)
        if not CORE or d <= 0: return math.sqrt(base / r)
        dc, rc = CORE; ac = math.pi / 4 * dc * dc
        m = base * (math.pi / 4 * d * d) + (rc - base) * min(ac, math.pi / 4 * d * d)   # g/cm3 x mm2
        a = (m - (rc - r) * ac) / r
        return math.sqrt(a * 4 / math.pi) / d if a > 0 else math.sqrt(base / r)
    def factor_at(x):
        cl = [z for z in zones if z[0] - EPS <= x <= z[1] + EPS]
        if not cl: return 1.0
        return sum(factor_for(z[2], orig(x)) for z in cl) / len(cl)
    def orig(x):
        s = next((s for s in segs if s[0] - EPS <= x <= s[1] + EPS), segs[-1])
        t = min(max((x - s[0]) / (s[1] - s[0]), 0), 1)
        return s[2] + t * (s[3] - s[2])

    xs = sorted({x for s in segs for x in s[:2]} |
                {e for z in zones for e in z[:2] if lo + EPS < e < hi - EPS})
    res = {x: orig(x) * factor_at(x) for x in xs}

    tot_base = tot_real = tot_shown = 0.0
    print(f"--- {label}  (base ρ {base:.3f}, core {CORE})")
    print(f"{'segment cm':>16} {'base g':>8} {'real g':>8} {'shown g':>8}  real-base  shown-real")
    for s in segs:
        loc = [x for x in xs if s[0] - EPS <= x <= s[1] + EPS]
        m_real, dens_slices = 0.0, []
        for a, b in zip(loc, loc[1:]):
            if b - a <= EPS: continue
            rho = max(hard((a + b) / 2), 0.94)
            m_real += frustum_g(res[a], res[b], b - a, rho)
            n = max(1, math.ceil(b - a))
            dens_slices += [rho] * n
        m_base = frustum_g(s[2], s[3], s[1] - s[0], base)
        m_shown = frustum_g(s[2], s[3], s[1] - s[0], sum(dens_slices) / len(dens_slices))  # VolumeCm3 × EffectiveSpecWeight
        tot_base += m_base; tot_real += m_real; tot_shown += m_shown
        if abs(m_real - m_base) > 1e-4 or abs(m_shown - m_real) > 1e-4:
            print(f"{s[0]:7.0f}-{s[1]:<7.0f} {m_base:8.3f} {m_real:8.3f} {m_shown:8.3f}  {(m_real/m_base-1)*100:+7.2f}%  {(m_shown/m_real-1)*100:+7.2f}%")
    print(f"{'TOTAL':>16} {tot_base*GR:7.1f}gr {tot_real*GR:7.1f}gr {tot_shown*GR:7.1f}gr  "
          f"{(tot_real/tot_base-1)*100:+7.2f}%  {(tot_shown/tot_real-1)*100:+7.2f}%")

if __name__ == '__main__':
    p = sys.argv[1]
    run(p, [(500.0, 1200.0, 1.10)], "zone 500-1200 cm, ρ 1.10 (edges mid-taper)")
    run(p, [(300.0, 980.0, 1.10)], "zone 300-980 cm, ρ 1.10 (edges ON nodes)")
    run(p, [(302.0, 1200.0, 1.10)], "zone 302-1200 cm, ρ 1.10 (start 2 cm after a node)")
