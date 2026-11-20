# DAE Polycam -> polycam.json + polycam.bin (stesso formato di project1/3d): posizioni e uv quantizzati a 16 bit, indici a 16 bit, texture ridotte
# Uso: python3 strumenti/polycam/converti.py scansione.dae cartella/3d nome [lato_texture]
# (lo zip di Polycam in DAE va scompattato prima: il .dae cerca le texture in textures/ accanto a sé)
import sys, os, json, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__)); from dae import leggi
dae, outdir, pref = sys.argv[1], sys.argv[2], sys.argv[3]; lato=int(sys.argv[4]) if len(sys.argv)>4 else 2048
os.makedirs(outdir, exist_ok=True); base=os.path.dirname(dae)
ms=leggi(dae); A=np.vstack([m['P'] for m in ms])
# appoggio a terra: y minima del pavimento ~ percentile basso
y0=np.percentile(A[:,1],0.5); cx=(A[:,0].min()+A[:,0].max())/2; cz=(A[:,2].min()+A[:,2].max())/2
texs=[]; meta=[]; buf=bytearray()
def al(): 
    while len(buf)%4: buf.append(0)
for m in ms:
    if m['tex'] not in texs: texs.append(m['tex'])
    ti=texs.index(m['tex'])
    P=m['P']-[cx,y0,cz]; T=m['T'][:,:2].copy(); T[:,1]=1-T[:,1]
    # deduplica vertici (pos+uv)
    key=np.c_[np.round(P,4),np.round(T,5)]
    uq,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
    # spezza in blocchi < 65536 vertici
    tri=inv.reshape(-1,3); i=0
    while i<len(tri):
        j=min(len(tri),i+40000)
        sub=tri[i:j]; u,ri=np.unique(sub,return_inverse=True)
        while len(u)>65535: j=i+(j-i)//2; sub=tri[i:j]; u,ri=np.unique(sub,return_inverse=True)
        V=uq[u]; p=V[:,:3]; t=np.clip(V[:,3:],0,1)
        mn=p.min(0); mx=p.max(0); q=np.round((p-mn)/np.maximum(mx-mn,1e-9)*65535).astype('<u2')
        e=dict(tex=f'{pref}{ti}.jpg',min=mn.tolist(),max=mx.tolist(),nv=len(u),ni=int(sub.size))
        al(); e['pos']=len(buf); buf+=q.tobytes()
        al(); e['uv']=len(buf); buf+=np.round(t*65535).astype('<u2').tobytes()
        al(); e['idx']=len(buf); buf+=ri.astype('<u2').tobytes()
        meta.append(e); i=j
for ti,t in enumerate(texs):
    im=Image.open(os.path.join(base,t)).convert('RGB'); im.thumbnail((lato,lato),Image.LANCZOS); im.save(os.path.join(outdir,f'{pref}{ti}.jpg'),quality=82,optimize=True,progressive=True)
open(os.path.join(outdir,f'{pref}.bin'),'wb').write(buf)
B=np.vstack([m['P'] for m in ms])-[cx,y0,cz]
json.dump(dict(versione=1,bin=f'{pref}.bin',min=B.min(0).round(3).tolist(),max=B.max(0).round(3).tolist(),mesh=meta),open(os.path.join(outdir,f'{pref}.json'),'w'))
print(pref,len(meta),'blocchi',len(buf)//1024,'KB','bbox',B.min(0).round(2),B.max(0).round(2))
