// Piano del terreno con le tile di OpenStreetMap disegnate su un canvas.
import * as THREE from 'three';

const TILE_URL = (z, x, y) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`;

function loadImage(src, timeout = 10000) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    const t = setTimeout(() => resolve(null), timeout);
    img.onload = () => { clearTimeout(t); resolve(img); };
    img.onerror = () => { clearTimeout(t); resolve(null); };
    img.src = src;
  });
}

export async function buildGround(proj, radius) {
  const z = radius > 400 ? 17 : 18;
  const n = 2 ** z;
  const lon2x = (lon) => ((lon + 180) / 360) * n;
  const lat2y = (lat) => {
    const r = (lat * Math.PI) / 180;
    return ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n;
  };
  const x2lon = (x) => (x / n) * 360 - 180;
  const y2lat = (y) => {
    const t = Math.PI - (2 * Math.PI * y) / n;
    return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(t) - Math.exp(-t)));
  };

  const ext = radius * 1.15;
  const nw = proj.toLatLon(-ext, ext);
  const se = proj.toLatLon(ext, -ext);
  const x0 = Math.floor(lon2x(nw.lon)), x1 = Math.floor(lon2x(se.lon));
  const y0 = Math.floor(lat2y(nw.lat)), y1 = Math.floor(lat2y(se.lat));

  const cols = x1 - x0 + 1, rows = y1 - y0 + 1;
  const canvas = document.createElement('canvas');
  canvas.width = cols * 256;
  canvas.height = rows * 256;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#e6e2d8';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const jobs = [];
  for (let ty = y0; ty <= y1; ty++) {
    for (let tx = x0; tx <= x1; tx++) {
      jobs.push(loadImage(TILE_URL(z, tx, ty)).then((img) => {
        if (img) ctx.drawImage(img, (tx - x0) * 256, (ty - y0) * 256);
      }));
    }
  }
  await Promise.all(jobs);

  const a = proj.toLocal(y2lat(y0), x2lon(x0)); // angolo NO
  const b = proj.toLocal(y2lat(y1 + 1), x2lon(x1 + 1)); // angolo SE
  const w = b.x - a.x, h = a.n - b.n;

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  const geo = new THREE.PlaneGeometry(w, h);
  geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: tex, roughness: 1, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }));
  mesh.position.set((a.x + b.x) / 2, 0.02, -(a.n + b.n) / 2);
  mesh.receiveShadow = true;
  mesh.name = 'Mappa_suolo';
  return mesh;
}
