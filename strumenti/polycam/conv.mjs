// SKP -> GLB con OpenSKP (stessa chiamata di strumenti/sole-src/src/skp-worker.js), più un riepilogo del modello
import {readFileSync,writeFileSync} from 'fs';
import {buildInstancedScene,toInstancedGLB} from 'openskp';
const [,,inp,out]=process.argv;const t0=Date.now();
const buf=new Uint8Array(readFileSync(inp));
const scene=buildInstancedScene(buf);
console.log('scena in',(Date.now()-t0)/1000,'s; chiavi',Object.keys(scene),'unità',scene.units);
const glb=toInstancedGLB(scene,{textures:true});writeFileSync(out,glb);
console.log('glb',(glb.length/1e6).toFixed(1),'MB in',(Date.now()-t0)/1000,'s');
