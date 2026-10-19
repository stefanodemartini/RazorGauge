import trimesh, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
parts={'tower':('#555',0),'carriage':('#58a',24.5),'lid':('#999',None)}
meshes={}
for p,(c,z) in parts.items():
    m=trimesh.load('v_'+p+'.stl')
    if p=='carriage': m.apply_translation([0,0,z])
    if p=='lid':
        # undo print orientation: rotate([0,-90,0]) translate([-CI-LID_T,0,0])
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0])); m.apply_translation([12,0,0])
    meshes[p]=(m,c)
fig,axs=plt.subplots(1,3,figsize=(15,10),gridspec_kw={'width_ratios':[1,1,1.2]})
for ax,(n,ix,t) in zip(axs,[((0,1,0),(0,2),'Sez. Y=0 (X avanti-dietro, Z)'),((1,0,0),(1,2),'Sez. X=0 (Y lungo cavo, Z)')]):
    for p,(m,c) in meshes.items():
        s=m.section(plane_origin=(0,0,0),plane_normal=n)
        if s is None: continue
        for e in s.discrete: ax.fill(e[:,ix[0]],e[:,ix[1]],color=c,alpha=.85,ec='k',lw=.4)
    ax.set_aspect('equal'); ax.set_title(t); ax.grid(alpha=.3)
    for z,l in [(0,'chip'),(4.0,'cavo'),(24.5,'L2'),(105.2,'L1'),(120.2,'laser')]:
        ax.axhline(z,color='r',lw=.5,ls='--'); ax.text(ax.get_xlim()[1],z,' '+l,color='r',va='center',fontsize=8)
# zoom zona cavo
ax=axs[2]
for p,(m,c) in meshes.items():
    s=m.section(plane_origin=(0,23,0),plane_normal=(0,1,0))
    if s is None: continue
    for e in s.discrete: ax.fill(e[:,0],e[:,2],color=c,alpha=.85,ec='k',lw=.4)
for d in [0.5,2,3]:
    ax.add_patch(plt.Circle((0,2.5+d/2),d/2,color='orange'))
ax.add_patch(plt.Rectangle((-15,-3.1),30,1.6,color='green',alpha=.6)); ax.add_patch(plt.Rectangle((-1.5,-1.5),3,1.5,color='k'))
ax.set_xlim(-25,20); ax.set_ylim(-22,30); ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_title('Guida cavo a J (sez. Y=23) + scheda')
plt.tight_layout(); plt.savefig('v_sections.png',dpi=85)
