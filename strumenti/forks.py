import trimesh, numpy as np
T=trimesh.transformations
F0=trimesh.load("/home/claude/fp/rh/5.stl")            # forcella ORIGINALE dell'utente (porta rullo con sede boccola)
def place(zline, d=2.0):
    """forcella sul cavo di diametro d: centro rullo a Y 66.91 + d + 8, Z = zline"""
    m=F0.copy(); m.apply_translation([-177.88,-6.0,-8.0])
    m.apply_transform(T.rotation_matrix(np.pi/2,[0,1,0]))
    m.apply_translation([22.22, 66.91+d+8, zline]); return m
