// toglie TEXCOORD dai materiali senza texture: SketchUp dà uv a ogni faccia e impedisce di saldare i vertici
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc=await io.read(process.argv[2]);let tolti=0,tenuti=0;
for(const m of doc.getRoot().listMeshes())for(const p of m.listPrimitives()){
 const mat=p.getMaterial();const tex=mat&&(mat.getBaseColorTexture()||mat.getNormalTexture());
 p.setAttribute('NORMAL',null);for(const s of ['TEXCOORD_0','TEXCOORD_1']){const a=p.getAttribute(s);if(!a)continue;if(tex){tenuti++;continue;}p.setAttribute(s,null);tolti++;}}
for(const a of doc.getRoot().listAccessors())if(a.listParents().length<=1)a.dispose();
await io.write(process.argv[3],doc);console.log('uv tolti',tolti,'tenuti',tenuti);
