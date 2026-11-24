// Progetto Mario: finiture del modello come nei render, sul GLB grezzo di OpenSKP (prima di strip-uv e optimize).
// Uso: node finiture-mario.mjs grezzo.glb spina.jpg uscita.glb
// - pavimenti (texture laminato m227, m229) -> parquet a spina in rovere (spina.py), coordinate dalla pianta, a 45°
// - bianco predefinito di SketchUp (m10, m4) -> bianco caldo; lato di sopra dei controsoffitti (m219, grigio) -> chiaro
// - vetrata disegnata in azzurro pieno (m205) -> vetro
// - facce gemelle (stesso triangolo, versi opposti: fronte e retro di una faccia SketchUp) -> primitive a faccia singola,
//   così il visore non le disegna una sopra l'altra (lampi ruotando). Il resto resta a doppia faccia.
// Gli indici dei materiali valgono per il mario.skp del 24/11/2026: se il file cambia, rifare l'inventario.
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {readFileSync} from 'fs';
const [,,inp,spina,out]=process.argv;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS);const doc=await io.read(inp);const R=doc.getRoot();const M=R.listMaterials();
const lin=c=>c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4);const srgb=(r,g,b,a=1)=>[lin(r/255),lin(g/255),lin(b/255),a];
const PAV=new Set([227,229]),BIANCO=new Set([10,4]);
// materiale nuovo del parquet
const tex=doc.createTexture('spina').setImage(new Uint8Array(readFileSync(spina))).setMimeType('image/jpeg').setURI('spina.jpg');
const parq=doc.createMaterial('parquet spina rovere').setBaseColorTexture(tex).setBaseColorFactor([1,1,1,1]).setRoughnessFactor(0.55).setMetallicFactor(0).setDoubleSided(true);
for(const i of BIANCO)M[i].setBaseColorFactor(srgb(240,236,228)).setRoughnessFactor(0.9).setMetallicFactor(0);
M[219].setBaseColorFactor(srgb(228,224,216)).setRoughnessFactor(0.9);
M[205].setBaseColorFactor([0.82,0.88,0.88,0.22]).setAlphaMode('BLEND').setRoughnessFactor(0.05);
const PIAST=1.08,S2=Math.SQRT1_2;   // lato della piastrella di spina.py: 12 doghe da 9 cm
// nodi per mesh (servono le matrici del mondo per le coordinate del parquet)
const usi=new Map();R.listNodes().forEach(n=>{const m=n.getMesh();if(m)(usi.get(m)||usi.set(m,[]).get(m)).push(n);});
let nPav=0,nGem=0,nMesh=0;const singola=new Map();
const faccia1=m=>{if(!singola.has(m))singola.set(m,m.clone().setName((m.getName()||'mat')+' 1f').setDoubleSided(false));return singola.get(m);};
for(const mesh of R.listMeshes()){const nodi=usi.get(mesh)||[];
 for(const p of [...mesh.listPrimitives()]){const mi=M.indexOf(p.getMaterial());
  if(PAV.has(mi)){
   if(nodi.length!==1)console.log('attenzione: pavimento in una mesh usata',nodi.length,'volte');
   const W=nodi[0].getWorldMatrix();const P=p.getAttribute('POSITION').getArray();const n=P.length/3;const uv=new Float32Array(n*2);
   for(let k=0;k<n;k++){const x=P[k*3],y=P[k*3+1],z=P[k*3+2];const X=W[0]*x+W[4]*y+W[8]*z+W[12],Z=W[2]*x+W[6]*y+W[10]*z+W[14];
    uv[k*2]=(X+Z)*S2/PIAST;uv[k*2+1]=(X-Z)*S2/PIAST;}
   let a=p.getAttribute('TEXCOORD_0');if(!a){a=doc.createAccessor().setType('VEC2').setBuffer(R.listBuffers()[0]);p.setAttribute('TEXCOORD_0',a);}
   a.setArray(uv);p.setMaterial(parq);nPav++;}}
 // facce gemelle: chiave = i tre vertici arrotondati al mm, in qualunque ordine
 const prims=[...mesh.listPrimitives()];const vista=new Map();const tri=[];
 prims.forEach((p,pi)=>{const P=p.getAttribute('POSITION').getArray(),I=p.getIndices().getArray();
  for(let t=0;t<I.length;t+=3){const v=[I[t],I[t+1],I[t+2]].map(i=>[P[i*3],P[i*3+1],P[i*3+2]]);
   const k=v.map(q=>q.map(x=>Math.round(x*1000)).join(',')).sort().join('|');
   const u=[v[1][0]-v[0][0],v[1][1]-v[0][1],v[1][2]-v[0][2]],w=[v[2][0]-v[0][0],v[2][1]-v[0][1],v[2][2]-v[0][2]];
   const nn=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];const id=tri.length;tri.push({pi,t,g:false});
   const e=vista.get(k);if(e&&!tri[e.id].g&&e.n[0]*nn[0]+e.n[1]*nn[1]+e.n[2]*nn[2]<0){tri[e.id].g=true;tri[id].g=true;}else if(!e)vista.set(k,{id,n:nn});}});
 if(!tri.some(t=>t.g))continue;nMesh++;
 prims.forEach((p,pi)=>{const mine=tri.filter(t=>t.pi===pi);const gem=mine.filter(t=>t.g);if(!gem.length)return;nGem+=gem.length;
  const I=p.getIndices().getArray();const resto=mine.filter(t=>!t.g);
  const mk=ts=>{const a=new Uint32Array(ts.length*3);ts.forEach((t,j)=>{a[j*3]=I[t.t];a[j*3+1]=I[t.t+1];a[j*3+2]=I[t.t+2];});return a;};
  const q=p.clone();q.setIndices(doc.createAccessor().setType('SCALAR').setArray(mk(gem)).setBuffer(R.listBuffers()[0]));q.setMaterial(faccia1(p.getMaterial()));mesh.addPrimitive(q);
  if(resto.length)p.setIndices(doc.createAccessor().setType('SCALAR').setArray(mk(resto)).setBuffer(R.listBuffers()[0]));else{mesh.removePrimitive(p);p.dispose();}});}
console.log('pavimenti in parquet',nPav,'| triangoli gemelli a faccia singola',nGem,'in',nMesh,'mesh | materiali a faccia singola',singola.size);
await io.write(out,doc);
