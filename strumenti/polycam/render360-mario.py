# Progetto Mario: panorami 360 equirettangolari del modello con Cycles (GPU OptiX se c'è).
# uso: blender -b --factory-startup --python render360-mario.py -- modello.glb stanze.json uscita_dir larghezza campioni [id1,id2|tutti] [--clay]
#   modello.glb = finito.glb (finiture-mario.mjs, senza compressione meshopt: Blender non la legge)
#   stanze.json = [{"id":..,"n":..,"x":..,"z":..}, ...] in metri del modello (x, z come nella pianta); il punto di vista
#   si sposta da solo nel punto libero più vicino (niente mobili sotto, almeno 45 cm dalle pareti), lo sguardo iniziale
#   va verso la vista più lunga. Scrive punti.json, visibili.json e un JPEG per stanza.
import sys,math,json,time,os,bpy
from mathutils import Vector
A=sys.argv[sys.argv.index('--')+1:]
glb,STZ,OUT,LARG,CAMP=A[0],A[1],A[2],int(A[3]),int(A[4]);IDS=A[5].split(',') if len(A)>5 and not A[5].startswith('--') else ['tutti']
CLAY='--clay' in A;os.makedirs(OUT,exist_ok=True)
log=lambda *a:print(*a,flush=True)
PAV=0.37;OC=1.55          # pavimento del modello (y) e altezza degli occhi
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
sc=bpy.context.scene
B=lambda x,y,z:Vector((x,-z,y))      # modello (x, y su, z) -> Blender (x, -z, y)
# luci V-Ray di SketchUp: rettangoli e forni finti, nel render sarebbero lastre grigie
via=[o for o in sc.objects if 'v-ray' in o.name.lower() or 'definitivo' in o.name.lower()]
for o in via:bpy.data.objects.remove(o,do_unlink=True)
log('oggetti tolti (luci V-Ray, scritte)',len(via))
for o in sc.objects:
    if o.type=='MESH':
        for p_ in o.data.polygons:p_.use_smooth=False
# --- materiali ---
nb=0;nv=0
for mat in list(bpy.data.materials):
    nt=mat.node_tree
    if not nt:continue
    b=nt.nodes.get('Principled BSDF');out=next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'),None)
    if not b or not out:continue
    al=b.inputs['Alpha'];r=b.inputs['Roughness'];met=b.inputs['Metallic']
    # niente specchi perfetti dove non servono
    if not r.is_linked and r.default_value<0.2:r.default_value=0.2
    if not met.is_linked:met.default_value=min(met.default_value,0.3)
    # vetri (trasparenza forte): lastra sottile, trasparente colorata più un riflesso, niente rifrazione
    if not al.is_linked and al.default_value<0.6:   # anche le finestre «Janela» (grigio al 50 %)
        c=b.inputs['Base Color'].default_value
        for l_ in list(out.inputs['Surface'].links):nt.links.remove(l_)
        tr=nt.nodes.new('ShaderNodeBsdfTransparent');tr.inputs['Color'].default_value=(0.55+0.45*c[0],0.55+0.45*c[1],0.55+0.45*c[2],1)
        gl=nt.nodes.new('ShaderNodeBsdfGlossy');gl.inputs['Roughness'].default_value=0.03
        fr=nt.nodes.new('ShaderNodeFresnel');fr.inputs['IOR'].default_value=1.5
        mx=nt.nodes.new('ShaderNodeMixShader');nt.links.new(fr.outputs[0],mx.inputs[0]);nt.links.new(tr.outputs[0],mx.inputs[1]);nt.links.new(gl.outputs[0],mx.inputs[2])
        nt.links.new(mx.outputs[0],out.inputs['Surface']);nv+=1
    # facce gemelle di SketchUp (fronte e retro nello stesso piano, versi opposti): finiture-mario.mjs le ha messe in
    # materiali a faccia singola. In Cycles il retro si rende trasparente: ogni lato mostra solo il suo materiale e le
    # due facce non si fanno ombra a vicenda
    if mat.use_backface_culling:
        s=out.inputs['Surface'].links[0].from_socket
        for l_ in list(out.inputs['Surface'].links):nt.links.remove(l_)
        g=nt.nodes.new('ShaderNodeNewGeometry');t=nt.nodes.new('ShaderNodeBsdfTransparent');m=nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(g.outputs['Backfacing'],m.inputs[0]);nt.links.new(s,m.inputs[1]);nt.links.new(t.outputs[0],m.inputs[2]);nt.links.new(m.outputs[0],out.inputs['Surface'])
        nb+=1
log('materiali: vetri',nv,'a faccia singola',nb)
# --- ingombri e terreno ---
ms=[o for o in sc.objects if o.type=='MESH'];mn=Vector((1e9,)*3);mx=-mn
for o in ms:
    for c in o.bound_box:w=o.matrix_world@Vector(c);mn=Vector(map(min,mn,w));mx=Vector(map(max,mx,w))
log('ingombro',tuple(round(v,2) for v in mn),tuple(round(v,2) for v in mx))
# terreno lontano sotto la casa (un piano alto: dalle finestre si vede un fondo chiaro, non il vuoto)
bpy.ops.mesh.primitive_plane_add(size=1,location=((mn.x+mx.x)/2,(mn.y+mx.y)/2,PAV-9));p=bpy.context.object;p.scale=(400,400,1)
mt=bpy.data.materials.new('terreno');mt.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.32,0.31,0.27,1);mt.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=1;p.data.materials.append(mt)
dg=bpy.context.evaluated_depsgraph_get()
def ray(o,d,L=50):
    h,loc,nor,*_=sc.ray_cast(dg,o,d,distance=L);return (h,loc,nor)
# soffitto dove manca: nel modello alcune stanze sono aperte in alto. Celle di 10 cm alla quota del soffitto (3,07 m,
# la più frequente) dove si è dentro casa (a 1,9 m i muri chiudono in tutte e otto le direzioni entro 12 m) e sopra
# non c'è niente. I terrazzi restano all'aperto: da lì almeno una direzione esce
QS=float(os.environ.get('QSOFF',3.07))+0.005   # 5 mm sopra: niente sovrapposizioni con i soffitti veri
P8=[Vector((math.cos(a),math.sin(a),0)) for a in [i*math.pi/4+0.1 for i in range(8)]]
vs=[];fs=[];G=0.1
NX,NY=int((mx.x-mn.x)/G)+1,int((mx.y-mn.y)/G)+1;den=set()
for i in range(NX):
    for j in range(NY):
        o=Vector((mn.x+(i+.5)*G,mn.y+(j+.5)*G,1.9+PAV))
        if ray(o,Vector((0,0,1)),5)[0]:continue
        if all(ray(o,d,12)[0] for d in P8):den.add((i,j))
# allargato di 30 cm: copre anche le teste dei muri più basse del soffitto (altrimenti lungo i muri si vede il cielo)
R=3;tet={(i+a,j+b) for i,j in den for a in range(-R,R+1) for b in range(-R,R+1)}
for i,j in tet:
    x,y=mn.x+i*G,mn.y+j*G;k=len(vs);vs+=[(x,y,QS),(x+G,y,QS),(x+G,y+G,QS),(x,y+G,QS)];fs.append((k,k+3,k+2,k+1))
if fs:
    me=bpy.data.meshes.new('soffitto');me.from_pydata(vs,[],fs);me.validate()
    import bmesh;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.001);bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new('soffitto',me);sc.collection.objects.link(ob)
    ms_=bpy.data.materials.new('soffitto');b_=ms_.node_tree.nodes['Principled BSDF'];b_.inputs['Base Color'].default_value=(0.87,0.83,0.77,1);b_.inputs['Roughness'].default_value=0.9;me.materials.append(ms_)
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
log('soffitto aggiunto, m²',round(len(fs)*G*G,1))
# --- punti di vista ---
DIR=[Vector((math.cos(a),math.sin(a),0)) for a in [i*math.pi/12 for i in range(24)]]
def libero(x,z):
    # True se dall'altezza degli occhi si vede il pavimento sotto e nulla è più vicino di 45 cm fino a 1,9 m
    e=B(x,PAV+OC,z);h,loc,nor=ray(e,Vector((0,0,-1)),3)
    if not h or abs(nor.z)<0.9 or abs(loc.z-PAV)>0.06:return None
    for hh in (0.35,0.9,1.5,1.9):
        o=B(x,PAV+hh,z)
        for d in DIR:
            if ray(o,d,0.45)[0]:return None
    return loc.z
def sposta(x,z):
    best=None
    for i in range(-16,17):
        for j in range(-16,17):
            dx,dz=i*0.1,j*0.1;dd=math.hypot(dx,dz)
            if dd>1.6 or (best and dd>=best[0]):continue
            if libero(x+dx,z+dz) is not None:best=(dd,x+dx,z+dz)
    return best
PUNTI=[]
for s in json.load(open(STZ)):
    b=sposta(s['x'],s['z'])
    if not b:log('nessun punto libero per',s['n']);continue
    x,z=round(b[1],2),round(b[2],2);e=B(x,PAV+OC,z)
    # sguardo iniziale: la direzione con la vista più lunga
    lun=[(ray(e,d)[1]-e).length if ray(e,d)[0] else 50 for d in DIR];k=max(range(len(DIR)),key=lambda i:lun[i]);d=DIR[k]
    hs,ls,_=ray(e,Vector((0,0,1)),6);soff=round(ls.z,2) if hs else None
    PUNTI.append(dict(id=s['id'],n=s['n'],p='casa',x=x,z=z,y=PAV,tx=round(x+d.x*3,2),tz=round(z-d.y*3,2),soffitto=soff,spost=round(b[0],2),esterno=bool(s.get('esterno'))))
    log('punto',PUNTI[-1])
json.dump(PUNTI,open(f'{OUT}/punti.json','w'),indent=1,ensure_ascii=False)
vis={}
for q in PUNTI:
    vis[q['id']]=[]
    for r in PUNTI:
        if r is q:continue
        a_=B(q['x'],PAV+OC,q['z']);b_=B(r['x'],PAV+1.0,r['z']);d_=b_-a_
        if not ray(a_,d_.normalized(),d_.length-0.05)[0]:vis[q['id']].append(r['id'])
json.dump(vis,open(f'{OUT}/visibili.json','w'));log('visibili',vis)
# --- luce: cielo, sole, luce calda dal soffitto nelle stanze ---
w=bpy.data.worlds.new('mondo');sc.world=w;nt=w.node_tree;bg=nt.nodes['Background']
sky=nt.nodes.new('ShaderNodeTexSky')
try:sky.sky_type='MULTIPLE_SCATTERING'
except Exception:
    try:sky.sky_type='NISHITA'
    except Exception:pass
EL,AZ=math.radians(float(os.environ.get('SOLE_EL',22))),math.radians(float(os.environ.get('SOLE_AZ',150)))
try:sky.sun_elevation=EL;sky.sun_rotation=AZ;sky.sun_disc=False;sky.altitude=60
except Exception:pass
nt.links.new(sky.outputs[0],bg.inputs['Color']);bg.inputs['Strength'].default_value=float(os.environ.get('CIELO',0.35))
sole=bpy.data.lights.new('sole','SUN');sole.energy=float(os.environ.get('SOLE',4.0));sole.angle=math.radians(1.5);sole.color=(1,0.8,0.6)
so=bpy.data.objects.new('sole',sole);sc.collection.objects.link(so)
sd=Vector((math.cos(EL)*math.sin(AZ),-math.cos(EL)*math.cos(AZ),math.sin(EL)))   # verso il sole (z su)
so.rotation_euler=sd.to_track_quat('Z','Y').to_euler()
LUCE=float(os.environ.get('LUCE',90))
for q in PUNTI:
    if q['esterno'] or not q['soffitto']:continue
    l=bpy.data.lights.new('l_'+q['id'],'AREA');l.shape='DISK';l.size=1.2;l.energy=LUCE;l.color=(1.0,0.84,0.66)
    o=bpy.data.objects.new('l_'+q['id'],l);sc.collection.objects.link(o);o.location=B(q['x'],q['soffitto']-0.03,q['z'])
    l.cycles.is_caustics_light=False;o.visible_camera=False
# --- camera e Cycles ---
cd=bpy.data.cameras.new('pano');cd.type='PANO'
try:cd.panorama_type='EQUIRECTANGULAR'
except Exception:cd.cycles.panorama_type='EQUIRECTANGULAR'
cd.clip_start=0.05
cam=bpy.data.objects.new('pano',cd);sc.collection.objects.link(cam);sc.camera=cam
sc.render.engine='CYCLES';cy=sc.cycles
pr=bpy.context.preferences.addons['cycles'].preferences
try:
    pr.compute_device_type='OPTIX';pr.refresh_devices()
    for d in pr.devices:d.use=(d.type=='OPTIX')
    cy.device='GPU';log('GPU',[d.name for d in pr.devices if d.use])
except Exception as ex:log('niente GPU',ex);cy.device='CPU'
cy.samples=CAMP;cy.use_adaptive_sampling=True;cy.adaptive_threshold=0.01;cy.use_denoising=True
try:cy.denoiser='OPTIX' if cy.device=='GPU' else 'OPENIMAGEDENOISE'
except Exception:pass
cy.max_bounces=12;cy.diffuse_bounces=5;cy.glossy_bounces=4;cy.transmission_bounces=8;cy.transparent_max_bounces=64
cy.sample_clamp_indirect=8
sc.render.resolution_x=LARG;sc.render.resolution_y=LARG//2;sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast' if 'AgX - Medium High Contrast' in [i.identifier for i in sc.view_settings.bl_rna.properties['look'].enum_items] else 'None'
sc.view_settings.exposure=float(os.environ.get('ESPO',0.0))
if CLAY:sc.view_layers[0].material_override=bpy.data.materials.new('clay')
sc.render.image_settings.file_format='JPEG';sc.render.image_settings.quality=90
for q in PUNTI:
    if IDS!=['tutti'] and q['id'] not in IDS:continue
    cam.location=B(q['x'],PAV+OC,q['z'])
    d=B(q['tx'],0,q['tz'])-B(q['x'],0,q['z']);th=math.atan2(-d.x,d.y)
    cam.rotation_euler=(math.radians(90),0,th)
    sc.render.filepath=f"{OUT}/{q['id']}.jpg";t0=time.time();bpy.ops.render.render(write_still=True);log('FATTO',q['id'],round(time.time()-t0),'s')
