#!/usr/bin/env python3
"""Controlla che durante il montaggio nessun pezzo attraversi un altro.

    python3 strumenti/verifica-montaggio.py

Campiona 1201 istanti dell'animazione e confronta gli ingombri di tutte le 105
coppie di pezzi. Le facce che si toccano non contano (EPS): nel modello i pezzi
appoggiano l'uno sull'altro, quindi condividere un piano e corretto.

ATTENZIONE: la funzione esploso() e RANK qui sotto devono restare identiche a
quelle nella pagina. Se si cambia la coreografia in un posto, aggiornare anche
l'altro e rilanciare questo controllo.
"""
import json,sys
d=json.load(open("/Users/matteorotondi/Desktop/visio-studio/madia-3d.json"))
# lat = fase A (allineamento), app = fase B (ingresso sull'asse libero)
def esploso(n,cx):
    if 'pied' in n:    return ([0,0,0],       [0,-.40,0])
    if n=='fondo':     return ([0,0,-.34],    [0, .20,0])
    if 'fianco' in n:  return ([cx*.50,0,0],  [0, .32,0])
    if 'mensola' in n: return ([cx*.40,0,0],  [0, .69,0])
    if 'schiena' in n: return ([0,0,0],       [0,0,-.95])
    if n=='top legno': return ([0,0,.26],     [0, .54,0])
    if 'marmo' in n:   return ([0,0,-.26],    [0, .64,0])
    if 'anta' in n:    return ([cx*.30,0,0],  [0,0, .95])
    return ([0,0,0],[0,0,0])
RANK=lambda n:0 if 'pied' in n else 1 if n=='fondo' else 2 if 'fianco' in n else \
    3 if 'mensola' in n else 4 if 'schiena' in n else 5 if n=='top legno' else 6 if 'marmo' in n else 7
ease=lambda t:1-(1-t)**3
cl=lambda t:max(0.,min(1.,t))
P=[]
for q in d["parts"]:
    v=q["v"]; xs=v[0::3]; ys=v[1::3]; zs=v[2::3]
    L,A=esploso(q["n"],q["cx"])
    P.append({"n":q["n"],"mn":[min(xs),min(ys),min(zs)],"mx":[max(xs),max(ys),max(zs)],"L":L,"A":A,"r":RANK(q["n"])})
passo,durata=.105,.26
EPS=5e-4
peggio={}; n=0
for step in range(1201):
    kA=step/1200.0
    box=[]
    for q in P:
        t=cl((kA-q["r"]*passo)/durata)
        tl=ease(cl(t/0.55)); tv=ease(cl((t-0.45)/0.55))
        o=[q["L"][i]*(1-tl)+q["A"][i]*(1-tv) for i in range(3)]
        box.append((q["n"],[q["mn"][i]+o[i] for i in range(3)],[q["mx"][i]+o[i] for i in range(3)]))
    for i in range(len(box)):
        for j in range(i+1,len(box)):
            ni,ai,bi=box[i]; nj,aj,bj=box[j]
            ov=[min(bi[k],bj[k])-max(ai[k],aj[k]) for k in range(3)]
            if all(o>EPS for o in ov):
                n+=1; key=tuple(sorted((ni,nj)))
                if min(ov)>peggio.get(key,(0,))[0]: peggio[key]=(min(ov),kA)
if not peggio:
    print("NESSUNA COMPENETRAZIONE — 1201 istanti x 105 coppie verificati")
else:
    print("compenetrazioni in %d istanti:" % n)
    for (a,b),(v,kk) in sorted(peggio.items(),key=lambda x:-x[1][0])[:12]:
        print("  %-12s <-> %-12s %6.1f mm  a k=%.3f" % (a,b,v*1000,kk))
