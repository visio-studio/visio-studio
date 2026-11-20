# panorami 360 equirettangolari del modello con Cycles: blender --python / python con bpy
# uso: python render360.py modello.glb uscita_dir larghezza campioni id1,id2,...
import sys,math,json,time,bpy
from mathutils import Vector
glb,OUT,LARG,CAMP,IDS=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),sys.argv[5].split(',')
T,C,OC=0.0,3.58,1.55
PUNTI=json.load(open(sys.argv[6]))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
sc=bpy.context.scene
# facce gemelle di SketchUp: fronte col materiale vero e retro col bianco predefinito nello stesso punto, rivolte in
# versi opposti. In Cycles si fanno ombra a vicenda (pavimenti e mobili neri): si tolgono i retri bianchi dove dall'altra
# parte c'è un materiale vero
import bmesh,numpy as np
DEF={m.name for m in bpy.data.materials if m.name=='Material_28'}
tolte=0
for ob in [o for o in sc.objects if o.type=='MESH']:
    me=ob.data;n=len(me.polygons)
    if n==0 or not ob.material_slots:continue
    if me.has_custom_normals:
        with bpy.context.temp_override(object=ob,active_object=ob,selected_objects=[ob]):bpy.ops.mesh.customdata_custom_splitnormals_clear()
    N=np.empty(n*3);me.polygons.foreach_get('normal',N);N=N.reshape(-1,3);Cc=np.empty(n*3);me.polygons.foreach_get('center',Cc);Cc=Cc.reshape(-1,3)
    M3=np.array(ob.matrix_world.to_3x3());Mw=np.array(ob.matrix_world)
    Nw=N@M3.T;Nw/=np.linalg.norm(Nw,axis=1,keepdims=True)+1e-12;Cw=Cc@Mw[:3,:3].T+Mw[:3,3]
    MI=np.empty(n,np.int64);me.polygons.foreach_get('material_index',MI);AR=np.empty(n);me.polygons.foreach_get('area',AR);AR*=abs(np.linalg.det(M3))**(2/3)
    slot=np.array([1 if (s.material and s.material.name in DEF) else 0 for s in ob.material_slots]);isdef=slot[np.clip(MI,0,len(slot)-1)]==1
    ax=np.argmax(np.abs(Nw),1);ok=np.abs(Nw[np.arange(n),ax])>0.999
    sg=np.sign(Nw[np.arange(n),ax]).astype(int);pl=np.round(Cw[np.arange(n),ax]*500).astype(np.int64)
    key=ax*10**9+pl
    via=[];fatti=set()
    for k in np.unique(key[ok&isdef]):
        sel=ok&(key==k)
        for s_ in (1,-1):
            d=sel&isdef&(sg==s_);o=sel&~isdef&(sg==-s_)
            if d.any() and o.any():via+=list(np.flatnonzero(d));fatti.add(int(k))
    # orizzontali con materiali veri sui due lati: fino a 1,80 m sopra ogni pavimento si guarda dall'alto, più su è soffitto
    for k in np.unique(key[ok&(ax==2)]):
        if int(k) in fatti:continue
        sel=ok&(key==k)&(ax==2)
        if not ((sg[sel]==1).any() and (sg[sel]==-1).any()):continue
        au=AR[sel&(sg==1)].sum();ad=AR[sel&(sg==-1)].sum()
        if abs(au-ad)>0.03*max(au,ad):d=sel&(sg==(1 if au>ad else -1))   # il lato difettoso copre anche i buchi: ha più area
        else:
            z=Cw[sel][0,2];liv=0.588 if z<3.4 else 3.588;sopra=(z-liv)<1.8
            d=sel&(sg==(-1 if sopra else 1))
        via+=list(np.flatnonzero(d))
    if via:
        bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.faces[i] for i in set(via)],context='FACES');bm.to_mesh(me);bm.free();tolte+=len(set(via))
    for p_ in me.polygons:p_.use_smooth=False
print('retri bianchi tolti',tolte,flush=True)
# da coordinate del modello (x, y su, z) a Blender (x, -z, y)
B=lambda x,y,z:Vector((x,-z,y))
# soffitto del piano camere (il modello non ha il tetto)
mn=Vector((1e9,1e9,1e9));mx=-mn
for o in sc.objects:
    if o.type=='MESH':
        for c in o.bound_box:
            w=o.matrix_world@Vector(c);mn=Vector(map(min,mn,w));mx=Vector(map(max,mx,w))
bpy.ops.mesh.primitive_plane_add(size=1,location=((mn.x+mx.x)/2,(mn.y+mx.y)/2,mx.z+0.01));p=bpy.context.object;p.scale=(mx.x-mn.x+2,mx.y-mn.y+2,1)
m=bpy.data.materials.new('soffitto');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.92,0.9,0.86,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=0.9;p.data.materials.append(m)
# materiali: niente specchi perfetti dove non servono, pareti opache
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    for n in mat.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED':
            r=n.inputs['Roughness'];met=n.inputs['Metallic']
            if not r.is_linked and r.default_value<0.25 and n.inputs['Transmission Weight'].default_value<0.5:r.default_value=0.35
            if not met.is_linked:met.default_value=min(met.default_value,0.3)
# strisce LED: luce calda vera (gole, nicchie, mobili)
led=bpy.data.materials.new('led');led.use_nodes=True;nt=led.node_tree;nt.nodes.clear()
em=nt.nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=(1.0,0.72,0.42,1);em.inputs['Strength'].default_value=18
out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],out.inputs[0])
nled=0
for o in sc.objects:
    if o.type=='MESH' and 'led' in o.name.lower():
        for sl in o.material_slots:sl.material=led
        nled+=1
print('oggetti LED',nled,flush=True)
# cielo e sole
w=bpy.data.worlds.new('mondo');sc.world=w;w.use_nodes=True;bg=w.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(0.75,0.85,1.0,1);bg.inputs['Strength'].default_value=1.0
sole=bpy.data.lights.new('sole','SUN');sole.energy=3.0;sole.angle=math.radians(2);sole.color=(1,0.95,0.88)
so=bpy.data.objects.new('sole',sole);sc.collection.objects.link(so);so.rotation_euler=(math.radians(50),0,math.radians(35))
# luce calda dal soffitto in ogni stanza (come gole LED e faretti)
for q in PUNTI:
    l=bpy.data.lights.new('l_'+q['id'],'AREA');l.shape='RECTANGLE';l.size=1.6;l.size_y=1.6;l.energy=140;l.color=(1.0,0.82,0.62)
    o=bpy.data.objects.new('l_'+q['id'],l);sc.collection.objects.link(o);o.location=B(q['x'],q['y']+2.45,q['z'])
# camera panoramica
cd=bpy.data.cameras.new('pano');cd.type='PANO';cd.panorama_type='EQUIRECTANGULAR';cd.clip_start=0.05
cam=bpy.data.objects.new('pano',cd);sc.collection.objects.link(cam);sc.camera=cam
sc.render.engine='CYCLES';cy=sc.cycles;cy.device='CPU';cy.samples=CAMP;cy.use_denoising=True;cy.denoiser='OPENIMAGEDENOISE';cy.max_bounces=6;cy.diffuse_bounces=4;cy.glossy_bounces=3;cy.transmission_bounces=6;cy.use_adaptive_sampling=True
sc.render.resolution_x=LARG;sc.render.resolution_y=LARG//2;sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - High Contrast';sc.view_settings.exposure=-0.35
if '--clay' in sys.argv:
    clay=bpy.data.materials.new('clay');sc.view_layers[0].material_override=clay
sc.render.image_settings.file_format='JPEG';sc.render.image_settings.quality=88
# quali punti si vedono fra loro (stesso piano, nessun ostacolo fra gli occhi): per i cerchi del tour
dg=bpy.context.evaluated_depsgraph_get();vis={}
for q in PUNTI:
    vis[q['id']]=[]
    for r in PUNTI:
        if r is q or r['p']!=q['p']:continue
        a_=B(q['x'],q['y']+OC,q['z']);b_=B(r['x'],r['y']+1.0,r['z']);d_=b_-a_;L=d_.length
        hit,loc,*_=sc.ray_cast(dg,a_,d_.normalized(),distance=L-0.05)
        if not hit:vis[q['id']].append(r['id'])
json.dump(vis,open(f'{OUT}/visibili.json','w'));print('visibili',vis,flush=True)
for q in PUNTI:
    if q['id'] not in IDS:continue
    cam.location=B(q['x'],q['y']+OC,q['z'])
    d=B(q['tx'],0,q['tz'])-B(q['x'],0,q['z']);th=math.atan2(-d.x,d.y)
    cam.rotation_euler=(math.radians(90),0,th)
    sc.render.filepath=f"{OUT}/{q['id']}.jpg";t0=time.time();bpy.ops.render.render(write_still=True);print('FATTO',q['id'],round(time.time()-t0),'s',flush=True)
