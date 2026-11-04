// Converte un file SketchUp (.skp) in GLB in un thread separato, così la pagina non si blocca
// mentre legge modelli grandi. Libreria: OpenSKP (MIT), lettura del formato senza SketchUp.
import { buildInstancedScene, toInstancedGLB } from 'openskp';

self.onmessage = (e) => {
  try {
    const scene = buildInstancedScene(e.data);
    const glb = toInstancedGLB(scene, { textures: true });
    self.postMessage({ ok: true, glb, units: scene.units || null }, [glb.buffer]);
  } catch (err) {
    self.postMessage({ ok: false, error: String((err && err.message) || err) });
  }
};
