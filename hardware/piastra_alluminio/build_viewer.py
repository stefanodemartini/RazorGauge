import pickle,trimesh,base64
D=pickle.load(open('/tmp/layout.pkl','rb'))
sc=trimesh.Scene()
for k,(v,f,c) in D.items():
    if k=='RB_componenti': continue
    m=trimesh.Trimesh(v,f,process=False); nm=k[2:] if k.startswith('A_') else k
    if k=='RazorBoard': m.visual.face_colors=trimesh.load('/tmp/razorboard_mesh.ply',process=False).visual.face_colors
    sc.add_geometry(m,node_name=nm,geom_name=nm)
O='/mnt/user-data/outputs/RazorGauge/piastra_alluminio/'
sc.export(O+'piastra_assieme.glb')
t=open('/home/claude/viewer/piastra_template.html').read()
open('/home/claude/viewer/Piastra_3D.html','w').write(t.replace('__GLB__',base64.b64encode(open(O+'piastra_assieme.glb','rb').read()).decode()))
print('ok')
