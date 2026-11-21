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
