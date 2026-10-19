exec(open('sim_fresnel_metodo_area.py').read().split('for D in')[0])
def area(n,margin=8,fix=False):
    imin=2+np.argmin(n[2:126]); i=imin
    while i>0 and n[i]<0.5: i-=1
    L=i-margin; i=imin
    while i<N-1 and n[i]<0.5: i+=1
    R=i+margin
    if fix:
        out=[n[j] for j in range(2,N-2) if j<L or j>R]; n=n/np.mean(out)
    return np.sum(1-n[L:R+1])*pitch
rng=np.random.default_rng(0)
for D in [0.5,4.0]:
  for fix in [False,True]:
    e=[]
    for c in np.linspace(-0.4,0.4,9):
      p=shadow(D,c)
      for k in [0.97,1.0,1.03]:   # +/-3% energia impulso
        for _ in range(20):
          fr=np.mean([p*k+rng.normal(0,0.005,N) for _ in range(16)],axis=0)
          e.append((area(fr,fix=fix)-D)*1000)
    print(f"D={D} fix={fix}: mean {np.mean(e):+.2f} std {np.std(e):.2f} um, max|err| {np.max(np.abs(e)):.1f}")
