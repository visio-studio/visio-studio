import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { makeProjection, geocode, parseCoords } from './geo.js';
import { fetchBuildings, buildBuildingsMesh } from './buildings.js';
import { buildGround } from './ground.js';
import { sunPosition, sunTimes, cardinal } from './sun.js';
import { zoneFor, zonedToUtc, fmtTime, todayInZone, pad, minutesToHHMM } from './time.js';
import { sampleElements } from './sample.js';
import { zipSync } from 'three/examples/jsm/libs/fflate.module.js';

// Modalità anteprima (pagina su claude.ai): i server esterni sono bloccati,
// quindi si parte da un quartiere di esempio e si possono caricare file OSM.
const PREVIEW = import.meta.env.MODE === 'preview-artifact';

const $ = (id) => document.getElementById(id);

// ---------------- stato ----------------
const state = {
  lat: 41.89921, lon: 12.47306, radius: 300, tz: 'Europe/Rome',
  y: 2026, m: 6, d: 21, minutes: 600,
  playing: false, speed: 60,
  proj: null, elements: [], uploaded: null, loadToken: 0, osmOk: false,
};
{
  const t = todayInZone(state.tz);
  Object.assign(state, { y: t.y, m: t.m, d: t.d, minutes: 600 });
}
readHash();

// ---------------- scena ----------------
const container = $('viewport');
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 3, 12000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI / 2 - 0.03;
controls.minDistance = 15;
controls.maxDistance = 5000;

const hemi = new THREE.HemisphereLight(0xdde8ff, 0x8a8070, 0.6);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 3);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.0002;
sun.shadow.normalBias = 0.35;
scene.add(sun, sun.target);

const outer = new THREE.Mesh(
  new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ color: 0xd9d4c8, roughness: 1 })
);
outer.receiveShadow = true;
outer.position.y = -0.6; // sotto la mappa, abbastanza da non contendersi la profondità (sfarfallio)
outer.name = 'Terreno';
scene.add(outer);

const world = new THREE.Group(); // edifici OSM
const groundGroup = new THREE.Group(); // mappa al suolo
const userModels = new THREE.Group(); // modello di progetto
const pathGroup = new THREE.Group(); // percorso solare (non esportato)
scene.add(world, groundGroup, userModels, pathGroup);

const sunMarker = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), new THREE.MeshBasicMaterial({ color: 0xffd34d }));
scene.add(sunMarker);

const SKY_DAY = new THREE.Color(0xbcd4ec);
const SKY_LOW = new THREE.Color(0xe9c39a);
const SKY_NIGHT = new THREE.Color(0x0b1020);
const SUN_WHITE = new THREE.Color(0xfff6e8);
const SUN_WARM = new THREE.Color(0xffa860);
scene.background = SKY_DAY.clone();

function resize() {
  const w = container.clientWidth, h = container.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(container);
resize();

function resetView() {
  const R = state.radius;
  camera.position.set(-R * 0.85, R * 1.05, R * 1.25);
  controls.target.set(0, 0, 0);
  controls.update();
}

function disposeGroup(g) {
  g.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => { if (m.map) m.map.dispose(); m.dispose(); });
    }
  });
  g.clear();
}

function setStatus(msg, isErr = false, autoHideMs = 0) {
  const el = $('status');
  el.textContent = msg;
  el.classList.toggle('err', isErr);
  clearTimeout(setStatus.t);
  if (autoHideMs) setStatus.t = setTimeout(() => { el.textContent = ''; }, autoHideMs);
}

// ---------------- caricamento area ----------------
async function loadArea(preset = null) {
  const token = ++state.loadToken;
  const R = state.radius;
  state.proj = makeProjection(state.lat, state.lon);
  state.tz = zoneFor(state.lat, state.lon);
  state.elements = [];
  disposeGroup(world);
  disposeGroup(groundGroup);
  outer.scale.set(R * 10, 1, R * 10);

  const sc = sun.shadow.camera;
  const s = R * 1.3;
  Object.assign(sc, { left: -s, right: s, top: s, bottom: -s, near: 1, far: R * 8 });
  sc.updateProjectionMatrix();
  sunMarker.scale.setScalar(R * 0.025);

  rebuildSunPath();
  updateSun();
  writeHash();

  // Edifici forniti (file caricato o quartiere di esempio): niente download.
  const online = !PREVIEW && state.osmOk;
  if (preset || !online) {
    state.elements = preset || sampleElements(state.lat, state.lon);
    rebuildBuildings();
    if (!preset) {
      $('stat-buildings').textContent += ' · quartiere di esempio';
      setStatus(PREVIEW
        ? 'Anteprima: edifici di esempio. Carica un file OSM per un luogo reale.'
        : 'Edifici di esempio. Cerca un indirizzo per vedere un luogo reale.', false, 8000);
    } else setStatus('');
    if (!online) return;
  }
  if (preset) {
    buildGround(state.proj, R).then((g) => { if (token === state.loadToken) groundGroup.add(g); }).catch(() => {});
    return;
  }

  setStatus('');
  $('stat-buildings').textContent = 'Caricamento edifici in corso…';
  loader.start(token);
  buildGround(state.proj, R)
    .then((g) => {
      if (token === state.loadToken) { groundGroup.add(g); loader.step('map', 'ok'); }
      else { g.geometry.dispose(); g.material.map.dispose(); }
    })
    .catch(() => { if (token === state.loadToken) loader.step('map', 'err'); });

  try {
    const els = await fetchBuildings(state.lat, state.lon, R);
    if (token !== state.loadToken) return;
    state.elements = els;
    rebuildBuildings();
    loader.step('bld', 'ok');
    loader.done(token);
  } catch {
    if (token !== state.loadToken) return;
    loader.fail(token);
    $('stat-buildings').textContent = 'Edifici non caricati.';
  }
}

// Pannello di caricamento al centro: dice cosa sta arrivando e da quanto si aspetta.
const loader = (() => {
  const box = $('loading'), sec = $('ld-sec'), msg = $('ld-msg');
  let tok = 0, t0 = 0, iv = 0;
  const tick = () => {
    const s = Math.round((performance.now() - t0) / 1000);
    sec.textContent = s + ' s';
    if (s >= 12) msg.textContent = 'I server pubblici di OpenStreetMap oggi sono lenti: di solito rispondono entro 30 secondi.';
  };
  const step = (k, st) => {
    const el = box.querySelector(`[data-step="${k}"]`);
    if (el) el.dataset.st = st;
  };
  return {
    start(t) {
      tok = t; t0 = performance.now();
      box.classList.remove('err');
      box.querySelectorAll('[data-step]').forEach((e) => { e.dataset.st = 'wait'; });
      $('ld-title').textContent = 'Carico il quartiere';
      msg.textContent = 'Mappa e altezze degli edifici arrivano da OpenStreetMap.';
      $('ld-retry').hidden = true;
      box.hidden = false;
      clearInterval(iv); tick(); iv = setInterval(tick, 500);
    },
    step,
    done(t) { if (t !== tok) return; clearInterval(iv); setTimeout(() => { if (t === tok) box.hidden = true; }, 450); },
    fail(t) {
      if (t !== tok) return;
      clearInterval(iv);
      step('bld', 'err');
      box.classList.add('err');
      $('ld-title').textContent = 'Edifici non arrivati';
      msg.textContent = 'I server degli edifici sono tutti occupati in questo momento. Riprova tra qualche secondo: la mappa resta visibile.';
      $('ld-retry').hidden = false;
    },
    hide() { tok = 0; clearInterval(iv); box.hidden = true; },
  };
})();
$('ld-retry').addEventListener('click', () => loadArea(state.uploaded));
$('ld-close').addEventListener('click', () => loader.hide());

function rebuildBuildings() {
  disposeGroup(world);
  const res = buildBuildingsMesh(state.elements, state.proj, { hideAt: $('hideCenter').checked ? [0, 0] : null });
  if (res.mesh) world.add(res.mesh);
  $('stat-buildings').textContent = res.count
    ? `${res.count} edifici nel raggio di ${state.radius} m · ${res.estimated} con altezza stimata`
    : 'Nessun edificio trovato in OpenStreetMap.';
}

// ---------------- sole ----------------
function currentDate() {
  return zonedToUtc(state.y, state.m, state.d, state.minutes, state.tz);
}

function makeLabel(text, color = '#f2f0ec') {
  const c = document.createElement('canvas');
  c.width = 96; c.height = 48;
  const ctx = c.getContext('2d');
  ctx.font = '600 30px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = 6;
  ctx.strokeStyle = 'rgba(0,0,0,0.55)';
  ctx.strokeText(text, 48, 24);
  ctx.fillStyle = color;
  ctx.fillText(text, 48, 24);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthWrite: false, transparent: true }));
  return sp;
}

function rebuildSunPath() {
  disposeGroup(pathGroup);
  const Rd = state.radius * 0.9;
  const { lat, lon, tz } = state;

  const addPath = (y, m, d, color, opacity) => {
    let seg = [];
    const segs = [];
    for (let min = 0; min <= 1440; min += 5) {
      const s = sunPosition(zonedToUtc(y, m, d, min, tz), lat, lon);
      if (s.alt > 0) seg.push(new THREE.Vector3(s.dir.x * Rd, s.dir.y * Rd, s.dir.z * Rd));
      else if (seg.length) { segs.push(seg); seg = []; }
    }
    if (seg.length) segs.push(seg);
    for (const pts of segs) {
      if (pts.length < 2) continue;
      pathGroup.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color, transparent: true, opacity })
      ));
    }
  };
  addPath(state.y, 6, 21, 0xff9f43, 0.45); // solstizio d'estate (emisfero nord)
  addPath(state.y, 12, 21, 0x5aa9ff, 0.45); // solstizio d'inverno
  addPath(state.y, state.m, state.d, 0xffd34d, 1);

  // marcatori orari sul giorno selezionato
  const dotGeo = new THREE.SphereGeometry(state.radius * 0.008, 10, 8);
  const dotMat = new THREE.MeshBasicMaterial({ color: 0xffd34d });
  for (let h = 0; h < 24; h++) {
    const s = sunPosition(zonedToUtc(state.y, state.m, state.d, h * 60, tz), lat, lon);
    if (s.alt <= 0) continue;
    const p = new THREE.Vector3(s.dir.x, s.dir.y, s.dir.z).multiplyScalar(Rd);
    const dot = new THREE.Mesh(dotGeo, dotMat);
    dot.position.copy(p);
    pathGroup.add(dot);
    const lbl = makeLabel(String(h));
    lbl.position.copy(p).multiplyScalar(1.06);
    lbl.scale.set(state.radius * 0.07, state.radius * 0.035, 1);
    pathGroup.add(lbl);
  }

  // orizzonte e punti cardinali
  const ring = [];
  for (let i = 0; i <= 128; i++) {
    const a = (i / 128) * Math.PI * 2;
    ring.push(new THREE.Vector3(Math.cos(a) * Rd, 0.2, Math.sin(a) * Rd));
  }
  pathGroup.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(ring),
    new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 })
  ));
  const card = [['N', 0, -1], ['E', 1, 0], ['S', 0, 1], ['O', -1, 0]];
  for (const [t, x, z] of card) {
    const l = makeLabel(t, t === 'N' ? '#f2b134' : '#f2f0ec');
    l.position.set(x * Rd * 1.07, state.radius * 0.03, z * Rd * 1.07);
    l.scale.set(state.radius * 0.1, state.radius * 0.05, 1);
    pathGroup.add(l);
  }
  pathGroup.visible = $('showPath').checked;
}

function updateSun() {
  const date = currentDate();
  const s = sunPosition(date, state.lat, state.lon);
  const R = state.radius;
  const D = R * 3;
  sun.position.set(s.dir.x * D, s.dir.y * D, s.dir.z * D);
  sun.target.position.set(0, 0, 0);

  const up = s.alt > 0;
  const k = Math.max(0, Math.min(1, s.altDeg / 20)); // 0 all'orizzonte, 1 sopra 20°
  sun.intensity = up ? 0.6 + 2.6 * Math.min(1, Math.sin(s.alt) * 2.5) : 0;
  sun.color.copy(SUN_WARM).lerp(SUN_WHITE, k);
  hemi.intensity = up ? 0.3 + 0.45 * k : Math.max(0.06, 0.3 + s.altDeg / 20);
  if (up) scene.background.copy(SKY_LOW).lerp(SKY_DAY, k);
  else scene.background.copy(SKY_LOW).lerp(SKY_NIGHT, Math.min(1, -s.altDeg / 8));

  const Rd = R * 0.9;
  sunMarker.visible = up;
  sunMarker.position.set(s.dir.x * Rd, s.dir.y * Rd, s.dir.z * Rd);

  // pannello dati
  $('i-time').textContent = `${minutesToHHMM(state.minutes)}`;
  $('i-alt').textContent = `${s.altDeg.toFixed(1)}°`;
  $('i-az').textContent = `${s.bearing.toFixed(1)}° ${cardinal(s.bearing)}`;
  const times = sunTimes(zonedToUtc(state.y, state.m, state.d, 720, state.tz), state.lat, state.lon);
  $('i-rise').textContent = fmtTime(times.sunrise, state.tz);
  $('i-set').textContent = fmtTime(times.sunset, state.tz);
  $('i-shadow').textContent = s.altDeg > 0.5
    ? `Un elemento alto 10 m proietta un'ombra di ${(10 / Math.tan(s.alt)).toFixed(1)} m verso ${cardinal((s.bearing + 180) % 360)}.`
    : 'Il sole è sotto l’orizzonte.';
  $('timeVal').textContent = minutesToHHMM(state.minutes);
  $('time').value = Math.floor(state.minutes);
}

// ---------------- URL condivisibile ----------------
// #lat,lon,AAAA-MM-GG,HH:MM,raggio
function readHash() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (!h) return;
  const [la, lo, date, time, r] = h.split(',');
  const lat = parseFloat(la), lon = parseFloat(lo);
  if (!isNaN(lat) && !isNaN(lon)) { state.lat = lat; state.lon = lon; }
  const dm = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || '');
  if (dm) { state.y = +dm[1]; state.m = +dm[2]; state.d = +dm[3]; }
  const tm = /^(\d{1,2}):(\d{2})$/.exec(time || '');
  if (tm) state.minutes = +tm[1] * 60 + +tm[2];
  if ([150, 300, 500].includes(+r)) state.radius = +r;
}

function writeHash() {
  clearTimeout(writeHash.t);
  writeHash.t = setTimeout(() => {
    const h = `${state.lat.toFixed(5)},${state.lon.toFixed(5)},${state.y}-${pad(state.m)}-${pad(state.d)},${minutesToHHMM(state.minutes)},${state.radius}`;
    history.replaceState(null, '', '#' + h);
  }, 300);
}

// ---------------- interfaccia ----------------
function syncDateInput() {
  $('date').value = `${state.y}-${pad(state.m)}-${pad(state.d)}`;
}

$('search').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = $('q').value.trim();
  if (!q) return;
  if (!PREVIEW && !state.osmOk && !parseCoords(q)) { askConsent(); return; }
  setStatus('Cerco…');
  try {
    const r = await geocode(q);
    if (!r) { setStatus('Nessun risultato trovato.', true); return; }
    state.lat = r.lat; state.lon = r.lon;
    state.uploaded = null;
    $('q').value = r.label.split(',').slice(0, 3).join(',');
    await loadArea();
  } catch {
    setStatus(PREVIEW
      ? 'In anteprima la ricerca per indirizzo non è disponibile: scrivi le coordinate (es. 41.9, 12.49) o carica un file OSM.'
      : 'Ricerca non riuscita: prova con le coordinate (es. 41.9, 12.49).', true);
  }
});

// ---------------- file OSM (JSON di Overpass) ----------------
$('importOsm').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  e.target.value = '';
  if (!f) return;
  try {
    const j = JSON.parse(await f.text());
    const els = (j.elements || []).filter((el) => el.geometry || el.members);
    const pts = [];
    for (const el of els) {
      if (el.geometry) pts.push(...el.geometry);
      for (const m of el.members || []) if (m.geometry) pts.push(...m.geometry);
    }
    if (!pts.length) throw new Error('vuoto');
    let a = 90, b = 180, c = -90, d = -180;
    for (const p of pts) { a = Math.min(a, p.lat); b = Math.min(b, p.lon); c = Math.max(c, p.lat); d = Math.max(d, p.lon); }
    state.lat = (a + c) / 2;
    state.lon = (b + d) / 2;
    const ext = Math.max((c - a) * 111320, (d - b) * 111320 * Math.cos((state.lat * Math.PI) / 180)) / 2;
    state.radius = ext > 300 ? 500 : ext > 150 ? 300 : 150;
    $('radius').value = String(state.radius);
    $('q').value = `${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`;
    state.uploaded = els;
    resetView();
    await loadArea(els);
  } catch {
    setStatus('File non valido: serve l’esportazione “raw OSM data” (JSON) di overpass-turbo con “out geom”.', true, 9000);
  }
});

$('radius').addEventListener('change', (e) => {
  state.radius = +e.target.value;
  resetView();
  loadArea(state.uploaded);
});
$('showMap').addEventListener('change', (e) => { groundGroup.visible = e.target.checked; });
$('showPath').addEventListener('change', (e) => { pathGroup.visible = e.target.checked; });
$('hideCenter').addEventListener('change', () => { if (state.elements.length) rebuildBuildings(); });

$('date').addEventListener('change', (e) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(e.target.value);
  if (!m) return;
  state.y = +m[1]; state.m = +m[2]; state.d = +m[3];
  rebuildSunPath(); updateSun(); writeHash();
});
$('time').addEventListener('input', (e) => {
  state.minutes = +e.target.value;
  updateSun(); writeHash();
});
document.querySelectorAll('[data-preset]').forEach((b) =>
  b.addEventListener('click', () => {
    const p = b.dataset.preset;
    if (p === 'today') {
      const t = todayInZone(state.tz);
      Object.assign(state, { y: t.y, m: t.m, d: t.d, minutes: t.minutes });
    } else {
      state.m = { winter: 12, equinox: 3, summer: 6 }[p];
      state.d = 21;
    }
    syncDateInput(); rebuildSunPath(); updateSun(); writeHash();
  })
);

function setPlaying(v) {
  state.playing = v;
  $('play').textContent = v ? '❚❚' : '▶';
  $('play').setAttribute('aria-label', v ? 'Pausa' : 'Riproduci');
}
$('play').addEventListener('click', () => setPlaying(!state.playing));
$('speed').addEventListener('change', (e) => { state.speed = +e.target.value; });
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !['INPUT', 'SELECT'].includes(document.activeElement?.tagName)) {
    e.preventDefault(); setPlaying(!state.playing);
  }
});
$('resetView').addEventListener('click', resetView);
$('infoToggle').addEventListener('click', () => $('info').classList.toggle('open'));

// ---------------- modello di progetto ----------------
const gltfLoader = new GLTFLoader();
let modelPivot = null;

function clearModel() {
  if (modelPivot) { disposeGroup(modelPivot); userModels.remove(modelPivot); modelPivot = null; }
}
$('importModel').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const url = URL.createObjectURL(f);
  try {
    const g = await gltfLoader.loadAsync(url);
    clearModel();
    const root = g.scene;
    root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const box = new THREE.Box3().setFromObject(root);
    root.position.x -= (box.min.x + box.max.x) / 2;
    root.position.z -= (box.min.z + box.max.z) / 2;
    root.position.y -= box.min.y;
    modelPivot = new THREE.Group();
    modelPivot.name = 'Modello_progetto';
    modelPivot.add(root);
    modelPivot.rotation.y = -THREE.MathUtils.degToRad(+$('modelRot').value);
    userModels.add(modelPivot);
    const sz = box.getSize(new THREE.Vector3());
    setStatus(`Modello caricato: ${sz.x.toFixed(1)} × ${sz.z.toFixed(1)} m, alto ${sz.y.toFixed(1)} m (unità attese: metri).`, false, 6000);
  } catch {
    setStatus('Impossibile leggere il file: usa un .glb.', true, 6000);
  } finally {
    URL.revokeObjectURL(url);
    e.target.value = '';
  }
});
$('modelRot').addEventListener('input', (e) => {
  $('modelRotVal').textContent = `${e.target.value}°`;
  if (modelPivot) modelPivot.rotation.y = -THREE.MathUtils.degToRad(+e.target.value);
});
$('clearModel').addEventListener('click', clearModel);

// ---------------- esportazioni ----------------
function stamp() {
  return `${state.y}${pad(state.m)}${pad(state.d)}-${minutesToHHMM(state.minutes).replace(':', '')}`;
}
// Su claude.ai i download passano dalla conferma della pagina (e il .glb va dentro uno .zip);
// altrove si usa il normale link di download.
let downloadsApi;
async function getDownloads() {
  if (downloadsApi !== undefined) return downloadsApi;
  downloadsApi = window.claude?.use ? await window.claude.use('downloads').catch(() => null) : null;
  return downloadsApi;
}
async function download(blob, name) {
  const dl = await getDownloads();
  if (dl) {
    let data = blob, filename = name;
    if (name.endsWith('.glb')) {
      const bytes = new Uint8Array(await blob.arrayBuffer());
      data = new Blob([zipSync({ [name]: bytes }, { level: 0 })]);
      filename = name.replace(/\.glb$/, '.zip');
    }
    try {
      await dl.save({ filename, data });
      return true;
    } catch (e) {
      if (e?.code !== 'declined') setStatus('Salvataggio non disponibile in questa vista.', true, 6000);
      return false;
    }
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  return true;
}

$('exportPng').addEventListener('click', () => {
  renderer.render(scene, camera);
  renderer.domElement.toBlob((b) => b && download(b, `visio-ombre-${stamp()}.png`), 'image/png');
});

$('exportGlb').addEventListener('click', async () => {
  const exp = new THREE.Scene();
  for (const g of [world, userModels]) g.children.forEach((c) => exp.add(c.clone(true)));
  if (groundGroup.visible) groundGroup.children.forEach((c) => exp.add(c.clone(true)));
  const ground = outer.clone();
  exp.add(ground);

  const L = new THREE.DirectionalLight(0xffffff, 3);
  L.name = `Sole_${state.y}-${pad(state.m)}-${pad(state.d)}_${minutesToHHMM(state.minutes)}`;
  L.position.copy(sun.position);
  L.lookAt(0, 0, 0);
  L.add(L.target);
  L.target.position.set(0, 0, -1);
  exp.add(L);

  setStatus('Preparo il file GLB…');
  try {
    const buf = await new GLTFExporter().parseAsync(exp, { binary: true });
    setStatus('');
    const ok = await download(new Blob([buf], { type: 'model/gltf-binary' }), `visio-scena-${stamp()}.glb`);
    if (!ok) return;
    const s = sunPosition(currentDate(), state.lat, state.lon);
    setStatus(`Esportato. Sole: altezza ${s.altDeg.toFixed(1)}°, azimut ${s.bearing.toFixed(1)}°. Origine = punto cercato, unità in metri.`, false, 9000);
  } catch {
    setStatus('Esportazione non riuscita.', true, 6000);
  }
});

// ---------------- ciclo di rendering ----------------
const timer = new THREE.Timer();
const rose = document.querySelector('#compass .rose');
function tick() {
  timer.update();
  const dt = Math.min(timer.getDelta(), 0.1);
  if (state.playing) {
    state.minutes = (state.minutes + state.speed * dt) % 1440;
    updateSun();
    writeHash();
  }
  controls.update();
  rose.style.transform = `rotate(${controls.getAzimuthalAngle()}rad)`;
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

// avvio
$('radius').value = String(state.radius);
syncDateInput();
// Consenso alle mappe reali: i server OpenStreetMap ricevono l'IP di chi usa lo strumento,
// quindi si contattano solo dopo una scelta esplicita (ricordata in questo browser).
const OSM_KEY = 'visio-sole-osm';
try { state.osmOk = localStorage.getItem(OSM_KEY) === '1'; } catch { /* storage bloccato */ }
let consentPending = null; // ricerca da ripetere dopo il consenso
function askConsent() {
  consentPending = $('q').value.trim() || null;
  $('consent').hidden = false;
  $('cs-ok').focus();
}
$('cs-ok').addEventListener('click', () => {
  state.osmOk = true;
  try { localStorage.setItem(OSM_KEY, '1'); } catch { /* ok */ }
  $('consent').hidden = true;
  if (consentPending) $('search').requestSubmit();
  else if (!state.uploaded) loadArea();
});
$('cs-no').addEventListener('click', () => { $('consent').hidden = true; consentPending = null; });
if (!PREVIEW && !state.osmOk) $('consent').hidden = false;

resetView();
loadArea();
tick();
