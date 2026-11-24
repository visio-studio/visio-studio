# Progetto Mario: allineamento in pianta della scansione unica (scena Polycam) al modello di progetto, solo numpy
# (SciPy qui non parte: DLL bloccate da Smart App Control).
# uso: python -I allinea-mario.py tri.bin sez-modello.json uscita.json
#   tri.bin = triangoli-glb.mjs sulla scena; sez-modello.json = sezione-glb.mjs del modello a 1,20 m dal pavimento
# Muri della scansione = celle di 5 cm tagliate sia a 1,20 m sia a 1,90 m dal pavimento (gli arredi bassi spariscono).
# Rotazione (anche specchiata) per correlazione FFT con i muri del modello, poi rifinitura ICP 2D.
# Scrive pavimento della scansione, matrice 4x4 scansione -> modello (y: pavimento della scansione sul pavimento
# del modello, 0,37 m) e quanti punti dei muri cadono entro 5 e 15 cm.
import sys, json, numpy as np
tri, sez, OUT = sys.argv[1:4]
T = np.fromfile(tri, '<f4').reshape(-1, 3, 3).astype(float)
PAV_MOD = 0.37; R = 0.05
# pavimento: quota più frequente dei triangoli quasi orizzontali nella metà bassa
n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ar = np.linalg.norm(n, axis=1) / 2; ny = np.abs(n[:, 1]) / (2 * ar + 1e-12)
cy = T[:, :, 1].mean(1); y0, y1 = cy.min(), cy.max()
k = (ny > 0.95) & (cy < (y0 + y1) / 2)
h, e = np.histogram(cy[k], bins=np.arange(y0, (y0 + y1) / 2, 0.01), weights=ar[k]); PAV = float(e[h.argmax()] + 0.005)
print('pavimento scansione', round(PAV, 3), 'altezza', round(y1 - y0, 2))
def sezione(h):
    y = T[:, :, 1] - h; s = np.sign(y); t = T[~((s[:, 0] == s[:, 1]) & (s[:, 1] == s[:, 2]))]; y = t[:, :, 1] - h; seg = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ya, yb = y[:, a], y[:, b]; c = ya * yb < 0; u = np.where(c, ya / (ya - yb + 1e-12), 0)
        seg.append(np.where(c[:, None], t[:, a] + (t[:, b] - t[:, a]) * u[:, None], np.nan))
    P = np.stack(seg, 1)  # tri x 3 lati x 3
    out = []
    for i in range(len(P)):
        q = P[i][~np.isnan(P[i][:, 0])]
        if len(q) == 2: out.append([q[0, 0], q[0, 2], q[1, 0], q[1, 2]])
    return np.array(out)
def celle(seg):
    # punti campionati lungo i segmenti ogni 2 cm -> insieme di celle
    a, b = seg[:, :2], seg[:, 2:]; L = np.linalg.norm(b - a, axis=1); k = np.maximum(1, np.ceil(L / 0.02)).astype(int)
    idx = np.repeat(np.arange(len(seg)), k); t = (np.arange(k.sum()) - np.repeat(np.cumsum(k) - k, k)) / np.repeat(k, k)
    p = a[idx] + (b[idx] - a[idx]) * t[:, None]; return set(map(tuple, np.floor(p / R).astype(int)))
S1 = sezione(PAV + 1.2); S2 = sezione(PAV + 1.9)
c1, c2 = celle(S1), celle(S2)
dil = lambda c: {(i + a, j + b) for i, j in c for a in (-1, 0, 1) for b in (-1, 0, 1)}
muri_s = np.array(sorted(dil(c1) & dil(c2)), float) * R + R / 2
print('segmenti scansione', len(S1), len(S2), 'celle muro', len(muri_s))
M = json.load(open(sez)); mw = np.array(M['51:Gruppo#20'])
muri_m = np.array(sorted(celle(mw)), float) * R + R / 2
print('celle muro modello', len(muri_m))
def immagine(p, o, sh):
    I = np.zeros(sh, np.float32); ij = np.floor((p - o) / R).astype(int); k = (ij >= 0).all(1) & (ij[:, 0] < sh[0]) & (ij[:, 1] < sh[1]); I[ij[k, 0], ij[k, 1]] = 1; return I
def sfoca(I):
    k = np.array([1, 4, 6, 4, 1], np.float32); k /= k.sum()
    for ax in (0, 1): I = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), ax, I)
    return I
def rot(th, mir):
    c, s = np.cos(th), np.sin(th); Rm = np.array([[c, -s], [s, c]]); return Rm @ np.diag([-1, 1]) if mir else Rm
om = muri_m.min(0) - 8; sh = tuple(int(v) for v in (muri_m.max(0) - om) / R + 320)
sh = (int(2 ** np.ceil(np.log2(sh[0]))), int(2 ** np.ceil(np.log2(sh[1]))))
Fm = np.fft.rfft2(sfoca(immagine(muri_m, om, sh)))
cs = muri_s.mean(0)
def prova(deg, mir):
    q = (muri_s - cs) @ rot(np.radians(deg), mir).T; oq = q.min(0); Iq = immagine(q, oq, sh)
    c = np.fft.irfft2(Fm * np.conj(np.fft.rfft2(Iq)), sh); k = np.unravel_index(np.argmax(c), c.shape)
    return c[k] / len(q), om + np.array(k) * R - oq
best = (-1,)
for mir in (False, True):
    for deg in np.arange(0, 360, 1.0):
        sc, t = prova(deg, mir)
        if sc > best[0]: best = (sc, deg, mir, t)
for deg in np.arange(best[1] - 1, best[1] + 1.01, 0.1):
    sc, t = prova(deg, best[2])
    if sc > best[0]: best = (sc, deg, best[2], t)
sc, deg, mir, t = best; print('correlazione', round(float(sc), 3), 'rotazione', round(float(deg), 1), 'specchiata', mir)
A = rot(np.radians(deg), mir); b = t - cs @ A.T
def vicini(q, P):
    d = np.full(len(q), 1e9); i = np.zeros(len(q), int)
    for s in range(0, len(P), 2000):
        D = ((q[:, None, :] - P[None, s:s + 2000, :]) ** 2).sum(2); j = D.argmin(1); dd = D[np.arange(len(q)), j]; m = dd < d; d[m] = dd[m]; i[m] = j[m] + s
    return np.sqrt(d), i
for it in range(30):
    q = muri_s @ A.T + b; d, i = vicini(q, muri_m); k = d < (0.3 if it < 10 else 0.15)
    X = muri_s[k] @ (np.diag([-1, 1]) if mir else np.eye(2)); Y = muri_m[i[k]]; mx, my = X.mean(0), Y.mean(0)
    U, _, Vt = np.linalg.svd((X - mx).T @ (Y - my)); D = np.diag([1, np.sign(np.linalg.det(Vt.T @ U.T))]); Rr = Vt.T @ D @ U.T
    A = Rr @ (np.diag([-1, 1]) if mir else np.eye(2)); b = my - (muri_s[k].mean(0)) @ A.T
q = muri_s @ A.T + b; d, _ = vicini(q, muri_m)
res = dict(pavimento=PAV, A=A.tolist(), b=b.tolist(), specchiata=bool(mir), entro5cm=float((d < 0.05).mean()), entro15cm=float((d < 0.15).mean()),
           ang=float(np.degrees(np.arctan2(A[1, 0], A[0, 0]))))
# matrice 4x4 (x, y, z) scansione -> modello: x,z con A e b; y traslata sul pavimento del modello
M4 = np.eye(4); M4[0, 0], M4[0, 2], M4[2, 0], M4[2, 2] = A[0, 0], A[0, 1], A[1, 0], A[1, 1]; M4[0, 3], M4[2, 3] = b; M4[1, 3] = PAV_MOD - PAV
res['M4'] = M4.tolist(); json.dump(res, open(OUT, 'w'), indent=1)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items() if k not in ('A', 'M4')})
