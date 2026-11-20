# copia nel sito i panorami pronti, con punti e visibilità filtrati su quelli disponibili
import sys,json,os
from PIL import Image
S=sys.argv[1];D='area-ct26/3d/tour'
P=json.load(open(f'{S}/pano/punti.json'));V=json.load(open(f'{S}/pano/hd/visibili.json'))
pronti=[q['id'] for q in P if os.path.exists(f'{S}/pano/hd/{q["id"]}.jpg')]
for i in pronti:
    if not os.path.exists(f'{D}/{i}.jpg') or os.path.getmtime(f'{S}/pano/hd/{i}.jpg')>os.path.getmtime(f'{D}/{i}.jpg'):
        Image.open(f'{S}/pano/hd/{i}.jpg').save(f'{D}/{i}.jpg',quality=86,optimize=True,progressive=True)
json.dump([q for q in P if q['id'] in pronti],open(f'{D}/punti.json','w'),indent=1)
json.dump({k:[x for x in v if x in pronti] for k,v in V.items() if k in pronti},open(f'{D}/visibili.json','w'))
print('pronti',len(pronti),pronti)
