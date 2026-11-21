// linee disegnate di SketchUp che dividono una faccia piana in due (fughe delle ante, giunti): nelle esportazioni in
// triangoli spariscono. Uscita: segmenti in metri, coordinate del modello (x, y su, z = -Y di SketchUp), con la normale
import {readFileSync,writeFileSync} from 'fs';import {parseSkp} from 'openskp';
const p=parseSkp(new Uint8Array(readFileSync(process.argv[2])));const D=p.definitions;const IN=0.0254;
console.log('root in definitions?',D.has(p.root.id),'esempio refIdx',p.root.instances[0].refIdx,'presente',D.has(p.root.instances[0].refIdx));
// per ogni definizione: segmenti candidati in coordinate locali
const cache=new Map();
function candidati(def){
 if(cache.has(def))return cache.get(def);
 const V=new Map(def.vertices.map(v=>[v.id,[v.x,v.y,v.z]]));const adj=new Map();
 for(const f of def.faces){if(f.hidden)continue;for(const loop of f.loops)for(const u of loop){(adj.get(u.edgeId)||adj.set(u.edgeId,[]).get(u.edgeId)).push(f);}}
 const out=[];
 for(const e of def.edges){if(e.soft||e.smooth||e.hidden)continue;const fs=adj.get(e.id)||[];
  if(fs.length<2){const v1=V.get(e.v1Id),v2=V.get(e.v2Id);if(v1&&v2)out.push([v1,v2,fs.length?fs[0].normal:[0,0,0],'libera']);continue;}
  if(fs.length!==2)continue;
  const [a,b]=fs;const d=a.normal[0]*b.normal[0]+a.normal[1]*b.normal[1]+a.normal[2]*b.normal[2];
  const v1=V.get(e.v1Id),v2=V.get(e.v2Id);if(!v1||!v2)continue;
  if(d>=0.9995)out.push([v1,v2,a.normal,null]);            // linea su una faccia piana
  else if(Math.abs(d)<0.02)out.push([v1,v2,a.normal,b.normal]);}   // spigolo a 90°: forse una fuga fra due scatole
 cache.set(def,out);return out;}
const mul=(A,B)=>{// matrici 3x3 per righe + traslazione: [r(9), t(3)]
 const R=[0,0,0,0,0,0,0,0,0];for(let i=0;i<3;i++)for(let j=0;j<3;j++){let s=0;for(let k=0;k<3;k++)s+=A[3*i+k]*B[3*k+j];R[3*i+j]=s;}
 const t=[0,1,2].map(i=>A[3*i]*B[9]+A[3*i+1]*B[10]+A[3*i+2]*B[11]+A[9+i]);return [...R,...t];};
const ap=(M,v)=>[0,1,2].map(i=>M[3*i]*v[0]+M[3*i+1]*v[1]+M[3*i+2]*v[2]+M[9+i]);
const apn=(M,n)=>{const r=[0,1,2].map(i=>M[3*i]*n[0]+M[3*i+1]*n[1]+M[3*i+2]*n[2]);const l=Math.hypot(...r)||1;return r.map(x=>x/l);};
const seg=[];let nist=0;
function visita(def,M,prof){if(prof>30)return;
 for(const [a,b,n,m] of candidati(def)){const A=ap(M,a),B=ap(M,b),N=apn(M,n);
  const r=[A[0]*IN,A[2]*IN,-A[1]*IN,B[0]*IN,B[2]*IN,-B[1]*IN,N[0],N[2],-N[1]];
  if(m==='libera')r.push(0);else if(m){const Q=apn(M,m);r.push(Q[0],Q[2],-Q[1]);}seg.push(r);}
 for(const ins of def.instances){if(ins.hidden)continue;const c=D.get(ins.refIdx);if(!c)continue;nist++;const m=ins.matrix;visita(c,mul(M,m.slice(0,12)),prof+1);}}
visita(p.root,[1,0,0,0,1,0,0,0,1,0,0,0],0);
let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];for(const r of seg)for(const o of [0,3])for(let k=0;k<3;k++){mn[k]=Math.min(mn[k],r[o+k]);mx[k]=Math.max(mx[k],r[o+k]);}
console.log('istanze visitate',nist,'segmenti',seg.length,'spigoli a 90°',seg.filter(r=>r.length>10).length,'linee libere',seg.filter(r=>r.length===10).length,'bbox',mn.map(v=>v.toFixed(2)),mx.map(v=>v.toFixed(2)));
writeFileSync(process.argv[3],JSON.stringify(seg.map(s=>s.map(v=>+v.toFixed(4)))));
