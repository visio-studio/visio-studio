# facce perse nell'esportazione da SketchUp: buchi rettangolari nei mobili (si vede l'interno nero). Si richiudono i
# contorni aperti piani fino a N lati, solo dove nello stesso piano non c'è già una faccia
import bpy,bmesh,math
from mathutils import Vector
def chiudi(sc,lati=4,log=print):
    tot=0
    dg=bpy.context.evaluated_depsgraph_get()
    for ob in [o for o in sc.objects if o.type=='MESH' and o.name!='linee']:
        me=ob.data
        if len(me.polygons)<4:continue
        bm=bmesh.new();bm.from_mesh(me)
        prima=set(bm.faces)
        bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.0008)
        bd=[e for e in bm.edges if e.is_boundary]
        if not bd:bm.free();continue
        r=bmesh.ops.holes_fill(bm,edges=bd,sides=lati)
        nuove=[f for f in r['faces']]
        Mw=ob.matrix_world;via=[]
        for f in nuove:
            f.normal_update();n=(Mw.to_3x3()@f.normal).normalized();c=Mw@f.calc_center_median();A=f.calc_area()
            ax=max(abs(n.x),abs(n.y),abs(n.z))
            pv=[Mw@v.co for v in f.verts];piano=max(abs((p-c).dot(n)) for p in pv)
            if ax<0.999 or A<0.004 or piano>0.001:via.append(f);continue
            # già coperta da una faccia nello stesso piano?
            cop=False
            for s in (1,-1):
                h,l,nn,*_=sc.ray_cast(dg,c+n*0.003*s,-n*s,distance=0.006)
                if h:cop=True;break
            if cop:via.append(f);continue
            # materiale dei vicini più grandi
            vic=[g for e in f.edges for g in e.link_faces if g is not f and g in prima]
            if vic:f.material_index=max(vic,key=lambda g:g.calc_area()).material_index
        bmesh.ops.delete(bm,geom=via,context='FACES')
        k=len(nuove)-len(via)
        if k:bm.to_mesh(me);tot+=k
        bm.free()
    log('facce richiuse',tot)
    return tot

# scritte 3D di SketchUp (etichette dei mobili) che nel render si vedono come lettere in rilievo
ETICHETTE={'anta tecnic','appenderia cappo','cappotti','carr estr','estr','ANT','CASS','ASSE  STIRO','CESTONI  PANNI','LAV ASC','PANNI SPORCHI','ribalta','ribalta#1'}
def etichette(sc,log=print):
    via=[o for o in sc.objects if o.name.split('.')[0] in ETICHETTE]
    for o in via:bpy.data.objects.remove(o,do_unlink=True)
    log('etichette tolte',len(via))

# scala del piano terra: ogni gradino è un blocco con la faccia di sopra rovesciata e triangolata male (triangoli
# sovrapposti = pedate nere, buchi = si vede il cielo). Si rifà la pedata: un poligono pulito per gradino, verso l'alto,
# nella pietra del pavimento
def scala(sc,log=print):
    import collections
    from mathutils.geometry import convex_hull_2d
    ob=bpy.data.objects.get('Gruppo#15')
    if not ob:return
    me=ob.data;M=ob.matrix_world;Mi=M.inverted()
    mat=bpy.data.materials.get('Material_119')
    if mat.name not in [s.material.name for s in ob.material_slots if s.material]:me.materials.append(mat)
    mi=[s.material.name if s.material else '' for s in ob.material_slots].index(mat.name)
    bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table()
    G=collections.defaultdict(list)
    for f in bm.faces:
        c=M@f.calc_center_median();n=(M.to_3x3()@f.normal).normalized()
        if 12.2<c.x<13.545 and -3.4<-c.y<-0.85 and 0.65<c.z<1.5 and n.z<-0.99:G[round(c.z,3)].append(f)
    via=[];nuove=0
    for h,fs in sorted(G.items()):
        pts=[(M@v.co) for f in fs for v in f.verts];pts=[p for p in pts if p.x<13.545]
        p2=[(p.x,p.y) for p in pts];idx=convex_hull_2d(p2)
        if len(idx)<3:continue
        vs=[bm.verts.new(Mi@Vector((p2[i][0],p2[i][1],h+0.0005))) for i in idx]
        f=bm.faces.new(vs);f.normal_update()
        if (M.to_3x3()@f.normal).z<0:f.normal_flip()
        f.material_index=mi;via+=fs;nuove+=1
    bmesh.ops.delete(bm,geom=list(set(via)),context='FACES');bm.to_mesh(me);bm.free()
    log('pedate rifatte',nuove)
