# Smussi di stampa su coperchio e carrello (dopo l'esportazione da OpenSCAD, nei loro sistemi di riferimento):
#  coperchio: perimetro della faccia esterna raccordato R0.5 (03/11/2026; prima smusso 0.6 a gradini) (la faccia interna appoggia sulla colonna: viva)
#  carrello: 4 spigoli paralleli allo scorrimento 0.5 (aiutano nel canale 24 x 24 dagli angoli interni non vivi in MJF),
#            perimetro delle due facce di estremita' 0.3 (invito nel canale)
import trimesh, numpy as np, io, sys
sys.path.insert(0, "/home/claude/fp/v3")
from build_tappo import wedge
def fix(t):
    for dig in (None, 5, 4, 6, 3):                    # None: mesh gia' chiusa cosi' com'e' (03/11: il raccordo da minkowski non va fuso)
        q = t.copy()
        if dig is not None: q.merge_vertices(digits_vertex=dig); q.update_faces(q.nondegenerate_faces()); q.remove_unreferenced_vertices()
        b = io.BytesIO(); q.export(b, file_type="stl"); b.seek(0); r = trimesh.load(b, file_type="stl")
        if r.is_watertight and r.is_volume and len(r.split(only_watertight=False)) == 1: return q
    if t.is_watertight and t.is_volume: print("  (mesh chiusa ma da ripulire: passare ripara_stl.py)"); return t
    raise SystemExit("mesh non chiusa")
def lid(src, dst):
    import shapely.geometry as sg, shapely.ops as so
    m = trimesh.load(src); z1 = m.bounds[1][2]; L, H = 0.6, 0.1
    sec, _ = m.section(plane_origin=[0, 0, z1 - 1.0], plane_normal=[0, 0, 1]).to_2D(to_2D=np.array([[1,0,0,0],[0,1,0,0],[0,0,1,-(z1-1.0)],[0,0,0,1]], dtype=float))
    S = so.unary_union(list(sec.polygons_full)).buffer(0)
    E = so.unary_union([sg.Polygon(g.exterior) for g in getattr(S, "geoms", [S])])     # contorno esterno della faccia (sotto l'incisione)
    Ew = E.buffer(-1.0, 32).buffer(1.0, 32)                                  # senza le parti strette (< 2 mm): restano vive
    narrow = E.difference(Ew)
    keep = so.unary_union([g.buffer(0.3, 16) for g in getattr(narrow, "geoms", [narrow]) if g.area > 0.02]) if not narrow.is_empty else sg.Polygon()
    OUT = E.buffer(0.6, 16)
    holes = so.unary_union([sg.Polygon(r).buffer(1.9, 32) for g in getattr(S, 'geoms', [S]) for r in g.interiors if sg.Polygon(r).area < 15])   # fori viti: parete 1.05 al bordo -> niente smusso attorno
    # 03/11/2026 (Stefano): niente smussi a gradini -> RACCORDO TONDO R0.5 sul perimetro della faccia esterna (sfera fatta scorrere
    # sul contorno, minkowski con manifold3d), stesse esclusioni (fori viti).
    import manifold3d as mf
    R = 0.5
    def ext(poly, za, zb):
        ms = []
        for g in getattr(poly, "geoms", [poly]):
            if g.geom_type == "Polygon" and g.area > 1e-3:
                w = trimesh.creation.extrude_polygon(g, zb - za); w.apply_translation([0, 0, za]); ms.append(w)
        return trimesh.boolean.union(ms) if len(ms) > 1 else ms[0]
    core = ext(E.buffer(-R + 0.02, 32), z1 - 3.0, z1 - R + 0.003)
    rnd = mf.Manifold(mf.Mesh(vert_properties=np.asarray(core.vertices, np.float32), tri_verts=np.asarray(core.faces, np.uint32))).minkowski_sum(mf.Manifold.sphere(R, 48)).to_mesh()
    rnd = trimesh.Trimesh(np.asarray(rnd.vert_properties)[:, :3], np.asarray(rnd.tri_verts), process=False)
    cuts = [trimesh.boolean.difference([ext(OUT.difference(holes), z1 - R - 0.05, z1 + 0.2), rnd])]
    r = fix(trimesh.boolean.difference([m, trimesh.boolean.union(cuts)])); r.export(dst); return m, r
def carriage(src, dst):
    m = trimesh.load(src); (x0, y0, z0), (x1, y1, z1) = m.bounds
    cuts = [wedge("z", (x, y), (sx, sy), 0.5, z0 - 0.1, z1 + 0.1) for x, sx in ((x0, -1), (x1, 1)) for y, sy in ((y0, -1), (y1, 1))]
    for z, sz in ((z0, -1), (z1, 1)):
        cuts += [wedge("x", (y, z), (sy, sz), 0.3, x0 - 0.1, x1 + 0.1) for y, sy in ((y0, -1), (y1, 1))]
        cuts += [wedge("y", (x, z), (sx, sz), 0.3, y0 - 0.1, y1 + 0.1) for x, sx in ((x0, -1), (x1, 1))
                 if not (sx == 1 and sz == 1)]     # spigolo vicino al foro M3 frontale (parete 0.95): resta vivo
    r = fix(trimesh.boolean.difference([m, trimesh.boolean.union(cuts)])); r.export(dst); return m, r
if __name__ == "__main__":
    for f, (a, b) in (("coperchio", lid(sys.argv[1], sys.argv[2])), ("carrello", carriage(sys.argv[3], sys.argv[4]))):
        print(f, "da %.1f a %.1f mm3" % (a.volume, b.volume), "chiuso", b.is_watertight, "ingombro", b.extents.round(2).tolist())
