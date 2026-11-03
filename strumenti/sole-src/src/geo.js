// Proiezione locale in metri attorno a un punto di origine (x = est, n = nord).
// Per aree di pochi km l'errore rispetto a una proiezione esatta è trascurabile.
const M_PER_DEG = 111320;

export function makeProjection(lat0, lon0) {
  const kx = M_PER_DEG * Math.cos((lat0 * Math.PI) / 180);
  return {
    lat0,
    lon0,
    toLocal(lat, lon) {
      return { x: (lon - lon0) * kx, n: (lat - lat0) * M_PER_DEG };
    },
    toLatLon(x, n) {
      return { lat: lat0 + n / M_PER_DEG, lon: lon0 + x / kx };
    },
  };
}

export function parseCoords(s) {
  const m = s.trim().match(/^(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const lat = parseFloat(m[1]);
  const lon = parseFloat(m[2]);
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat, lon };
}

// Geocoding con Nominatim (OpenStreetMap). Accetta anche "lat, lng".
export async function geocode(q) {
  const c = parseCoords(q);
  if (c) return { ...c, label: `${c.lat.toFixed(5)}, ${c.lon.toFixed(5)}` };
  const url =
    'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=it&q=' +
    encodeURIComponent(q);
  const r = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!r.ok) throw new Error('Ricerca non riuscita');
  const j = await r.json();
  if (!j.length) return null;
  return { lat: parseFloat(j[0].lat), lon: parseFloat(j[0].lon), label: j[0].display_name };
}
