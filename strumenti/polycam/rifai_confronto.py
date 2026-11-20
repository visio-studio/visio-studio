# catena completa del confronto (stessi passi fatti a mano la prima volta): rilievo riscalato, filtro a 1,30 m, pulizie finali
import sys,json,numpy as np
sys.path.insert(0,sys.argv[1]);import piante
from scipy import ndimage
TS=json.load(open('allineamento-scala.json'))
for piano,h1,scans,post_key in (('terra',1.788,['pt','sc'],'terra'),('camere',4.788,['p1','sc'],'camere')):
    z=np.load(f'maschere-{piano}.npz');post=z['post']
    sg=[];alto=[]
    for n in scans:
        o=piante.sez_scan(n,TS,[h1,h1+1.3]);sg+=o[h1];alto+=o[h1+1.3]
    L=piante.raster(sg);es,nu,de=piante.confronto(post,L)
    A=ndimage.binary_dilation(piante.raster(alto),iterations=10)
    lab,n=ndimage.label(de);de=np.isin(lab,[i for i in range(1,n+1) if ((lab==i)&A).sum()>0.6*(lab==i).sum()])
    if piano=='camere':de[:]=False
    else:
        dp=ndimage.distance_transform_edt(~post);d=de&(dp>40);d=ndimage.binary_dilation(d,iterations=3)&de
        lab,n=ndimage.label(d);s=ndimage.sum(d,lab,range(1,n+1));de=np.isin(lab,1+np.flatnonzero(s>=800))
    chiuso=ndimage.binary_closing(post,iterations=60);est=~ndimage.binary_fill_holes(chiuso);est_d=ndimage.binary_dilation(est,iterations=4)
    lab,n=ndimage.label(nu);nu=np.isin(lab,[i for i in range(1,n+1) if not ((lab==i)&est_d).any()]);es=post&~nu
    np.savez_compressed(f'confronto-{piano}.npz',esist=es,nuovi=nu,dem=de,linee=L);print(piano,'nuovi',nu.sum()/1e4,'demoliti',de.sum()/1e4,flush=True)
