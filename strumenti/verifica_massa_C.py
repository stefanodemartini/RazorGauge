"""Mass of an NC design vs its C file(s): total, AFFTA 30 ft, and the worst local window."""
import json, math, sys, os

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

def mass_between(pcs, a, b):
    """grams between a and b cm (exact frustum on each clipped piece)."""
    g = 0.0
    for x0, x1, d0, d1, rho in pcs:
        lo, hi = max(a, x0), min(b, x1)
        if hi <= lo: continue
        f = lambda x: d0 + (d1 - d0) * (x - x0) / (x1 - x0)
        r1, r2 = f(lo) / 20.0, f(hi) / 20.0  # radius in cm
        g += math.pi * (hi - lo) / 3.0 * (r1 * r1 + r1 * r2 + r2 * r2) * rho
    return g

GR = 15.4323584
def report(nc_path, c_path, window=30.0):
    nc, c = pieces(load(nc_path)), pieces(load(c_path))
    end = min(nc[-1][1], c[-1][1])
    tot_nc, tot_c = mass_between(nc, 0, end), mass_between(c, 0, end)
    h_nc, h_c = mass_between(nc, 0, 914.4), mass_between(c, 0, 914.4)
    worst = (0, 0)
    x = 0.0
    while x + window <= end:
        a, b = mass_between(nc, x, x + window), mass_between(c, x, x + window)
        e = (b - a) / a * 100 if a > 0 else 0
        if abs(e) > abs(worst[1]): worst = (x, e)
        x += 5
    print(f"{os.path.basename(c_path)}")
    print(f"   total  NC {tot_nc*GR:8.1f} gr   C {tot_c*GR:8.1f} gr   diff {(tot_c-tot_nc)*GR:+7.1f} gr ({(tot_c/tot_nc-1)*100:+.2f}%)")
    print(f"   30 ft  NC {h_nc*GR:8.1f} gr   C {h_c*GR:8.1f} gr   diff {(h_c-h_nc)*GR:+7.1f} gr ({(h_c/h_nc-1)*100:+.2f}%)")
    print(f"   worst {window:.0f} cm window: {worst[0]:.0f}-{worst[0]+window:.0f} cm  {worst[1]:+.2f}%")

if __name__ == '__main__':
    report(sys.argv[1], sys.argv[2])
