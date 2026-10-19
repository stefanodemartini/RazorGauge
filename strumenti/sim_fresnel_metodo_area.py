import numpy as np
from scipy.special import fresnel
lam=650e-6; z=3.5; pitch=0.0635; N=128; EDGE=0.25
def edge_field(x):  # knife edge, lit for x>0 ; complex amplitude
    v=x*np.sqrt(2/(lam*z)); S,C=fresnel(v)
    return ((0.5+C)+1j*(0.5+S))/(1+1j)
def shadow(D,c0=0.0):
    x=np.linspace(-4.1,4.1,40001)
    a=c0-D/2; b=c0+D/2
    # opaque strip [a,b]: field = 1 - (field through slit) ; slit = edge(x-a)-edge(x-b)
    slit=edge_field(x-a)-edge_field(x-b)
    I=np.abs(1-slit)**2
    # integrate over pixels (pixel width 63.5, aperture ~ full)
    pix=np.zeros(N)
    for i in range(N):
        xc=(i-63.5)*pitch; m=(x>=xc-pitch/2)&(x<xc+pitch/2); pix[i]=I[m].mean()
    return pix
def measure(n):
    imin=2+np.argmin(n[2:126]); i=imin
    while i>0 and n[i]<EDGE: i-=1
    xl=i+(n[i]-EDGE)/(n[i]-n[i+1]); i=imin
    while i<N-1 and n[i]<EDGE: i+=1
    xr=(i-1)+(EDGE-n[i-1])/(n[i]-n[i-1])
    return (xr-xl)*pitch
for D in [0.5,1.0,2.0,3.0,4.0]:
    errs=[ (measure(shadow(D,c))-D)*1000 for c in np.linspace(-0.5,0.5,11)]
    print(f"D={D}: err um mean {np.mean(errs):+.1f} spread {np.ptp(errs):.1f}")
print("--- area method")
def area(n,margin=8):
    imin=2+np.argmin(n[2:126]); i=imin
    while i>0 and n[i]<0.5: i-=1
    L=max(0,i-margin); i=imin
    while i<N-1 and n[i]<0.5: i+=1
    R=min(N-1,i+margin)
    return np.sum(1-n[L:R+1])*pitch
for D in [0.5,1.0,2.0,3.0,4.0]:
    for noise in [0,0.01]:
        rng=np.random.default_rng(1)
        errs=[ (area(shadow(D,c)+rng.normal(0,noise,N))-D)*1000 for c in np.linspace(-0.5,0.5,11)]
        print(f"D={D} noise={noise}: err um mean {np.mean(errs):+.1f} spread {np.ptp(errs):.1f}")
