# allineamento in pianta rilievo -> modello: immagini dei muri (celle con punti sia in basso sia in alto),
# ricerca della rotazione (anche specchiata) con correlazione FFT, poi rifinitura ICP 2D sui punti dei muri
import sys,json,numpy as np
from scipy import ndimage,signal
from scipy.spatial import cKDTree
R=0.05
def muri(P,y0):
    y=P[:,1]-y0;s=(y>0.05)&(y<2.5);P=P[s];y=y[s]
    xz=P[:,[0,2]];lo=xz[y<0.7];hi=xz[y>1.7]
    return lo,hi
def img(lo,hi,o,shape):
    a=np.zeros(shape,bool);b=np.zeros(shape,bool)
    for pts,arr in ((lo,a),(hi,b)):
        ij=np.floor((pts-o)/R).astype(int);k=(ij[:,0]>=0)&(ij[:,1]>=0)&(ij[:,0]<shape[0])&(ij[:,1]<shape[1]);arr[ij[k,0],ij[k,1]]=True
    w=ndimage.binary_dilation(a,iterations=1)&ndimage.binary_dilation(b,iterations=1)
    return w
def rot(th,mir):
    c,s=np.cos(th),np.sin(th);Rm=np.array([[c,-s],[s,c]]);
    return Rm@np.diag([-1,1]) if mir else Rm
def wallpts(P,y0):
    lo,hi=muri(P,y0);o=np.minimum(lo.min(0),hi.min(0))-1;sh=tuple((np.maximum(lo.max(0),hi.max(0))-o)/R+3)
    sh=tuple(int(v) for v in sh);w=img(lo,hi,o,sh);ij=np.argwhere(w);return o+(ij+0.5)*R
def allinea(S,y0s,Mp,y0m,area=None):
    ws=wallpts(S,y0s);wm=wallpts(Mp,y0m)
    if area is not None:wm=wm[(wm[:,0]>area[0])&(wm[:,0]<area[2])&(wm[:,1]>area[1])&(wm[:,1]<area[3])]
    om=wm.min(0)-3;shm=tuple(int(v) for v in (wm.max(0)-om)/R+60)
    Im=np.zeros(shm,np.float32);ij=np.floor((wm-om)/R).astype(int);Im[ij[:,0],ij[:,1]]=1
    Im=ndimage.gaussian_filter(Im,1.2)
    best=(-1,)
    cs=ws.mean(0)
    for mir in (False,True):
        for deg in range(0,360,2):
            q=(ws-cs)@rot(np.radians(deg),mir).T
            oq=q.min(0);shq=tuple(int(v) for v in (q.max(0)-oq)/R+2);Iq=np.zeros(shq,np.float32)
            ij=np.floor((q-oq)/R).astype(int);Iq[ij[:,0],ij[:,1]]=1
            c=signal.fftconvolve(Im,Iq[::-1,::-1],mode='valid') if all(a>=b for a,b in zip(Im.shape,Iq.shape)) else None
            if c is None:continue
            k=np.unravel_index(np.argmax(c),c.shape);sc=c[k]/len(ws)
            if sc>best[0]:best=(sc,deg,mir,om+np.array(k)*R-oq)
    sc,deg,mir,t=best
    Rm=rot(np.radians(deg),mir);t=t  # q = (ws-cs)Rm^T ; mondo = q + t
    # ICP 2D fine
    tree=cKDTree(wm)
    A=Rm.copy();b=t-cs@Rm.T
    for it in range(40):
        q=ws@A.T+b;d,i=tree.query(q);k=d<0.25
        if k.sum()<20:break
        X=ws[k];Y=wm[i[k]];mx=X.mean(0);my=Y.mean(0);H=(X-mx).T@(Y-my)
        U,_,Vt=np.linalg.svd(H);D=np.diag([1,np.sign(np.linalg.det(Vt.T@U.T))])
        Rr=Vt.T@D@U.T
        if mir:  # mantiene la specchiatura: risolve sui punti specchiati
            Xm=X@np.diag([-1,1]);mxm=Xm.mean(0);H=(Xm-mxm).T@(Y-my);U,_,Vt=np.linalg.svd(H);D=np.diag([1,np.sign(np.linalg.det(Vt.T@U.T))]);Rr=(Vt.T@D@U.T)@np.diag([-1,1]);mx=X.mean(0)
        A=Rr;b=my-mx@A.T
    q=ws@A.T+b;d,_=tree.query(q)
    return dict(score=float(sc),deg=deg,mir=mir,A=A.tolist(),b=b.tolist(),entro5cm=float((d<0.05).mean()),entro15cm=float((d<0.15).mean()),n=len(ws))
if __name__=='__main__':
    M=np.load('mod.npy');res={}
    for n,y0m in (('pt',0.0),('p1',3.58)):
        S=np.load(n+'.npy');r=allinea(S,0.0,M,y0m);res[n]=r;print(n,{k:(v if k not in('A',) else np.round(v,3).tolist()) for k,v in r.items()})
    json.dump(res,open('allinea.json','w'))
