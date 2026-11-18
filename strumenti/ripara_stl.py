# Pulizia degli STL per i service di stampa (02/11/2026): i booleani lasciano spigoli di pochi micron e triangoli di area ~0,
# che i software dei service (fusione dei vertici a ~0.001 mm) vedono come difetti da riparare.
# Passi: manifold3d simplify(0.001 mm) (fonde i triangoli complanari, toglie i microspigoli), fusione dei vertici a 0.0012 mm,
# rimozione facce nulle/duplicate. Controlli: chiuso, normali coerenti, 0 autointersezioni, 0 spigoli/vertici non-manifold,
# 0 spigoli < 0.001 mm, 0 facce di area < 1e-6 mm2, scostamento massimo dall'originale.
# Uso: python3 ripara_stl.py file1.stl [file2.stl ...]   (sovrascrive i file)
import sys, numpy as np, trimesh, pymeshlab, manifold3d as m3, tempfile, os
def report(f):
    m = trimesh.load(f); el = m.edges_unique_length; a = m.area_faces
    ms = pymeshlab.MeshSet(); ms.load_new_mesh(f)
    ms.compute_selection_by_self_intersections_per_face(); si = ms.current_mesh().selected_face_number(); ms.set_selection_none()
    ms.compute_selection_by_non_manifold_edges_per_face(); ne = ms.current_mesh().selected_face_number(); ms.set_selection_none()
    ms.compute_selection_by_non_manifold_per_vertex(); nv = ms.current_mesh().selected_vertex_number()
    t = ms.get_topological_measures()
    return dict(chiuso=bool(m.is_watertight), normali=bool(m.is_winding_consistent and m.volume > 0), vol_cm3=round(m.volume/1000, 3), facce=len(m.faces),
                autointersezioni=si, nonmanif_spigoli=ne, nonmanif_vertici=nv, buchi=t['number_holes'], corpi=t['connected_components_number'],
                spigoli_sotto_1um=int((el < 1e-3).sum()), facce_area_nulla=int((a < 1e-6).sum()))
def ripara(f):
    t = trimesh.load(f)
    M = m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32))).simplify(0.001)
    mm = M.to_mesh(); o = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=True)
    tmp = tempfile.mktemp(suffix=".stl"); o.export(tmp)
    ms = pymeshlab.MeshSet(); ms.load_new_mesh(tmp)
    ms.meshing_merge_close_vertices(threshold=pymeshlab.PureValue(0.0012)); ms.meshing_remove_duplicate_faces(); ms.meshing_remove_null_faces(); ms.meshing_remove_unreferenced_vertices()
    ms.save_current_mesh(tmp, binary=True)
    r = trimesh.load(tmp)
    d1 = trimesh.proximity.closest_point(r, t.sample(20000))[1].max(); d2 = trimesh.proximity.closest_point(t, r.sample(20000))[1].max()
    r.export(f); os.remove(tmp)
    rep = report(f); rep["scostamento_max_mm"] = round(float(max(d1, d2)), 4)
    ok = rep["chiuso"] and rep["normali"] and rep["corpi"] == 1 and not any(rep[k] for k in ("autointersezioni", "nonmanif_spigoli", "nonmanif_vertici", "buchi", "spigoli_sotto_1um", "facce_area_nulla"))
    return ok, rep
if __name__ == "__main__":
    for f in sys.argv[1:]:
        for _ in range(3):                                   # 03/11/2026: fino a 3 passate (dopo i raccordi da minkowski a volte ne serve una seconda)
            ok, rep = ripara(f)
            if ok: break
        print(("OK " if ok else "!! ") + os.path.basename(f), rep)
