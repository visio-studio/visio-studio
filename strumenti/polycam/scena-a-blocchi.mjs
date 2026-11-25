// Scena Polycam (GLB) -> formato del visore 3D (nome.json + nome.bin + una texture per blocco, come converti.py),
// già messa nel riferimento del modello di progetto: matrice dell'allineamento (allinea-mario.py, chiave M4) e poi lo
// stesso spostamento che il visore dà al progetto (centro in pianta e pavimento più basso a zero).
// uso: node scena-a-blocchi.mjs scena.glb allineamento.json progetto.glb cartella nome
// Le texture escono come nomeN.src.jpg (originali): vanno ridotte a parte (riduci-texture.py) in nomeN.jpg.
import {NodeIO, getBounds} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {MeshoptDecoder} from 'meshoptimizer';import {writeFileSync,readFileSync} from 'fs';
const [,, glb, alj, prog, out, nome] = process.argv;
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder': MeshoptDecoder});
const P = await io.read(prog); const bb = getBounds(P.getRoot().listScenes()[0]);
const off = [-(bb.min[0] + bb.max[0]) / 2, -bb.min[1], -(bb.min[2] + bb.max[2]) / 2];
const M4 = JSON.parse(readFileSync(alj, 'utf8')).M4;   // righe
const doc = await io.read(glb); const sc = doc.getRoot().listScenes()[0];
const mul = (m, v) => [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12], m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13], m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
const al = v => [0, 1, 2].map(i => M4[i][0]*v[0]+M4[i][1]*v[1]+M4[i][2]*v[2]+M4[i][3] + off[i]);
const parti = []; let len = 0; const meta = []; const texs = [];
const pad = () => { const n = (4 - len % 4) % 4; if (n) { parti.push(Buffer.alloc(n)); len += n; } };
const put = b => { pad(); const o = len; parti.push(Buffer.from(b.buffer, b.byteOffset, b.byteLength)); len += b.byteLength; return o; };
const gmn = [1e9, 1e9, 1e9], gmx = [-1e9, -1e9, -1e9];
sc.traverse(n => { const me = n.getMesh(); if (!me) return; const W = n.getWorldMatrix();
  for (const p of me.listPrimitives()) {
    const pos = p.getAttribute('POSITION'), uv = p.getAttribute('TEXCOORD_0'), ix = p.getIndices(); const nv = pos.getCount();
    if (nv > 65535) throw new Error('blocco troppo grande');
    const tex = p.getMaterial().getBaseColorTexture(); let ti = texs.indexOf(tex); if (ti < 0) { texs.push(tex); ti = texs.length - 1; }
    const V = new Float64Array(nv * 3), t = [0, 0, 0]; const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (let i = 0; i < nv; i++) { const w = al(mul(W, pos.getElement(i, t))); for (let a = 0; a < 3; a++) { V[3*i+a] = w[a]; mn[a] = Math.min(mn[a], w[a]); mx[a] = Math.max(mx[a], w[a]); } }
    for (let a = 0; a < 3; a++) { gmn[a] = Math.min(gmn[a], mn[a]); gmx[a] = Math.max(gmx[a], mx[a]); }
    const q = new Uint16Array(nv * 3); for (let i = 0; i < nv * 3; i++) { const a = i % 3; q[i] = Math.round((V[i] - mn[a]) / Math.max(mx[a] - mn[a], 1e-9) * 65535); }
    const u = new Uint16Array(nv * 2), e2 = [0, 0]; for (let i = 0; i < nv; i++) { uv.getElement(i, e2); u[2*i] = Math.round(Math.min(1, Math.max(0, e2[0])) * 65535); u[2*i+1] = Math.round(Math.min(1, Math.max(0, e2[1])) * 65535); }
    const ni = ix.getCount(); const I = new Uint16Array(ni); for (let i = 0; i < ni; i++) I[i] = ix.getScalar(i);
    const e = {tex: `${nome}${ti}.jpg`, min: mn, max: mx, nv, ni};
    e.pos = put(q); e.uv = put(u); e.idx = put(I); meta.push(e);
  } });
texs.forEach((t, i) => writeFileSync(`${out}/${nome}${i}.src.jpg`, Buffer.from(t.getImage())));
writeFileSync(`${out}/${nome}.bin`, Buffer.concat(parti));
writeFileSync(`${out}/${nome}.json`, JSON.stringify({versione: 1, bin: `${nome}.bin`, min: gmn.map(v => +v.toFixed(3)), max: gmx.map(v => +v.toFixed(3)), mesh: meta}));
console.log(nome, meta.length, 'blocchi', Math.round(len / 1024), 'KB', 'texture', texs.length, 'ingombro', gmn.map(v => v.toFixed(2)), gmx.map(v => v.toFixed(2)), 'spostamento progetto', off.map(v => v.toFixed(3)));
