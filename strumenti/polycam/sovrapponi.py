# immagine di controllo: muri del modello in grigio, muri del rilievo trasformato in rosso
import sys,json,numpy as np
from PIL import Image
sys.path.insert(0,sys.argv[1]);from allinea import wallpts
M=np.load('mod.npy');res=json.load(open(sys.argv[2]));out=[]
for n,y0m,y0s in (('pt',0.0,0.0),('p1',3.58,0.7)):
    S=np.load(n+'.npy');r=res[n];A=np.array(r['A']);b=np.array(r['b'])
    wm=wallpts(M,y0m);ws=wallpts(S,y0s)@A.T+b
    o=np.array([4.5,-9.0]);R=0.025;W,H=int(19/R),int(11/R)
    im=np.full((H,W,3),255,np.uint8)
    for pts,col in ((wm,(150,150,150)),(ws,(220,30,30))):
        ij=np.floor((pts-o)/R).astype(int);k=(ij[:,0]>=0)&(ij[:,1]>=0)&(ij[:,0]<W)&(ij[:,1]<H)
        for dx in (0,1):
            for dy in (0,1):im[np.clip(ij[k,1]+dy,0,H-1),np.clip(ij[k,0]+dx,0,W-1)]=col
    out.append(Image.fromarray(im))
C=Image.new('RGB',(out[0].width,out[0].height*2+10),'black');C.paste(out[0],(0,0));C.paste(out[1],(0,out[0].height+10));C.thumbnail((1400,1400));C.save(sys.argv[3])
