# Progetto Mario: disegni ante operam, post operam e confronto (PNG a 200 px/m, stesso riquadro della pianta arredata).
# uso: python -I ante-post-mario.py tri.bin allineamento.json info.json sez-modello.json vista-scan.png pianta.png uscita_dir
#   tri.bin = triangoli-glb.mjs sulla scena Polycam; allineamento.json = allinea-mario.py; info.json, pianta.png =
#   orto-mario.html e pianta-mario.py; vista-scan.png = orto-mario.html ?foto&mat4=... sulla scansione, stesso riquadro.
# Stato attuale: vista dall'alto della scansione; muri = strisce non rilevate più strette di 50 cm fra zone rilevate. Confronto: muri di progetto vicini a muri rilevati = esistenti (grigio), il resto =
# nuovi (rosso); muri rilevati lontani dal progetto = da demolire (giallo). Solo numpy e PIL (SciPy bloccata qui).
import sys, json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
tri, alj, inf, sez, vsc, pia, OUT = sys.argv[1:8]
I = json.load(open(inf)); X0, Z0, PX = I['X0'], I['Z0'], I['PX']
W, H = Image.open(pia).size
M4 = np.array(json.load(open(alj))['M4'])
T = np.fromfile(tri, '<f4').reshape(-1, 3).astype(float); T = (np.c_[T, np.ones(len(T))] @ M4.T)[:, :3].reshape(-1, 3, 3)
PAV = 0.37
def sezione(h):
    y = T[:, :, 1] - h; s = np.sign(y); t = T[~((s[:, 0] == s[:, 1]) & (s[:, 1] == s[:, 2]))]; y = t[:, :, 1] - h; pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ya, yb = y[:, a], y[:, b]; c = ya * yb < 0; u = np.where(c, ya / (ya - yb + 1e-12), 0)
        pts.append(np.where(c[:, None], t[:, a] + (t[:, b] - t[:, a]) * u[:, None], np.nan))
    P = np.stack(pts, 1); ok = (~np.isnan(P[:, :, 0])).sum(1) == 2; P = P[ok]; m = ~np.isnan(P[:, :, 0])
    q = P[m].reshape(-1, 2, 3); return np.c_[q[:, 0, 0], q[:, 0, 2], q[:, 1, 0], q[:, 1, 2]]
def px(x, z): return ((x - X0) * PX, (z - Z0) * PX)
def raster(segs, w=3):
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for a, b, c, e in segs: d.line([px(a, b), px(c, e)], fill=255, width=w)
    return im
def filtro(im, f, n):
    for _ in range(n): im = im.filter(f(3))
    return im
B = lambda im: np.asarray(im) > 0
def img(m): return Image.fromarray((m * 255).astype(np.uint8))
def riempi(L, r):  # campisce le parti più strette di 2r fra le linee (apertura morfologica dello spazio libero)
    lib = img(~L); ap = filtro(filtro(lib, ImageFilter.MinFilter, r), ImageFilter.MaxFilter, r); return L | (~L & ~B(ap))
s12, s19, s24 = sezione(PAV + 1.2), sezione(PAV + 1.9), sezione(PAV + 2.4)
L12 = B(raster(s12)); L19d = B(filtro(raster(s19), ImageFilter.MaxFilter, 4)); L24d = B(filtro(raster(s24), ImageFilter.MaxFilter, 4))
LM = L12 & L19d & L24d   # linee presenti a 1,20, 1,90 e 2,40 m (gli arredi di rado arrivano a 2,40 m)
# muri di oggi: nella scansione sono le strisce non rilevate strette (meno di 50 cm) fra due zone rilevate
cov = np.asarray(Image.open(vsc).convert('L')) < 250
cov = B(filtro(filtro(img(cov), ImageFilter.MaxFilter, 3), ImageFilter.MinFilter, 3))   # chiude i buchini
gap = riempi(cov, int(0.25 * PX)) & ~cov
ante_pieno = B(filtro(filtro(img(gap), ImageFilter.MinFilter, 8), ImageFilter.MaxFilter, 8))   # via i filamenti sotto 8 cm
bordo = cov & ~B(filtro(img(cov), ImageFilter.MinFilter, 2))
S = json.load(open(sez)); post = riempi(B(raster(S['51:Gruppo#20'])), int(0.325 * PX))
# --- ante operam: vista dall'alto della scansione schiarita, bordo del rilievo e muri campiti ---
v = Image.open(vsc).convert('RGB'); a = np.asarray(v).astype(float); a = 255 - (255 - a) * 0.45
a[bordo] = (20, 20, 20); a[ante_pieno] = (24, 24, 24)
Image.fromarray(a.astype(np.uint8)).save(f'{OUT}/ante.png', optimize=True)
# --- confronto ---
# un muro di progetto è esistente se entro 45 cm c'è un muro di oggi o il bordo del rilievo (la faccia vista dalla stanza)
vicino_ante = B(filtro(img(ante_pieno | bordo), ImageFilter.MaxFilter, int(0.45 * PX)))
ril = B(filtro(img(cov), ImageFilter.MaxFilter, int(0.6 * PX)))   # zona rilevata, allargata di 60 cm
fuori = post & ~ril
esist = post & vicino_ante & ril
nuovi = post & ~esist & ~fuori
nuovi = B(filtro(filtro(img(nuovi), ImageFilter.MinFilter, 4), ImageFilter.MaxFilter, 4)); esist = post & ~nuovi & ~fuori
lontano_post = ~B(filtro(img(post), ImageFilter.MaxFilter, int(0.15 * PX)))
dem = ante_pieno & lontano_post
dem = B(filtro(filtro(img(dem), ImageFilter.MinFilter, 12), ImageFilter.MaxFilter, 12))   # via i buchi della scansione sotto 12 cm
# solo vicino all'appartamento di progetto (entro 1 m da un suo muro): fuori sono bordi di terrazzi e pianerottolo
dem &= B(filtro(img(post), ImageFilter.MaxFilter, int(1.0 * PX)))
c = np.full((H, W, 3), 255, np.uint8)
g = np.asarray(Image.open(pia).convert('RGB')).astype(float); g = g.mean(2, keepdims=True); c[:] = (255 - (255 - g) * 0.25).astype(np.uint8)
c[bordo] = (150, 170, 205); c[fuori] = (175, 175, 175); c[esist] = (95, 95, 95); c[dem] = (235, 180, 0); c[nuovi] = (210, 35, 35)
Image.fromarray(c).save(f'{OUT}/confronto.png', optimize=True)
Image.open(pia).convert('RGB').save(f'{OUT}/post.png', optimize=True)
m2 = lambda m: round(float(m.sum()) / PX ** 2, 1)
json.dump(dict(muri_ante_m2=m2(ante_pieno), muri_post_m2=m2(post), esistenti_m2=m2(esist), nuovi_m2=m2(nuovi), demoliti_m2=m2(dem), fuori_rilievo_m2=m2(fuori)), open(f'{OUT}/ante-post.json', 'w'), indent=1)
print(open(f'{OUT}/ante-post.json').read())
