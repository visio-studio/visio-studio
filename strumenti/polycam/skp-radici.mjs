// Elenca gli oggetti di primo livello di un SKP con ingombro in metri (Y in alto): serve a trovare la variante giusta
// quando il file ne contiene più d'una. Uso: node --max-old-space-size=24000 skp-radici.mjs file.skp  → stampa e scrive radici.json
// OpenSKP va corretto in locale (EdgeFlagStore → Map, vedi NOTE-DI-LAVORO §4) per i file grandi.
import {readFileSync,writeFileSync} from 'fs';import {buildInstancedScene} from 'openskp';
const t0=Date.now();const s=buildInstancedScene(new Uint8Array(readFileSync(process.argv[2])));
console.log('scena',(Date.now()-t0)/1000,'s bounds',JSON.stringify(s.bounds),'risorse',s.meshResources.length);
const R=new Map(s.meshResources.map(r=>[r.id,r]));
const rb=new Map();for(const r of s.meshResources){const b=[1e9,1e9,1e9,-1e9,-1e9,-1e9];let n=0;for(const p of r.primitives){const P=p.positions;n+=P.length/9;for(let i=0;i<P.length;i+=3)for(let k=0;k<3;k++){b[k]=Math.min(b[k],P[i+k]);b[k+3]=Math.max(b[k+3],P[i+k]);}}rb.set(r.id,{b,n});}
const mul=(a,b)=>{const r=new Array(16).fill(0);for(let i=0;i<4;i++)for(let j=0;j<4;j++)for(let k=0;k<4;k++)r[j*4+i]+=a[k*4+i]*b[j*4+k];return r;};
const ap=(M,v)=>[M[0]*v[0]+M[4]*v[1]+M[8]*v[2]+M[12],M[1]*v[0]+M[5]*v[1]+M[9]*v[2]+M[13],M[2]*v[0]+M[6]*v[1]+M[10]*v[2]+M[14]];
function walk(n,M,B,st){const W=mul(M,n.matrix);if(n.hidden){st.hid++;return;}if(n.meshResourceId){const {b,n:t}=rb.get(n.meshResourceId);st.tri+=t;if(b[0]<1e8)for(const x of [b[0],b[3]])for(const y of [b[1],b[4]])for(const z of [b[2],b[5]]){const p=ap(W,[x,y,z]);for(let k=0;k<3;k++){B[k]=Math.min(B[k],p[k]);B[k+3]=Math.max(B[k+3],p[k]);}}}for(const c of n.children)walk(c,W,B,st);}
const I=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];const out=[];
s.sceneHierarchy.children.forEach((c,k)=>{const B=[1e9,1e9,1e9,-1e9,-1e9,-1e9],st={tri:0,hid:0};walk(c,I,B,st);out.push({k,def:c.definitionName,layer:c.layer,hid:c.hidden,tri:st.tri,bb:B.map(x=>+x.toFixed(2))});});
for(const o of out.sort((a,b)=>a.bb[0]-b.bb[0]))console.log(o.k,o.def.slice(0,40).padEnd(40),o.layer.padEnd(14),o.hid?'NASC':'', 'tri',o.tri,'x',o.bb[0],o.bb[3],'y',o.bb[1],o.bb[4],'z',o.bb[2],o.bb[5]);
writeFileSync('radici.json',JSON.stringify(out));
