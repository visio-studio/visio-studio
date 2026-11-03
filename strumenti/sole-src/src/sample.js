// Quartiere di esempio (formato Overpass) usato quando i server OSM non sono raggiungibili:
// isolati con cortile, palazzine a schiera, una piazza allungata al centro, una chiesa con campanile.
import { makeProjection } from './geo.js';

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

export function sampleElements(lat, lon) {
  const proj = makeProjection(lat, lon);
  const rnd = rng(20261103);
  const ll = (x, n) => { const p = proj.toLatLon(x, n); return { lat: p.lat, lon: p.lon }; };
  const rect = (x0, n0, x1, n1) => [ll(x0, n0), ll(x1, n0), ll(x1, n1), ll(x0, n1), ll(x0, n0)];
  const els = [];
  let id = 1;

  const heightTags = () => {
    const r = rnd();
    if (r < 0.45) return { building: 'apartments', height: String(Math.round(13 + rnd() * 12)) };
    if (r < 0.8) return { building: 'apartments', 'building:levels': String(4 + Math.floor(rnd() * 4)) };
    return { building: 'residential' }; // senza altezza: stimata
  };

  // Piazza centrale e chiesa
  const PX = 45, PN = 95; // semi-assi della piazza (allungata nord-sud)
  els.push({ type: 'way', id: id++, tags: { building: 'church', height: '26' }, geometry: rect(PX + 14, -22, PX + 48, 26) });
  els.push({ type: 'way', id: id++, tags: { building: 'yes', 'building:part': 'yes', height: '42', 'tower:type': 'bell_tower' }, geometry: rect(PX + 14, 26, PX + 24, 36) });

  const STEP_X = 74, STEP_N = 66, STREET = 12, LIMIT = 460;
  for (let gx = -LIMIT; gx < LIMIT; gx += STEP_X) {
    for (let gn = -LIMIT; gn < LIMIT; gn += STEP_N) {
      const jx = (rnd() - 0.5) * 6, jn = (rnd() - 0.5) * 6;
      const x0 = gx + STREET / 2 + jx, x1 = gx + STEP_X - STREET / 2 + jx;
      const n0 = gn + STREET / 2 + jn, n1 = gn + STEP_N - STREET / 2 + jn;
      // lascia libera la piazza e la chiesa
      if (x1 > -PX - 6 && x0 < PX + 52 && n1 > -PN - 6 && n0 < PN + 6) continue;
      if (Math.hypot((x0 + x1) / 2, (n0 + n1) / 2) > LIMIT) continue;

      const r = rnd();
      if (r < 0.4) {
        // palazzo con cortile
        const t = 9 + rnd() * 3;
        els.push({
          type: 'relation', id: id++, tags: { type: 'multipolygon', ...heightTags() },
          members: [
            { type: 'way', role: 'outer', geometry: rect(x0, n0, x1, n1) },
            { type: 'way', role: 'inner', geometry: rect(x0 + t, n0 + t, x1 - t, n1 - t) },
          ],
        });
      } else if (r < 0.85) {
        // isolato diviso in palazzine
        const parts = 2 + Math.floor(rnd() * 3);
        const w = (x1 - x0) / parts;
        for (let i = 0; i < parts; i++) {
          const depth = 12 + rnd() * 6;
          els.push({ type: 'way', id: id++, tags: heightTags(), geometry: rect(x0 + i * w, n1 - depth, x0 + (i + 1) * w, n1) });
          els.push({ type: 'way', id: id++, tags: heightTags(), geometry: rect(x0 + i * w, n0, x0 + (i + 1) * w, n0 + depth) });
        }
      } else {
        // edificio basso con una torre
        els.push({ type: 'way', id: id++, tags: { building: 'commercial', height: '8' }, geometry: rect(x0, n0, x1, n1) });
        const cx = (x0 + x1) / 2, cn = (n0 + n1) / 2;
        els.push({ type: 'way', id: id++, tags: { building: 'office', height: String(Math.round(32 + rnd() * 16)) }, geometry: rect(cx - 9, cn - 9, cx + 9, cn + 9) });
      }
    }
  }
  return els;
}
