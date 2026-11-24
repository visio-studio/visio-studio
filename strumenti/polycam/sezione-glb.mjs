// Sezione orizzontale di un GLB (non compresso) a una quota: segmenti (x1,z1,x2,z2) per ogni oggetto di primo livello.
// Uso: node sezione-glb.mjs modello.glb quota uscita.json   (quota in metri, assi del GLB: y in alto)
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {writeFileSync} from 'fs';
const [,,inp,qs,out]=process.argv;const Q=+qs;
const d=await new NodeIO().registerExtensions(ALL_EXTENSIONS).read(inp);const top=d.getRoot().listScenes()[0].listChildren()[0];
const res={};
function seg(nodo,chiave){const m=nodo.getMesh();if(m){const W=nodo.getWorldMatrix();const S=res[chiave]||(res[chiave]=[]);
 for(const p of m.listPrimitives()){const P=p.getAttribute('POSITION').getArray(),I=p.getIndices().getArray();
  const v=i=>{const x=P[i*3],y=P[i*3+1],z=P[i*3+2];return [W[0]*x+W[4]*y+W[8]*z+W[12],W[1]*x+W[5]*y+W[9]*z+W[13],W[2]*x+W[6]*y+W[10]*z+W[14]];};
  for(let t=0;t<I.length;t+=3){const a=v(I[t]),b=v(I[t+1]),c=v(I[t+2]);const pts=[];
   for(const [u,w] of [[a,b],[b,c],[c,a]]){const du=u[1]-Q,dw=w[1]-Q;if((du<0)!==(dw<0)){const k=du/(du-dw);pts.push([u[0]+k*(w[0]-u[0]),u[2]+k*(w[2]-u[2])]);}}
   if(pts.length===2)S.push([+pts[0][0].toFixed(4),+pts[0][1].toFixed(4),+pts[1][0].toFixed(4),+pts[1][1].toFixed(4)]);}}}
 for(const c of nodo.listChildren())seg(c,chiave);}
const m0=top.getMesh();if(m0){const tmp=top.listChildren();seg({getMesh:()=>m0,getWorldMatrix:()=>top.getWorldMatrix(),listChildren:()=>[]},'ROOT');}
top.listChildren().forEach((c,k)=>seg(c,k+':'+c.getName()));
writeFileSync(out,JSON.stringify(res));for(const [k,s] of Object.entries(res))if(s.length)console.log(k,s.length);
