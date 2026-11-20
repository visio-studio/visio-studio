// sezione orizzontale del modello a quote date: segmenti [x1,z1,x2,z2] separati fra geometria sciolta (muri) e componenti (arredi)
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {writeFileSync} from 'fs';
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS);const doc=await io.read(process.argv[2]);const H=process.argv.slice(4).map(Number);
const out={};for(const h of H)out[h]={muri:[],arredi:[]};
function mul(m,v){return [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];}
const scene=doc.getRoot().listScenes()[0];
scene.traverse(n=>{const me=n.getMesh();if(!me)return;const M=n.getWorldMatrix();const tipo=/ROOT/.test(me.getName()||'')?'muri':'arredi';
 for(const p of me.listPrimitives()){const pos=p.getAttribute('POSITION');const ix=p.getIndices();const nt=ix?ix.getCount()/3:pos.getCount()/3;const tmp=[0,0,0];
  const V=[];for(let i=0;i<pos.getCount();i++)V.push(mul(M,pos.getElement(i,tmp)));
  for(let t=0;t<nt;t++){const P=[0,1,2].map(k=>V[ix?ix.getScalar(3*t+k):3*t+k]);
   for(const h of H){const s=[];for(let k=0;k<3;k++){const a=P[k],b=P[(k+1)%3];if((a[1]-h)*(b[1]-h)<0){const u=(h-a[1])/(b[1]-a[1]);s.push([a[0]+u*(b[0]-a[0]),a[2]+u*(b[2]-a[2])]);}}
    if(s.length===2)out[h][tipo].push([s[0][0],s[0][1],s[1][0],s[1][1]]);}}}});
writeFileSync(process.argv[3],JSON.stringify(out));for(const h of H)console.log(h,'muri',out[h].muri.length,'arredi',out[h].arredi.length);
