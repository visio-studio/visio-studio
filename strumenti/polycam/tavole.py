# disegni delle piante (PNG a 250 px/m) orientati come le piante del preventivo (modello ruotato di 180°)
import json,sys,numpy as np
from PIL import Image,ImageDraw,ImageOps
from scipy import ndimage
sys.path.insert(0,sys.argv[1]);import piante
OUT=sys.argv[2];S=250   # px per metro
X0,X1,Z0,Z1=7.0,22.6,-8.45,0.55   # ritaglio comune ai due piani, coordinate del modello
W,H=int((X1-X0)*S),int((Z1-Z0)*S)
def maschera(m):  # maschera a 1 cm del sistema piante -> ritaglio a S px/m
    i0,i1=int(round((X0-piante.X0)/piante.R)),int(round((X1-piante.X0)/piante.R));j0,j1=int(round((Z0-piante.Z0)/piante.R)),int(round((Z1-piante.Z0)/piante.R))
    return np.asarray(Image.fromarray((m[j0:j1,i0:i1]*255).astype(np.uint8)).resize((W,H),Image.NEAREST))>127
def sfondo(f,alpha):  # vista dall'alto a 100 px/m (X 4.5..23, Z -9.5..1.5) ritagliata, in grigio chiaro
    im=Image.open(f).convert('L');x0,y0=int((X0-4.5)*100),int((Z0+9.5)*100);im=im.crop((x0,y0,x0+int((X1-X0)*100),y0+int((Z1-Z0)*100))).resize((W,H),Image.BILINEAR)
    a=np.asarray(im).astype(float);return 255-(255-a)*alpha
def linee(segs,col,w,base):
    d=ImageDraw.Draw(base)
    for a,b,c,e in segs:d.line([((a-X0)*S,(b-Z0)*S),((c-X0)*S,(e-Z0)*S)],fill=col,width=w)
def fine(im,nome):ImageOps.flip(ImageOps.mirror(im)).save(f'{OUT}/{nome}.png',optimize=True)
T=json.load(open('/home/user/visio-studio/area-ct26/3d/allineamento.json'))
info={}
for piano,h,scans in (('terra',1.788,['pt','sc']),('camere',4.788,['p1','sc'])):
    m=np.load(f'maschere-{piano}.npz');c=np.load(f'confronto-{piano}.npz')
    # ante operam: solo rilievo, misure vere
    g=sfondo(f'../o-ril-{piano}.png',0.28);im=Image.fromarray(np.stack([g]*3,-1).astype(np.uint8))
    sg=[];[sg.extend(piante.sez_scan(n,T,[h])[h]) for n in scans];linee(sg,(15,15,15),6,im);fine(im,f'ante-{piano}')
    A=np.array(sg);xs=np.r_[A[:,0],A[:,2]];zs=np.r_[A[:,1],A[:,3]];x0,x1=np.percentile(xs,[0.3,99.7]);z0,z1=np.percentile(zs,[0.3,99.7])
    info[piano+'_ante']=dict(larg=round(x1-x0,2),prof=round(z1-z0,2),bbox=[x0,x1,z0,z1])
    # post operam: muri del modello pieni, arredi in grigio chiaro
    post=maschera(m['post']);g=sfondo(f'../o-mod-{piano}.png',0.32);im=Image.fromarray(np.stack([g]*3,-1).astype(np.uint8))
    SM=json.load(open('sez-modello.json'))[str(h)];linee(SM['muri']+SM['arredi'],(60,60,60),3,im)
    a=np.asarray(im).copy();a[post]=(25,25,25);im=Image.fromarray(a);fine(im,f'post-{piano}')
    ys,xs=np.nonzero(post);info[piano]=dict(larg=round((xs.max()-xs.min())/S,2),prof=round((ys.max()-ys.min())/S,2),bbox=[X0+xs.min()/S,X0+xs.max()/S,Z0+ys.min()/S,Z0+ys.max()/S])
    # confronto: esistenti grigio, demoliti giallo, nuovi rosso
    es,nu,de,li=(maschera(c[k]) for k in ('esist','nuovi','dem','linee'))
    a=np.full((H,W,3),255,np.uint8);a[li]=(185,195,215);a[es]=(95,95,95);a[de]=(235,180,0);a[nu]=(210,35,35)
    fine(Image.fromarray(a),f'confronto-{piano}')
json.dump(dict(info=info,ritaglio=[X0,X1,Z0,Z1],S=S),open(f'{OUT}/info.json','w'));print(info)
