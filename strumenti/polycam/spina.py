# Texture di parquet a spina di pesce in rovere, ripetibile senza giunture.
# Doghe L = 6 w (es. 54 x 9 cm): il disegno si ripete ogni 12 w in x e in y, quindi la piastrella è 12 w x 12 w.
# Uso: python -I spina.py uscita.jpg [px_per_doga=128] [seme=7]  -> stampa il lato della piastrella in doghe
import sys, numpy as np
from PIL import Image, ImageFilter
out = sys.argv[1]; w = int(sys.argv[2]) if len(sys.argv) > 2 else 128; rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
L = 6 * w; P = 12 * w
yy, xx = np.mgrid[0:P, 0:P]
# coppie a «L»: doga orizzontale [0,L)x[0,w) e verticale [0,w)x[w,w+L); reticolo v1=(w,w), v2=(L,-L).
# Per ogni pixel si cerca la doga che lo contiene fra le traslazioni vicine (in coordinate del reticolo, modulo P).
idx = -np.ones((P, P), np.int64); ori = np.zeros((P, P), np.int8); u = np.zeros((P, P)); v = np.zeros((P, P))
n = 0
for a in range(-14, 26):
    for b in range(-4, 6):
        ox, oy = a * w + b * L, a * w - b * L
        for o, (x0, y0, ww, hh) in enumerate(((ox, oy, L, w), (ox, oy + w, w, L))):
            for sx in (-P, 0, P):
                for sy in (-P, 0, P):
                    X0, Y0 = x0 + sx, y0 + sy
                    if X0 >= P or Y0 >= P or X0 + ww <= 0 or Y0 + hh <= 0: continue
                    m = (xx >= X0) & (xx < X0 + ww) & (yy >= Y0) & (yy < Y0 + hh)
                    # identità della doga uguale su tutte le copie periodiche: si usa la posizione modulo P
                    key = ((X0 % P) * 7919 + (Y0 % P)) * 2 + o
                    idx[m] = key; ori[m] = o
                    u[m] = (xx[m] - X0) if o == 0 else (yy[m] - Y0)   # lungo la doga
                    v[m] = (yy[m] - Y0) if o == 0 else (xx[m] - X0)   # di traverso
assert (idx >= 0).all(), 'buchi nel disegno'
keys = np.unique(idx); tono = {k: rng.normal(0, 1) for k in keys}; fase = {k: rng.uniform(0, 1000) for k in keys}
T = np.vectorize(tono.get)(idx); F = np.vectorize(fase.get)(idx)
# venatura: campo di rumore stirato (righe lunghe e sottili), letto nelle coordinate locali di ogni doga con uno
# scostamento casuale per doga, così due doghe vicine non hanno la stessa fibra
def striato(s, stira, morb):
    g = np.random.default_rng(s).normal(size=(P, max(8, P // stira)))
    im = Image.fromarray(((g - g.min()) / (g.max() - g.min()) * 255).astype(np.uint8)).resize((P, P), Image.BICUBIC)
    im = im.filter(ImageFilter.GaussianBlur(morb))
    a = np.asarray(im) / 255.0; return (a - a.mean()) / (a.std() + 1e-9)
G1 = striato(3, 60, 0.8); G2 = striato(5, 12, 2.5); Gm = striato(9, 4, 12)
oi = (F * 37).astype(np.int64) % P; oj = (F * 91).astype(np.int64) % P
ii = (v.astype(np.int64) * 2 + oi) % P; jj = (u.astype(np.int64) + oj) % P
fib = 0.55 * G1[ii, jj] + 0.35 * G2[ii, jj] + 0.25 * Gm[ii, jj]
base = np.array([176, 131, 86], float)       # rovere naturale caldo, come nei render
col = base[None, None, :] * (1 + 0.07 * T[..., None]) * (1 + 0.075 * fib[..., None])
col = col * np.array([1.0, 0.99, 0.965])[None, None, :]
# fuga scura e leggero smusso ai bordi di ogni doga
bord = np.minimum(np.minimum(u, L - 1 - u) / L * 6, np.minimum(v, w - 1 - v) / w * 1.0)
bord = np.minimum(u, np.minimum(L - 1 - u, np.minimum(v, w - 1 - v)))
col *= np.clip(0.55 + bord / 3.0, 0.55, 1.0)[..., None]
img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
img.save(out, quality=90, optimize=True)
print('piastrella', P, 'px =', 12, 'doghe di larghezza')
