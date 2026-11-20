# punti campionati per area dalle scansioni già convertite (stesse coordinate del visore)
import json,sys,numpy as np
def punti(base,n,dens=100):
    m=json.load(open(f'{base}/{n}.json'));buf=open(f'{base}/{m["bin"]}','rb').read();out=[]
    rng=np.random.default_rng(1)
    for e in m['mesh']:
        q=np.frombuffer(buf,'<u2',e['nv']*3,e['pos']).reshape(-1,3).astype(float)
        mn=np.array(e['min']);mx=np.array(e['max']);P=mn+q/65535*(mx-mn)
        I=np.frombuffer(buf,'<u2',e['ni'],e['idx']).reshape(-1,3)
        A,B,C=P[I[:,0]],P[I[:,1]],P[I[:,2]];ar=np.linalg.norm(np.cross(B-A,C-A),axis=1)/2
        k=rng.poisson(ar*dens)
        idx=np.repeat(np.arange(len(I)),k);r1=rng.random(len(idx));r2=rng.random(len(idx));f=r1+r2>1;r1[f]=1-r1[f];r2[f]=1-r2[f]
        out.append(A[idx]+(B[idx]-A[idx])*r1[:,None]+(C[idx]-A[idx])*r2[:,None])
    return np.vstack(out)
if __name__=='__main__':
    for n in sys.argv[2:]:
        p=punti(sys.argv[1],n);np.save(f'{n}.npy',p.astype(np.float32));print(n,len(p),p.min(0).round(2),p.max(0).round(2))
