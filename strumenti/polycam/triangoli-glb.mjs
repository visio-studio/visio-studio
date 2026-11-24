// triangoli di un GLB in coordinate mondo: float32 [ax,ay,az,bx,by,bz,cx,cy,cz] per triangolo
// uso: node triangoli-glb.mjs scena.glb uscita.bin   (gltf-transform da node_modules della cartella corrente)
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {writeFileSync} from 'fs';
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS);const doc=await io.read(process.argv[2]);
const sc=doc.getRoot().getDefaultScene()||doc.getRoot().listScenes()[0];const out=[];
const mul=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
sc.traverse(n=>{const me=n.getMesh();if(!me)return;const M=n.getWorldMatrix();
 for(const p of me.listPrimitives()){const pos=p.getAttribute('POSITION');const ix=p.getIndices();const nt=ix?ix.getCount()/3:pos.getCount()/3;const v=[0,0,0];
  for(let t=0;t<nt;t++)for(let k=0;k<3;k++){const i=ix?ix.getScalar(3*t+k):3*t+k;out.push(...mul(M,pos.getElement(i,v)));}}});
writeFileSync(process.argv[3],Buffer.from(new Float32Array(out).buffer));console.log('triangoli',out.length/9);
