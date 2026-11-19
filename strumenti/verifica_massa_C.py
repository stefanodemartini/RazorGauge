"""Mass of an NC design vs its C file(s): total, AFFTA 30 ft, and the worst local window.
Core-aware since 19/11/2026 (densities are the compound, the core is inside)."""
import json, math, sys, os

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

def load(p):
    return json.load(open(p, encoding='utf-8-sig'))

def pieces(j):
    """(x0, x1, d0, d1, rho) for every node-to-node piece, density from SegmentMetadata or shared."""
    nodes = sorted(((n['X'], n['Y']) for n in j['DesignNodes']), key=lambda t: t[0])
    meta = j.get('SegmentMetadata') or []
    shared = j.get('SharedDensityGCm3') or 0
    use_shared = j.get('UseSharedDensity', True)
    out = []
    for (x0, d0), (x1, d1) in zip(nodes, nodes[1:]):
        if x1 <= x0: continue
        mid = (x0 + x1) / 2
        rho = shared if use_shared else 0
        if not use_shared or rho <= 0:
            m = next((m for m in meta if m['StartCm'] - 1e-6 <= mid <= m['EndCm'] + 1e-6), None)
            rho = m['SpecWeight'] if m else shared
        out.append((x0, x1, d0, d1, rho))
    return out

def mass_between(pcs, a, b, core=None):
    """grams between a and b cm (exact frustum on each clipped piece, core inside if given)."""
    g = 0.0
    for x0, x1, d0, d1, rho in pcs:
        lo, hi = max(a, x0), min(b, x1)
        if hi <= lo: continue
        f = lambda x: d0 + (d1 - d0) * (x - x0) / (x1 - x0)
        r1, r2 = f(lo) / 20.0, f(hi) / 20.0  # radius in cm
        g += math.pi * (hi - lo) / 3.0 * (r1 * r1 + r1 * r2 + r2 * r2) * rho
        g += core_correction_g(core, f(lo), f(hi), hi - lo, rho)
    return g

GR = 15.4323584
def report(nc_path, c_path, window=30.0):
    jn, jc = load(nc_path), load(c_path)
    nc, c = pieces(jn), pieces(jc)
    kn, kc = core_of(jn), core_of(jc)
    def mb(pcs, a, b): return mass_between(pcs, a, b, kn if pcs is nc else kc)
    end = min(nc[-1][1], c[-1][1])
    tot_nc, tot_c = mb(nc, 0, end), mb(c, 0, end)
    h_nc, h_c = mb(nc, 0, 914.4), mb(c, 0, 914.4)
    worst = (0, 0)
    x = 0.0
    while x + window <= end:
        a, b = mb(nc, x, x + window), mb(c, x, x + window)
        e = (b - a) / a * 100 if a > 0 else 0
        if abs(e) > abs(worst[1]): worst = (x, e)
        x += 5
    print(f"{os.path.basename(c_path)}   core NC {kn}  C {kc}")
    print(f"   total  NC {tot_nc*GR:8.1f} gr   C {tot_c*GR:8.1f} gr   diff {(tot_c-tot_nc)*GR:+7.1f} gr ({(tot_c/tot_nc-1)*100:+.2f}%)")
    print(f"   30 ft  NC {h_nc*GR:8.1f} gr   C {h_c*GR:8.1f} gr   diff {(h_c-h_nc)*GR:+7.1f} gr ({(h_c/h_nc-1)*100:+.2f}%)")
    print(f"   worst {window:.0f} cm window: {worst[0]:.0f}-{worst[0]+window:.0f} cm  {worst[1]:+.2f}%")

if __name__ == '__main__':
    report(sys.argv[1], sys.argv[2])
