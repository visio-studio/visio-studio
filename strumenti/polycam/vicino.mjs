// tutti gli spigoli (anche nascosti o morbidi) vicini a una zona: per capire come sono disegnate le ante
import {readFileSync} from 'fs';import {parseSkp} from 'openskp';
const p=parseSkp(new Uint8Array(readFileSync(process.argv[2])));const D=p.definitions;const IN=0.0254;
const Z=JSON.parse(process.argv[3]);   // {x:[a,b],y:[a,b],z:[a,b]} coordinate del modello
const mul=(A,B)=>{const R=[0,0,0,0,0,0,0,0,0];for(let i=0;i<3;i++)for(let j=0;j<3;j++){let s=0;for(let k=0;k<3;k++)s+=A[3*i+k]*B[3*k+j];R[3*i+j]=s;}return [...R,...[0,1,2].map(i=>A[3*i]*B[9]+A[3*i+1]*B[10]+A[3*i+2]*B[11]+A[9+i])];};
const ap=(M,v)=>[0,1,2].map(i=>M[3*i]*v[0]+M[3*i+1]*v[1]+M[3*i+2]*v[2]+M[9+i]);
const cnt={};const es=[];
function visita(def,M,nome,prof){if(prof>30)return;const V=new Map(def.vertices.map(v=>[v.id,[v.x,v.y,v.z]]));const adj=new Map();
 for(const f of def.faces)for(const l of f.loops)for(const u of l)adj.set(u.edgeId,(adj.get(u.edgeId)||0)+1);
 for(const e of def.edges){const a=V.get(e.v1Id),b=V.get(e.v2Id);if(!a||!b)continue;const A=ap(M,a),B=ap(M,b);
  const m=[(A[0]+B[0])/2*IN,(A[2]+B[2])/2*IN,-(A[1]+B[1])/2*IN];
  if(m[0]<Z.x[0]||m[0]>Z.x[1]||m[1]<Z.y[0]||m[1]>Z.y[1]||m[2]<Z.z[0]||m[2]>Z.z[1])continue;
  const k=`${nome}|facce=${adj.get(e.id)||0}|${e.hidden?'nascosto':e.soft?'morbido':e.smooth?'liscio':'visibile'}`;cnt[k]=(cnt[k]||0)+1;
  if(es.length<40&&!e.soft&&!e.hidden)es.push([k,[A,B].map(P=>[P[0]*IN,P[2]*IN,-P[1]*IN].map(v=>+v.toFixed(3)))]);}
 for(const ins of def.instances){const c=D.get(ins.refIdx);if(c)visita(c,mul(M,ins.matrix.slice(0,12)),c.name||ins.name||'?',prof+1);}}
visita(p.root,[1,0,0,0,1,0,0,0,1,0,0,0],'ROOT',0);
console.log(Object.entries(cnt).sort((a,b)=>b[1]-a[1]).slice(0,20));for(const e of es)console.log(JSON.stringify(e));
