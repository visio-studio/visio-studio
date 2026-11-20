# maschere dei muri (1 cm/px) da sezioni orizzontali: progetto (modello) e stato attuale (rilievo allineato)
import json,numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
X0,X1,Z0,Z1,R=4.5,23.0,-9.5,1.5,0.01
W,H=int((X1-X0)/R),int((Z1-Z0)/R)
def raster(segs):
    im=Image.new('L',(W,H),0);d=ImageDraw.Draw(im)
    for a,b,c,e in segs:d.line([((a-X0)/R,(b-Z0)/R),((c-X0)/R,(e-Z0)/R)],fill=255,width=2)
    return np.asarray(im)>0
def campate(L,mn=5,mx=46):
    F=np.zeros_like(L)
    for A,Fv in ((L,F),(L.T,F.T)):
        for i in range(A.shape[0]):
            idx=np.flatnonzero(A[i])
            if len(idx)<2:continue
            g=np.diff(idx);k=np.flatnonzero((g>=mn)&(g<=mx))
            for j in k:Fv[i,idx[j]:idx[j+1]+1]=True
    return F
def pulisci(M,area=300):
    M=ndimage.binary_opening(M,iterations=1);lab,n=ndimage.label(M);s=ndimage.sum(M,lab,range(1,n+1))
    return np.isin(lab,1+np.flatnonzero(s>=area))
def sez_scan(n,T,hs):
    m=json.load(open(f'/home/user/visio-studio/area-ct26/3d/{n}.json'));buf=open(f'/home/user/visio-studio/area-ct26/3d/{m["bin"]}','rb').read()
    A=np.array(T[n]).reshape(4,4);out={h:[] for h in hs}
    for e in m['mesh']:
        q=np.frombuffer(buf,'<u2',e['nv']*3,e['pos']).reshape(-1,3).astype(float);mn=np.array(e['min']);mx=np.array(e['max']);P=mn+q/65535*(mx-mn)
        P=(np.c_[P,np.ones(len(P))]@A.T)[:,:3]
        I=np.frombuffer(buf,'<u2',e['ni'],e['idx']).reshape(-1,3);V=P[I]
        for h in hs:
            y=V[:,:,1]-h;s=np.sign(y);k=~((s[:,0]==s[:,1])&(s[:,1]==s[:,2]))
            for t in V[k]:
                pts=[]
                for a,b in ((0,1),(1,2),(2,0)):
                    ya,yb=t[a,1]-h,t[b,1]-h
                    if ya*yb<0:u=ya/(ya-yb);pts.append(t[a]+(t[b]-t[a])*u)
                if len(pts)==2:out[h].append([pts[0][0],pts[0][2],pts[1][0],pts[1][2]])
    return out
if __name__=='__main__':
    S=json.load(open('sez-modello.json'));T=json.load(open('/home/user/visio-studio/area-ct26/3d/allineamento.json'))
    res={}
    for piano,h1,h2,scans in (('terra','1.2','2',['pt','sc']),('camere','4.78','5.6',['p1','sc'])):
        L1=raster(S[h1]['muri']+S[h1]['arredi']);L2=raster(S[h2]['muri']+S[h2]['arredi'])
        post=pulisci(campate(L1)&ndimage.binary_dilation(campate(L2),iterations=3))
        hh=float(h1);sg={1.2:[],2.0:[]}
        for n in scans:
            o=sez_scan(n,T,[hh,hh+0.9]);sg[1.2]+=o[hh];sg[2.0]+=o[hh+0.9]
        A1=raster(sg[1.2]);A2=raster(sg[2.0])
        ante=pulisci(campate(A1,4,40)&ndimage.binary_dilation(campate(A2,4,40),iterations=4),200)
        np.savez_compressed(f'maschere-{piano}.npz',post=post,ante=ante,linee_post=L1,linee_ante=A1,linee_ante2=A2)
        print(piano,'post m²',post.sum()*R*R,'ante m²',ante.sum()*R*R,'linee rilievo',len(sg[1.2]))

def confronto(post,linee_ante,R=0.01):
    """esistenti = muri di progetto con una linea del rilievo su una faccia; nuovi = il resto;
    demoliti = linee del rilievo lontane dai muri di progetto, ingrossate a 10 cm"""
    dt=ndimage.distance_transform_edt(post)
    larg=ndimage.grey_dilation(dt*2,size=(41,41))*post
    ds=ndimage.distance_transform_edt(~linee_ante)
    esist=post&(ds<=larg+8)
    nuovi=pulisci(post&~esist,400)
    esist=post&~nuovi
    dp=ndimage.distance_transform_edt(~post)
    dem=linee_ante&(dp>15)
    dem=ndimage.binary_dilation(dem,iterations=5)
    lab,n=ndimage.label(dem);s=ndimage.sum(dem,lab,range(1,n+1));dem=np.isin(lab,1+np.flatnonzero(s>=500))
    return esist,nuovi,dem
