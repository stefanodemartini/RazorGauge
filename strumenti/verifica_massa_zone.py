"""Faithful replica of MainWindow.ApplyZoneDensities(adaptDiameters: true) + ProjectSegment.MassG,
on a real NC geometry with a synthetic zone whose edges fall mid-segment."""
import json, math, sys

GR = 15.4323584
EPS = 1e-6

def frustum_g(d0, d1, L, rho):
    r1, r2 = d0 / 20.0, d1 / 20.0
    return math.pi * L / 3.0 * (r1 * r1 + r1 * r2 + r2 * r2) * rho

def run(path, zones, label):
    j = json.load(open(path, encoding='utf-8-sig'))
    base = j['NozzleDefinitions'][0]['DensityGCm3'] or j['SharedDensityGCm3']
    nodes = sorted(((n['X'], n['Y']) for n in j['DesignNodes']))
    segs = [(a[0], b[0], a[1], b[1]) for a, b in zip(nodes, nodes[1:]) if b[0] > a[0]]
    lo, hi = segs[0][0], segs[-1][1]

    def hard(x):
        z = next((z for z in zones if z[0] <= x < z[1]), None)
        return z[2] if z else base
    def factor_for(r): return math.sqrt(base / max(r, 0.94))
    def factor_at(x):
        cl = [z for z in zones if z[0] - EPS <= x <= z[1] + EPS]
        if not cl: return 1.0
        return sum(factor_for(z[2]) for z in cl) / len(cl)
    def orig(x):
        s = next((s for s in segs if s[0] - EPS <= x <= s[1] + EPS), segs[-1])
        t = min(max((x - s[0]) / (s[1] - s[0]), 0), 1)
        return s[2] + t * (s[3] - s[2])

    xs = sorted({x for s in segs for x in s[:2]} |
                {e for z in zones for e in z[:2] if lo + EPS < e < hi - EPS})
    res = {x: orig(x) * factor_at(x) for x in xs}

    tot_base = tot_real = tot_shown = 0.0
    print(f"--- {label}  (base ρ {base:.3f})")
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
