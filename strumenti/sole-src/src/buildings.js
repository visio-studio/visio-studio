// Edifici da OpenStreetMap (Overpass API) estrusi in 3D.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
];

// I server Overpass pubblici sono spesso pieni (502 immediato) o restano appesi senza
// rispondere: si interrogano tutti insieme, vince il primo che risponde con dati validi,
// gli altri vengono interrotti. Ognuno ha un tempo massimo, così non si resta mai bloccati.
const TIMEOUT_MS = 45000;

export async function fetchBuildings(lat, lon, radius) {
  const a = `(around:${radius},${lat},${lon})`;
  const q = `[out:json][timeout:40];(way["building"]${a};way["building:part"]${a};relation["building"]${a};);out geom;`;
  const ctrls = ENDPOINTS.map(() => new AbortController());
  const timer = setTimeout(() => ctrls.forEach((c) => c.abort()), TIMEOUT_MS);
  const tries = ENDPOINTS.map(async (ep, i) => {
    const r = await fetch(ep, {
      method: 'POST',
      body: 'data=' + encodeURIComponent(q),
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      signal: ctrls[i].signal,
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    if (!Array.isArray(j.elements)) throw new Error('risposta non valida');
    // Overpass segnala i timeout interni con "remark" e un elenco vuoto: non è un risultato
    if (!j.elements.length && j.remark && /timed out|runtime error/i.test(j.remark)) throw new Error(j.remark);
    return { i, elements: j.elements };
  });
  try {
    const win = await Promise.any(tries);
    ctrls.forEach((c, i) => { if (i !== win.i) c.abort(); });
    return win.elements;
  } catch {
    throw new Error('Overpass non raggiungibile');
  } finally {
    clearTimeout(timer);
  }
}

// ---------- altezze ----------
const LEVEL = 3.2;
const DEFAULT_H = {
  house: 7, detached: 7, semidetached_house: 7, bungalow: 4, garage: 3, garages: 3, shed: 3,
  hut: 3, kiosk: 3, cabin: 4, roof: 4, carport: 3, church: 16, cathedral: 22, chapel: 8,
  apartments: 15, residential: 13, commercial: 12, office: 15, retail: 6, supermarket: 6,
  industrial: 8, warehouse: 8, school: 12, hospital: 18, hotel: 15, public: 12, civic: 12,
};

function num(v) {
  if (v == null) return NaN;
  const m = String(v).replace(',', '.').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : NaN;
}

function heights(tags) {
  let h = num(tags.height);
  const lv = num(tags['building:levels']);
  const rl = num(tags['roof:levels']);
  if (isNaN(h) && !isNaN(lv)) h = lv * LEVEL + (isNaN(rl) ? 0 : rl * LEVEL * 0.6);
  let min = num(tags.min_height);
  const minLv = num(tags['building:min_level']);
  if (isNaN(min)) min = !isNaN(minLv) ? minLv * LEVEL : 0;
  const estimated = isNaN(h);
  if (estimated) {
    const type = tags.building && tags.building !== 'yes' ? tags.building : tags['building:part'];
    h = DEFAULT_H[type] ?? 10;
  }
  // tettoie: solo la copertura
  if ((tags.building === 'roof' || tags['building:part'] === 'roof') && !tags.min_height && !tags['building:min_level']) {
    min = Math.max(0, h - 0.6);
  }
  if (h <= min) h = min + 1;
  return { h, min, estimated };
}

// ---------- geometria ----------
const same = (a, b) => Math.abs(a.lat - b.lat) < 1e-9 && Math.abs(a.lon - b.lon) < 1e-9;

function assembleRings(ways) {
  const rings = [];
  const pool = ways.map((w) => w.slice());
  while (pool.length) {
    let ring = pool.shift();
    let guard = 0;
    while (!same(ring[0], ring[ring.length - 1]) && guard++ < 1000) {
      const end = ring[ring.length - 1];
      const i = pool.findIndex((w) => same(w[0], end) || same(w[w.length - 1], end));
      if (i < 0) break;
      let w = pool.splice(i, 1)[0];
      if (!same(w[0], end)) w = w.reverse();
      ring = ring.concat(w.slice(1));
    }
    if (ring.length >= 4 && same(ring[0], ring[ring.length - 1])) rings.push(ring);
  }
  return rings;
}

function pointInRing(p, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function centroid(ring) {
  let x = 0, y = 0;
  for (const p of ring) { x += p[0]; y += p[1]; }
  return [x / ring.length, y / ring.length];
}

function bbox(ring) {
  let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
  for (const [x, y] of ring) { a = Math.min(a, x); b = Math.min(b, y); c = Math.max(c, x); d = Math.max(d, y); }
  return [a, b, c, d];
}

// Converte un anello lat/lon in coordinate locali, senza il punto di chiusura duplicato.
function toLocalRing(pts, proj) {
  const out = pts.map((p) => { const l = proj.toLocal(p.lat, p.lon); return [l.x, l.n]; });
  const f = out[0], l = out[out.length - 1];
  if (out.length > 1 && Math.abs(f[0] - l[0]) < 1e-6 && Math.abs(f[1] - l[1]) < 1e-6) out.pop();
  return out;
}

const COLOR_KNOWN = new THREE.Color(0xeae7e0);
const COLOR_EST = new THREE.Color(0xdcc9a6);

/**
 * opts.hideAt: [[x, n], …] — salta gli edifici che contengono uno di questi punti (per sostituirli col progetto).
 */
export function buildBuildingsMesh(elements, proj, opts = {}) {
  const fps = [];
  for (const el of elements) {
    const tags = el.tags || {};
    if (tags.building === 'no') continue;
    if (el.type === 'way' && el.geometry && el.geometry.length >= 4) {
      fps.push({
        outer: toLocalRing(el.geometry, proj),
        holes: [],
        tags,
        isPart: !!tags['building:part'] && !tags.building,
      });
    } else if (el.type === 'relation' && el.members) {
      const outerW = el.members.filter((m) => m.type === 'way' && m.role !== 'inner' && m.geometry).map((m) => m.geometry);
      const innerW = el.members.filter((m) => m.type === 'way' && m.role === 'inner' && m.geometry).map((m) => m.geometry);
      const outers = assembleRings(outerW).map((r) => toLocalRing(r, proj));
      const inners = assembleRings(innerW).map((r) => toLocalRing(r, proj));
      for (const o of outers) {
        fps.push({ outer: o, holes: inners.filter((h) => pointInRing(h[0], o)), tags, isPart: false });
      }
    }
  }

  // Se un edificio è descritto con building:part, nascondi il suo contorno generico.
  const partC = fps.filter((f) => f.isPart).map((f) => centroid(f.outer));
  for (const f of fps) {
    if (f.isPart || !partC.length) continue;
    const [a, b, c, d] = bbox(f.outer);
    if (partC.some((p) => p[0] >= a && p[0] <= c && p[1] >= b && p[1] <= d && pointInRing(p, f.outer))) f.skip = true;
  }

  const geoms = [];
  let count = 0, estimated = 0;
  for (const f of fps) {
    if (f.skip || f.outer.length < 3) continue;
    if (opts.hideAt && opts.hideAt.some((pt) => pointInRing(pt, f.outer))) continue;
    if (Math.abs(THREE.ShapeUtils.area(f.outer.map(([x, y]) => new THREE.Vector2(x, y)))) < 2) continue;
    const { h, min, estimated: est } = heights(f.tags);
    try {
      const shape = new THREE.Shape(f.outer.map(([x, y]) => new THREE.Vector2(x, y)));
      shape.holes = f.holes.map((r) => new THREE.Path(r.map(([x, y]) => new THREE.Vector2(x, y))));
      const g = new THREE.ExtrudeGeometry(shape, { depth: h - min, bevelEnabled: false });
      g.rotateX(-Math.PI / 2); // forma (x, nord) -> scena (x, y=su, z=-nord)
      g.translate(0, min, 0);
      const col = est ? COLOR_EST : COLOR_KNOWN;
      const n = g.attributes.position.count;
      const colors = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { colors[i * 3] = col.r; colors[i * 3 + 1] = col.g; colors[i * 3 + 2] = col.b; }
      g.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      g.clearGroups();
      geoms.push(g);
      count++;
      if (est) estimated++;
    } catch {
      /* geometria OSM non valida: salta */
    }
  }

  if (!geoms.length) return { mesh: null, count: 0, estimated: 0 };
  const merged = mergeGeometries(geoms, false);
  geoms.forEach((g) => g.dispose());
  merged.computeVertexNormals();
  const mesh = new THREE.Mesh(
    merged,
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0 })
  );
  mesh.name = 'Edifici_OSM';
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return { mesh, count, estimated };
}
