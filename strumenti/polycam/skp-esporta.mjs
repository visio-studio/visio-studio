// Esporta in GLB solo gli oggetti di primo livello che stanno in un riquadro della pianta (metri, assi di skp-radici.mjs),
// togliendo la geometria libera del livello principale; il riquadro finisce centrato sull'origine.
// Uso: node --max-old-space-size=24000 skp-esporta.mjs file.skp radici.json uscita.glb xmin xmax zmin zmax [escludi,definizioni]
// Poi: strip-uv.mjs (senza togliere NORMAL: su modelli grandi il ricalcolo nel browser blocca la pagina), gltf-transform prune e optimize.
import {readFileSync,writeFileSync} from 'fs';import {buildInstancedScene,toInstancedGLB} from 'openskp';
const [,,inp,rj,out,x0,x1,z0,z1,esc='']=process.argv;const X0=+x0,X1=+x1,Z0=+z0,Z1=+z1,E=new Set(esc.split(',').filter(Boolean));
const s=buildInstancedScene(new Uint8Array(readFileSync(inp)));const rad=JSON.parse(readFileSync(rj));
const tieni=new Set(rad.filter(o=>o.tri>0&&!E.has(o.def)&&o.bb[0]>=X0&&o.bb[3]<=X1&&o.bb[2]>=Z0&&o.bb[5]<=Z1).map(o=>o.k));
const H=s.sceneHierarchy;H.children=H.children.filter((c,k)=>tieni.has(k));delete H.meshResourceId;
const usati=new Set();(function w(n){if(n.meshResourceId)usati.add(n.meshResourceId);n.children.forEach(w);})(H);
s.meshResources=s.meshResources.filter(r=>usati.has(r.id));
H.matrix=[1,0,0,0,0,1,0,0,0,0,1,0,-(X0+X1)/2,0,-(Z0+Z1)/2,1];
console.log('oggetti tenuti',tieni.size,'risorse',s.meshResources.length);
const g=toInstancedGLB(s,{textures:true});writeFileSync(out,g);console.log('glb MB',(g.length/1e6).toFixed(1));
