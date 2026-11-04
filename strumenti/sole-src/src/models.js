// Lettura dei modelli di progetto: SketchUp, GLB/glTF, Collada, KMZ, OBJ, FBX, STL.
// Ogni lettore restituisce un Object3D in metri con l'asse Y verso l'alto.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { unzipSync, strFromU8 } from 'three/examples/jsm/libs/fflate.module.js';

export const ACCEPT = '.skp,.glb,.gltf,.dae,.kmz,.obj,.fbx,.stl';
const gltf = new GLTFLoader();

const ext = (name) => (name.split('.').pop() || '').toLowerCase();

function parseGLB(buffer) {
  return new Promise((res, rej) => gltf.parse(buffer, '', (g) => res(g.scene), rej));
}

// SketchUp: conversione in un worker (OpenSKP), poi lettura del GLB prodotto.
function skpToGLB(buffer) {
  return new Promise((res, rej) => {
    const w = new Worker(new URL('./skp-worker.js', import.meta.url), { type: 'module' });
    w.onmessage = (e) => {
      w.terminate();
      if (e.data.ok) res(e.data.glb.buffer);
      else rej(new Error(e.data.error));
    };
    w.onerror = (e) => { w.terminate(); rej(new Error(e.message || 'errore nel lettore SketchUp')); };
    w.postMessage(buffer, [buffer]);
  });
}

// KMZ (export "Google Earth" di SketchUp): contiene un .dae e, spesso, la posizione geografica.
async function readKMZ(buffer) {
  const { ColladaLoader } = await import('three/examples/jsm/loaders/ColladaLoader.js');
  const files = unzipSync(new Uint8Array(buffer));
  const names = Object.keys(files);
  const kmlName = names.find((n) => n.toLowerCase().endsWith('.kml'));
  const daeName = names.find((n) => n.toLowerCase().endsWith('.dae'));
  if (!daeName) throw new Error('nel KMZ non c’è un modello .dae');

  let geo = null;
  if (kmlName) {
    const kml = new DOMParser().parseFromString(strFromU8(files[kmlName]), 'application/xml');
    const loc = kml.getElementsByTagName('Location')[0];
    const num = (el, tag) => parseFloat(el?.getElementsByTagName(tag)[0]?.textContent);
    if (loc) {
      const lat = num(loc, 'latitude'), lon = num(loc, 'longitude');
      const heading = num(kml.getElementsByTagName('Orientation')[0], 'heading');
      if (Number.isFinite(lat) && Number.isFinite(lon)) geo = { lat, lon, heading: Number.isFinite(heading) ? heading : 0 };
    }
  }

  // le texture stanno nello zip accanto al .dae
  const base = daeName.includes('/') ? daeName.slice(0, daeName.lastIndexOf('/') + 1) : '';
  const blobs = [];
  const manager = new THREE.LoadingManager();
  manager.setURLModifier((url) => {
    const clean = decodeURIComponent(url).replace(/^\.\//, '');
    const hit = files[base + clean] || files[clean] || files[names.find((n) => n.endsWith('/' + clean.split('/').pop())) || ''];
    if (!hit) return url;
    const u = URL.createObjectURL(new Blob([hit]));
    blobs.push(u);
    return u;
  });
  const dae = new ColladaLoader(manager).parse(strFromU8(files[daeName]), '');
  setTimeout(() => blobs.forEach(URL.revokeObjectURL), 20000);
  return { object: dae.scene, geo };
}

/**
 * Restituisce { object, units, geo, guessed } — `guessed` è true quando il formato
 * non dice in che unità è stato disegnato e la scala è stata dedotta dalle misure.
 */
export async function loadModelFile(file) {
  const kind = ext(file.name);
  const buffer = await file.arrayBuffer();
  let object, geo = null, guessed = false;

  switch (kind) {
    case 'skp':
      object = await parseGLB(await skpToGLB(buffer));
      break;
    case 'glb':
    case 'gltf':
      object = await parseGLB(buffer);
      break;
    case 'dae': {
      const { ColladaLoader } = await import('three/examples/jsm/loaders/ColladaLoader.js');
      object = new ColladaLoader().parse(new TextDecoder().decode(buffer), '').scene;
      break;
    }
    case 'kmz':
      ({ object, geo } = await readKMZ(buffer));
      break;
    case 'obj': {
      const { OBJLoader } = await import('three/examples/jsm/loaders/OBJLoader.js');
      object = new OBJLoader().parse(new TextDecoder().decode(buffer));
      guessed = true;
      break;
    }
    case 'fbx': {
      const { FBXLoader } = await import('three/examples/jsm/loaders/FBXLoader.js');
      object = new FBXLoader().parse(buffer, '');
      guessed = true;
      break;
    }
    case 'stl': {
      const { STLLoader } = await import('three/examples/jsm/loaders/STLLoader.js');
      const g = new STLLoader().parse(buffer);
      g.rotateX(-Math.PI / 2); // STL è quasi sempre Z verso l'alto
      object = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xe8e2d6, roughness: 0.8 }));
      guessed = true;
      break;
    }
    default:
      throw new Error('formato non supportato');
  }

  // materiali a doppia faccia (i modelli SketchUp hanno spesso facce rovesciate) e ombre
  object.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    mats.forEach((m) => { if (m) { m.side = THREE.DoubleSide; m.shadowSide = THREE.FrontSide; } }); // niente righe d'ombra sulle facce
  });

  let scale = 1;
  if (guessed) scale = guessScale(object);
  return { object, geo, scale, guessed, kind };
}

// Senza unità dichiarate: un edificio sta fra 2 e 400 m. Si sceglie la scala che ci rientra.
export const SCALES = [
  { id: 'm', label: 'metri', k: 1 },
  { id: 'cm', label: 'centimetri', k: 0.01 },
  { id: 'mm', label: 'millimetri', k: 0.001 },
  { id: 'in', label: 'pollici', k: 0.0254 },
];
function guessScale(object) {
  const size = new THREE.Box3().setFromObject(object).getSize(new THREE.Vector3());
  const d = Math.max(size.x, size.y, size.z);
  if (d > 4000) return 0.001;
  if (d > 400) return 0.01;
  return 1;
}
