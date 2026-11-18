# Converte un SVG di un layer esportato da kicad-cli in geometria shapely (coordinate scheda in mm)
import svgelements as se, shapely.geometry as sg, shapely.ops as so
K = 25.4 / 96
def layer(path, skip_edge=True):
    svg = se.SVG.parse(path, reify=True); polys = []
    for e in svg.elements():
        if isinstance(e, se.Text) or not isinstance(e, se.Shape): continue
        if e.values.get("opacity") == "0": continue
        sw = float(e.stroke_width or 0) * K; fill = e.fill is not None and e.fill.value is not None and float(e.values.get("fill-opacity", 1)) > 0
        p = se.Path(e)
        for sp in p.as_subpaths():
            sp = se.Path(sp); L = sp.length(error=1e-3)
            n = max(2, int(L / 0.05)); pts = [(q.x * K, q.y * K) for q in (sp.point(i / n) for i in range(n + 1))]
            if fill and len(pts) >= 3: polys.append(sg.Polygon(pts).buffer(0))
            if sw > 0: polys.append(sg.LineString(pts).buffer(sw / 2, 8) if len(pts) > 1 else sg.Point(pts[0]).buffer(sw / 2, 8))
    return so.unary_union(polys)
