// punti del modello in coordinate mondo (centri dei triangoli + vertici), float32 x,y,z, per l'allineamento col rilievo
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {writeFileSync} from 'fs';
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS);const doc=await io.read(process.argv[2]);
const out=[];const scene=doc.getRoot().getDefaultScene()||doc.getRoot().listScenes()[0];
function mul(m,v){return [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];}
scene.traverse(n=>{const me=n.getMesh();if(!me)return;const M=n.getWorldMatrix();
 for(const p of me.listPrimitives()){const pos=p.getAttribute('POSITION');const ix=p.getIndices();const v=[0,0,0],w=[0,0,0],u=[0,0,0];
  const nt=ix?ix.getCount()/3:pos.getCount()/3;
  for(let t=0;t<nt;t++){const a=ix?ix.getScalar(3*t):3*t,b=ix?ix.getScalar(3*t+1):3*t+1,c=ix?ix.getScalar(3*t+2):3*t+2;
   const A=mul(M,pos.getElement(a,v)),B=mul(M,pos.getElement(b,w)),C=mul(M,pos.getElement(c,u));
   // area per campionare in proporzione: un punto ogni ~0,01 m² circa, minimo il baricentro
   const ab=[B[0]-A[0],B[1]-A[1],B[2]-A[2]],ac=[C[0]-A[0],C[1]-A[1],C[2]-A[2]];
   const cr=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];const ar=Math.hypot(...cr)/2;
   const k=Math.min(400,Math.max(1,Math.round(ar/0.01)));
   for(let i=0;i<k;i++){let r1=Math.random(),r2=Math.random();if(k===1){r1=r2=1/3;}else if(r1+r2>1){r1=1-r1;r2=1-r2;}
    out.push(A[0]+ab[0]*r1+ac[0]*r2,A[1]+ab[1]*r1+ac[1]*r2,A[2]+ab[2]*r1+ac[2]*r2);}}}});
writeFileSync(process.argv[3],Buffer.from(new Float32Array(out).buffer));console.log('punti',out.length/3);
