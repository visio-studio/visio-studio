# Progetto Mario: disegno della pianta arredata (PNG) dalla vista dall'alto e dalla sezione dei muri.
# Uso: python -I pianta-mario.py vista.png sezione.json info.json uscita_dir [stanze.json = [[nome, x, z], ...]]
#   vista.png   = orto-mario.html (?px=200), sezione.json = sezione-glb.mjs a 1,20 m dal pavimento, info.json = window.INFO
# Muri del modello (gruppo «Gruppo#20»): le parti più strette di 65 cm fra le linee di sezione si campiscono in nero.
# Ogni stanza si misura riempiendola da un punto interno (superficie netta, porte comprese fino a metà muro circa).
# Le altre linee di sezione (arredi, infissi) in grigio. Scrive pianta.png (200 px/m) e stanze.json.
import sys, json, numpy as np
from PIL import Image, ImageDraw
from PIL import ImageFilter
vista, sez, info, OUT = sys.argv[1:5]
I = json.load(open(info)); X0, Z0, PX = I['X0'], I['Z0'], I['PX']
S = json.load(open(sez))
im = Image.open(vista).convert('RGB'); W, H = im.size
def px(x, z): return ((x - X0) * PX, (z - Z0) * PX)
muri = S.get('51:Gruppo#20', [])
lin = Image.new('L', (W, H), 0); d = ImageDraw.Draw(lin)
for a, b, c, e in muri: d.line([px(a, b), px(c, e)], fill=255, width=3)
L = np.asarray(lin) > 0
# apertura morfologica con un quadrato di 65 cm, fatta a passi di 3 px (PIL non ha SciPy qui: DLL bloccate da Windows)
libero = Image.fromarray(((~L) * 255).astype(np.uint8)); r = int(0.325 * PX)
er = libero
for _ in range(r): er = er.filter(ImageFilter.MinFilter(3))
ap = er
for _ in range(r): ap = ap.filter(ImageFilter.MaxFilter(3))
largo = np.asarray(ap) > 0
muro = L | (~L & ~largo)
# stanze: riempimento dal punto indicato (centro in metri del modello), dentro il libero fra i muri campiti
STANZE = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else []
# per la misura fanno da barriera anche porte e finestre (sezione degli infissi), altrimenti le stanze si uniscono
bar = Image.fromarray((muro * 255).astype(np.uint8)); db = ImageDraw.Draw(bar)
for k, ss in S.items():
    if 'porta' in k or 'Janela' in k:
        for p, q, r, s_ in ss: db.line([px(p, q), px(r, s_)], fill=255, width=7)
base = Image.fromarray(((np.asarray(bar) == 0) * 255).astype(np.uint8)); stanze = []
for nome, x, z in STANZE:
    c = base.copy(); p = tuple(int(v) for v in px(x, z))
    if c.getpixel(p) != 255: print('punto dentro un muro:', nome); continue
    ImageDraw.floodfill(c, p, 128); m = np.asarray(c) == 128
    if m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any(): print("stanza aperta verso l'esterno:", nome); continue
    ys, xs = np.where(m); stanze.append(dict(n=nome, x=x, z=z, m2=round(m.sum() / PX ** 2, 1), cx=round(xs.mean() / PX + X0, 2), cz=round(ys.mean() / PX + Z0, 2)))
# disegno: vista dall'alto leggermente schiarita, muri in nero, altre sezioni in grigio scuro sottile
a = np.asarray(im).astype(float); a = 255 - (255 - a) * 0.92
a[muro] = (24, 24, 24)
out = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(out)
for k, ss in S.items():
    if k == '51:Gruppo#20': continue
    for p, q, r, s in ss: d.line([px(p, q), px(r, s)], fill=(70, 70, 70), width=2)
out.save(f'{OUT}/pianta.png', optimize=True)
ys, xs = np.where(L); json.dump(dict(stanze=stanze, muri_bbox=[round(xs.min() / PX + X0, 3), round(xs.max() / PX + X0, 3), round(ys.min() / PX + Z0, 3), round(ys.max() / PX + Z0, 3)]), open(f'{OUT}/stanze.json', 'w'), indent=1)
for s in stanze: print(s)
print('ingombro muri x', xs.min() / PX + X0, xs.max() / PX + X0, 'z', ys.min() / PX + Z0, ys.max() / PX + Z0)
