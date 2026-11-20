# lettore minimo dei DAE di Polycam (esportati da Assimp): mesh triangolate, una texture per materiale
import sys, re, numpy as np, xml.etree.ElementTree as ET
NS='{http://www.collada.org/2005/11/COLLADASchema}'
def leggi(path):
    r=ET.parse(path).getroot()
    img={i.get('id'):i.find(NS+'init_from').text for i in r.iter(NS+'image')}
    # effetto -> immagine
    fx={}
    for e in r.iter(NS+'effect'):
        surf={}
        for np_ in e.iter(NS+'newparam'):
            s=np_.find(NS+'surface')
            if s is not None: surf[np_.get('sid')]=s.find(NS+'init_from').text
        samp={}
        for np_ in e.iter(NS+'newparam'):
            s=np_.find(NS+'sampler2D')
            if s is not None: samp[np_.get('sid')]=surf.get(s.find(NS+'source').text)
        t=e.find('.//'+NS+'diffuse/'+NS+'texture')
        fx[e.get('id')]=img.get(samp.get(t.get('texture'))) if t is not None else None
    mat={m.get('id'):fx.get(m.find(NS+'instance_effect').get('url')[1:]) for m in r.iter(NS+'material')}
    geo={}
    for g in r.iter(NS+'geometry'):
        m=g.find(NS+'mesh'); src={}
        for s in m.findall(NS+'source'):
            fa=s.find(NS+'float_array'); st=int(s.find('.//'+NS+'accessor').get('stride'))
            src[s.get('id')]=np.array(fa.text.split(),dtype=np.float64).reshape(-1,st)
        vpos={v.get('id'):v.find(NS+'input').get('source')[1:] for v in m.findall(NS+'vertices')}
        parts=[]
        for pl in list(m.findall(NS+'polylist'))+list(m.findall(NS+'triangles')):
            ins=pl.findall(NS+'input'); no=max(int(i.get('offset')) for i in ins)+1
            p=np.array(pl.find(NS+'p').text.split(),dtype=np.int64).reshape(-1,no)
            vc=pl.find(NS+'vcount')
            if vc is not None: assert set(vc.text.split())<={'3'}
            d={}
            for i in ins:
                s=i.get('source')[1:]; s=vpos.get(s,s); d[i.get('semantic')]=(src[s],int(i.get('offset')))
            P=d['VERTEX'][0][p[:,d['VERTEX'][1]]]; T=d['TEXCOORD'][0][p[:,d['TEXCOORD'][1]]] if 'TEXCOORD' in d else None
            parts.append((pl.get('material'),P,T))
        geo[g.get('id')]=parts
    out=[]
    def walk(n,M):
        mt=n.find(NS+'matrix'); 
        if mt is not None: M=M@np.array(mt.text.split(),dtype=np.float64).reshape(4,4)
        for ig in n.findall(NS+'instance_geometry'):
            bind={im.get('symbol'):im.get('target')[1:] for im in ig.iter(NS+'instance_material')}
            for sym,P,T in geo[ig.get('url')[1:]]:
                Q=(np.c_[P,np.ones(len(P))]@M.T)[:,:3]
                out.append(dict(nome=n.get('name') or '',tex=mat.get(bind.get(sym)),P=Q,T=T))
        for c in n.findall(NS+'node'): walk(c,M)
    for vs in r.iter(NS+'visual_scene'):
        for n in vs.findall(NS+'node'): walk(n,np.eye(4))
    return out
if __name__=='__main__':
    for f in sys.argv[1:]:
        ms=leggi(f); print('==',f)
        A=np.vstack([m['P'] for m in ms]); print(' tot tri',len(A)//3,'min',A.min(0).round(2),'max',A.max(0).round(2))
        for m in ms: print('  ',m['nome'],m['tex'],len(m['P'])//3,m['P'].min(0).round(2),m['P'].max(0).round(2))
