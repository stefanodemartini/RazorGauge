# English 2D drawings for JLCCNC with full thread specifications (type, size, pitch, class, depth)
import pickle, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from collections import Counter

R = pickle.load(open('/tmp/fori.pkl', 'rb')); H = R['HOLES']; PL = R['PL']
O = '/mnt/user-data/outputs/RazorGauge/piastra_alluminio/cnc/'

SPEC = {'M3': ('M3x0.5-6H', 'Ø2.5'), 'M4': ('M4x0.7-6H', 'Ø3.3')}
COL = {'F': '#1f6fd1', 'B': '#b5179e', 'S': '#d07a14', 'P': '#2e9e44', 'A': '#666666'}
KIND = {'F': 'Tapped hole THRU', 'B': 'Tapped hole in plate EDGE', 'S': 'Countersunk hole',
        'P': 'Plain through hole', 'A': 'Cutout / slot'}


def spec(h, face_cs):
    t = h['tipo']
    if t == 'F':
        s, d = SPEC[h['d']]
        return f"{s} THRU (tap drill {d} thru)"
    if t == 'B':
        s, d = SPEC[h['d']]
        return f"{s}, tap drill {d} x 10 deep, full thread min 8 deep"
    if t == 'S':
        return f"Ø3.4 THRU, 90° countersink Ø6.5 on {face_cs} face (M3 flat head)"
    if t == 'P':
        d = h['d']
        if d.startswith('asola'):
            return 'slot ' + d.split()[1] + ' THRU, plain (no thread)'
        return d + ' THRU, plain (no thread)'
    return h['d'] + ' THRU (see STEP)'


def page(pdf, name, poly, tf, hs, title, xl, yl, face_cs, view_note, edge_note, size, invert=False):
    fig = plt.figure(figsize=(11.7, 16.5))
    # header
    c = Counter((h['d'], h['tipo']) for h in hs if h['tipo'] in 'FB')
    lines = []
    for (d, t), n in sorted(c.items(), key=lambda x: (x[0][1], x[0][0])):
        s, dr = SPEC[d]
        if t == 'F':
            lines.append(f"{n} x {s} THRU  -  metric coarse ISO thread, pitch {s.split('x')[1].split('-')[0]} mm, tolerance 6H, tap drill {dr}")
        else:
            lines.append(f"{n} x {s} in plate EDGE  -  tap drill {dr} x 10 deep, full thread min 8 deep, axis in plate mid-thickness (3.0 from each face), perpendicular to edge")
    cs = sum(1 for h in hs if h['tipo'] == 'S')
    if cs:
        lines.append(f"{cs} x countersunk Ø3.4 THRU, 90° x Ø6.5 on {face_cs} face (for M3 flat head screws) - NOT threaded")
    lines.append("All other holes and slots: plain, no thread, dimensions per STEP.")
    fig.text(0.04, 0.985, f"{name}   |   Al 6061-T6, 6 mm   |   Qty 1   |   Units: mm   |   General tolerance ISO 2768-m   |   Break sharp edges 0.3",
             fontsize=10, weight='bold', va='top')
    fig.text(0.04, 0.965, "THREAD SPECIFICATION\n" + "\n".join(lines), fontsize=9, va='top', color='#1f4e8c',
             bbox=dict(fc='#eef3fa', ec='#1f4e8c', pad=5), family='monospace' if False else None)
    # plan view
    ax = fig.add_axes([0.07, 0.47, 0.88, 0.40])
    for g in getattr(poly, 'geoms', [poly]):
        xs, ys = zip(*[tf(*p) for p in g.exterior.coords]); ax.fill(xs, ys, color='#e3e6ea', ec='k', lw=1)
        for r in g.interiors:
            xs, ys = zip(*[tf(*p) for p in r.coords]); ax.fill(xs, ys, color='white', ec='k', lw=0.8)
    for h in hs:
        x, y = tf(h['u'], h['v']); cc = COL[h['tipo']]
        ax.plot([x], [y], marker='v' if h['tipo'] == 'B' else '+', ms=9 if h['tipo'] == 'B' else 8, color=cc, mew=1.3)
        lab = h['cod']
        if h['tipo'] == 'F': lab += ' ' + SPEC[h['d']][0] + ' THRU'
        if h['tipo'] == 'B': lab += ' ' + SPEC[h['d']][0] + ' EDGE'
        if h['tipo'] == 'S': lab += ' CSK'
        ax.annotate(lab, (x, y), xytext=(4, 4), textcoords='offset points', fontsize=7.5, color=cc, weight='bold')
    for k in 'FBSPA':
        ax.plot([], [], marker='v' if k == 'B' else '+', ls='', color=COL[k], label=KIND[k])
    ax.legend(fontsize=7, loc='lower right', bbox_to_anchor=(1.0, 1.0), ncol=3, framealpha=0.9)
    ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.5); ax.tick_params(labelsize=7)
    ax.set_title(title + '\n' + view_note, fontsize=10, loc='left', pad=26); ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8)
    if invert: ax.invert_yaxis()
    # edge thread detail
    if any(h['tipo'] == 'B' for h in hs):
        ad = fig.add_axes([0.07, 0.355, 0.30, 0.095]); ad.set_aspect('equal'); ad.axis('off')
        ad.fill([0, 20, 20, 0], [0, 0, 6, 6], color='#e3e6ea', ec='k')
        ad.fill([0, 10, 10, 0], [1.75, 1.75, 4.25, 4.25], color='white', ec='#b5179e', lw=1)
        ad.plot([0, 8], [1.5, 1.5], color='#b5179e', lw=0.8, ls='--'); ad.plot([0, 8], [4.5, 4.5], color='#b5179e', lw=0.8, ls='--')
        ad.plot([0, 0], [-1, 7], color='k', lw=2)
        ad.text(10.5, 3, 'drill Ø2.5 x 10\nM3x0.5-6H x 8', fontsize=7, va='center', color='#b5179e')
        ad.text(-0.5, 7.6, 'EDGE THREAD - section (edge on the left)', fontsize=7.5, weight='bold')
        ad.text(-0.5, -2.4, 'axis at 3.0 from each face (t = 6)', fontsize=7)
        ad.set_xlim(-1, 30); ad.set_ylim(-3, 8.5)
        fig.text(0.40, 0.44, edge_note, fontsize=8.5, va='top')
    # table
    at = fig.add_axes([0.03, 0.02, 0.94, 0.32]); at.axis('off')
    rows = []
    for h in hs:
        x, y = tf(h['u'], h['v'])
        rows.append([h['cod'], KIND[h['tipo']], spec(h, face_cs), f"{x:.2f}", f"{y:.2f}"])
    t = at.table(cellText=rows, colLabels=['Code', 'Feature', 'Specification', 'X', 'Y'], loc='upper left',
                 cellLoc='left', colLoc='left', colWidths=[0.06, 0.2, 0.58, 0.08, 0.08])
    t.auto_set_font_size(False); t.set_fontsize(7 if len(rows) <= 24 else 6.4); t.scale(1, 1.25 if len(rows) <= 24 else 1.0)
    for (r, cidx), cell in t.get_celld().items():
        if r == 0: cell.set_text_props(weight='bold')
        elif rows[r - 1][1].startswith('Tapped'): cell.set_text_props(color='#1f4e8c', weight='bold')
    pdf.savefig(fig); plt.close(fig)


def one(fname, *a, **k):
    with PdfPages(O + fname) as pdf:
        page(pdf, *a, **k)


tfP = lambda u, v: (PL['z1'] - u, v - PL['y0'])
one('RG_piastra_verticale.pdf', 'RG_piastra_verticale', R['P'], tfP, [h for h in H if h['lastra'] == 'P'],
    'VERTICAL PLATE  314 x 227 (+ 3 tabs 20 x 6 on bottom edge) x 6', 'X from left edge', 'Y from bottom edge (tabs excluded)',
    'FRONT', 'View from FRONT face (= top face in STEP). Origin: bottom-left corner.',
    'P16-P19: M3 tapped holes in the BOTTOM edge (the edge with the 3 tabs),\nat the X positions in the table. Axis perpendicular to the edge.', None)
tfM = lambda u, v: (v - (-162), R['XPB'] - u)
one('RG_mensola.pdf', 'RG_mensola', R['M'], tfM, [h for h in H if h['lastra'] == 'M'],
    'SHELF  116 x 89 (+ 2 tabs 20 x 6) x 6', 'X along the plate', 'Y from the edge with tabs (tabs at Y<0)',
    'TOP', 'View from TOP. Origin: corner on the tab edge.',
    'M5-M7: M3 tapped holes in the TAB edge (the edge carrying the 2 tabs),\nat the X positions in the table. Axis perpendicular to the edge.', None, invert=True)
tfB = lambda u, v: (v - PL['z0'], u - (-120))
one('RG_base.pdf', 'RG_base', R['B'], tfB, [h for h in H if h['lastra'] == 'B'],
    'BASE  314 x 165 x 6', 'X along the long edge', 'Y from the rear edge',
    'BOTTOM', 'View from TOP. Countersinks B1-B4, B12-B13 are on the BOTTOM face (= bottom face in STEP).',
    '', None)
tfL = lambda u, v: (u - R['LZ'][0], v - PL['y0'])
one('RG_piastrina_presa_IEC.pdf', 'RG_piastrina_presa_IEC', R['L'], tfL, [h for h in H if h['lastra'] == 'L'],
    'IEC INLET PLATE  56 x 41 (+ 1 tab 20 x 6 on bottom edge) x 6', 'X from left edge', 'Y from bottom edge (tab excluded)',
    'FRONT', 'View from outside. Origin: bottom-left corner.',
    'B1-B2: M3 tapped holes in the BOTTOM edge (the edge with the tab),\nat the X positions in the table. Axis perpendicular to the edge.', None)
print('ok')
