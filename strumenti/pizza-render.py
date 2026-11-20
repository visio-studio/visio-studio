"""Resa fotorealistica procedurale di base pizza e ingredienti.

Ogni pezzo e' un campo di altezze con albedo, lucidita' e occlusione:
la luce arriva dall'alto a sinistra, come nel resto della scena.
Uscita: una striscia RGBA per ingrediente (VARS varianti affiancate)
e sei basi (rossa/bianca x tre impasti).

Serve per la demo /pizza/. Uso (servono numpy, scipy e Pillow, circa 2 minuti):
    python3 strumenti/pizza-render.py pizza/img            # tutto
    python3 strumenti/pizza-render.py pizza/img salame,olive # solo alcuni ingredienti
"""
import math, os, sys, json
import numpy as np
from scipy import ndimage as nd
from PIL import Image, ImageDraw

OUT = sys.argv[1]
ONLY = sys.argv[2].split(',') if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)
TAU = 2 * math.pi
L = np.array([-0.42, -0.52, 0.74]); L /= np.linalg.norm(L)
HV = L + np.array([0, 0, 1.0]); HV /= np.linalg.norm(HV)
VARS = 5
SS = 2  # supersampling


# ---------------------------------------------------------------- utilita'
def C(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def noise(shape, sigma, seed):
    r = np.random.default_rng(seed)
    n = nd.gaussian_filter(r.standard_normal(shape), sigma, mode='reflect')
    return n / (n.std() + 1e-9)


def fbm(shape, sigmas, seed, gain=0.55):
    out = np.zeros(shape)
    for i, s in enumerate(sigmas):
        out += gain ** i * noise(shape, s, seed * 131 + i * 7 + 1)
    return out / (out.std() + 1e-9)


def mix(a, b, t):
    t = np.clip(t, 0, 1)[..., None]
    return a * (1 - t) + b * t


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def poly_mask(n, pts, blur=0.9):
    im = Image.new('L', (n, n), 0)
    ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=255)
    return nd.gaussian_filter(np.asarray(im, float) / 255, blur)


def outline(n, rad, jit, seed, kmax=9, sx=1.0, sy=1.0, cx=0.0, cy=0.0, rot=0.0, npts=400):
    r = np.random.default_rng(seed)
    th = np.linspace(0, TAU, npts, endpoint=False)
    f = np.zeros_like(th)
    for k in range(2, kmax):
        f += r.normal() / k ** 1.15 * np.cos(k * th + r.uniform(0, TAU))
    f /= np.abs(f).max() + 1e-9
    rr = rad * (1 + jit * f)
    x, y = np.cos(th) * rr * sx, np.sin(th) * rr * sy
    cr, sr = math.cos(rot), math.sin(rot)
    return np.stack([n / 2 + cx + x * cr - y * sr, n / 2 + cy + x * sr + y * cr], 1)


def blob(n, rad, jit, seed, **kw):
    return poly_mask(n, outline(n, rad, jit, seed, **kw))


def edt(m):
    return nd.distance_transform_edt(m > 0.5)


def dome(d, dmax, hmax, p=0.5):
    return hmax * np.clip(d / dmax, 0, 1) ** p


def grid(n):
    yy, xx = np.mgrid[0:n, 0:n] + 0.5 - n / 2
    return xx, yy


def shade(alb, h, gloss=0.0, shin=30, amb=0.5, ao=0.0, aos=6, edge_dark=0.0, d=None, specc=(1, 0.98, 0.94)):
    gy, gx = np.gradient(h)
    nx, ny = -gx, -gy
    inv = 1 / np.sqrt(nx * nx + ny * ny + 1)
    nx, ny, nz = nx * inv, ny * inv, inv
    ndl = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, None)
    lit = amb + (1 - amb) * ndl / L[2]
    ndh = np.clip(nx * HV[0] + ny * HV[1] + nz * HV[2], 0, 1)
    spec = np.asarray(gloss) * ndh ** shin
    occ = np.ones_like(h)
    if ao:
        cav = np.clip(nd.gaussian_filter(h, aos) - h, 0, None)
        occ *= 1 - np.clip(ao * cav, 0, 0.6)
    if edge_dark and d is not None:
        occ *= 1 - edge_dark * np.exp(-d / (2.5 * SS))
    lo = lit * occ
    # ombre calde, come nel pane e nel formaggio veri (diffusione sotto la superficie)
    warm = np.stack([np.where(lo < 1, lo ** .8, lo), np.where(lo < 1, lo ** 1.0, lo), np.where(lo < 1, lo ** 1.35, lo)], -1)
    rgb = alb * warm + spec[..., None] * np.array(specc)
    return np.clip(rgb, 0, 1)


def finish(rgb, a, shadow=(0.03, 0.05, 0.035, 0.42)):
    n = a.shape[0]
    dx, dy, sig, op = shadow
    if op > 0:
        sa = nd.shift(a, (dy * n, dx * n), order=1, mode='constant')
        sa = nd.gaussian_filter(sa, sig * n) * op
    else:
        sa = np.zeros_like(a)
    oa = a + sa * (1 - a)
    sc = np.array([0.10, 0.04, 0.015])
    orgb = (rgb * a[..., None] + sc * (sa * (1 - a))[..., None]) / np.maximum(oa, 1e-6)[..., None]
    img = np.dstack([np.clip(orgb, 0, 1), np.clip(oa, 0, 1)])
    im = Image.fromarray((img * 255 + 0.5).astype(np.uint8), 'RGBA')
    return im.convert('RGBa').resize((n // SS, n // SS), Image.LANCZOS).convert('RGBA')


# ------------------------------------------------------------- ingredienti
# Ogni funzione riceve n (lato in px, supercampionato) e seed; restituisce un'immagine PIL.
# Il pezzo "nominale" ha diametro circa 0.7 n.

def cheese_pool(n, s, c_in, c_edge, c_spot, c_burn, spot_amt):
    m = blob(n, .30 * n, .30, s, kmax=13)
    m = nd.gaussian_filter(m, 2.2 * SS)
    d = edt(m)
    h = dome(d, .14 * n, .03 * n, .55) + fbm(m.shape, [7 * SS, 16 * SS], s) * .002 * n
    h = nd.gaussian_filter(h, 1.2 * SS)
    t_edge = 1 - np.clip(d / (.06 * n), 0, 1)
    alb = mix(np.broadcast_to(C(c_in), m.shape + (3,)).copy(), C(c_edge), t_edge * .8)
    sp = fbm(m.shape, [7 * SS, 16 * SS], s + 3)
    hi = np.clip(d / (.12 * n), 0, 1)
    alb = mix(alb, C(c_spot), sstep(1.3 - spot_amt, 2.3 - spot_amt, sp + hi * .5) * .7)
    burn = fbm(m.shape, [2.5 * SS, 5 * SS], s + 5)
    alb = mix(alb, C(c_burn), sstep(2.0, 2.8, burn + hi * .4) * .8)
    a = m * (.72 + .28 * np.clip(d / (.035 * n), 0, 1))
    rgb = shade(alb, h, gloss=.38, shin=30, amb=.58, ao=.04, aos=6 * SS, edge_dark=.0, d=d)
    return finish(rgb, a, (0.012, 0.02, 0.02, 0.16))


def g_fiordilatte(n, s):
    return cheese_pool(n, s, '#FBF7EC', '#F0E2C2', '#E2B66A', '#9C5A22', 0.55)


def g_provola(n, s):
    return cheese_pool(n, s, '#F3E4BE', '#E2C68D', '#C98E45', '#7A4318', 0.9)


def g_bufala(n, s):
    m = blob(n, .29 * n, .34, s, kmax=10, sx=1.08, sy=.92, rot=s)
    d = edt(m)
    xx, yy = grid(n)
    ang = s * 1.7
    u = xx * math.cos(ang) + yy * math.sin(ang)
    fib = noise(m.shape, SS * 1.0, s + 9)
    fib = nd.gaussian_filter1d(fib, 6 * SS, axis=0)
    h = dome(d, .2 * n, .1 * n, .5) + fbm(m.shape, [9 * SS, 20 * SS], s) * .006 * n + fib * .0005 * n
    h = nd.gaussian_filter(h, 1.0 * SS)
    alb = np.broadcast_to(C('#FDFDFA'), m.shape + (3,)).copy()
    alb = mix(alb, C('#E9E6DC'), np.clip(fbm(m.shape, [8 * SS], s + 2) * .35 + .2, 0, 1))
    rgb = shade(alb, h, gloss=.5, shin=40, amb=.62, ao=.12, aos=8 * SS, edge_dark=.18, d=d, specc=(1, 1, 1))
    return finish(rgb, m, (0.03, 0.05, 0.04, 0.42))


def g_ricotta(n, s):
    m = blob(n, .27 * n, .22, s, kmax=9)
    d = edt(m)
    grain = fbm(m.shape, [.7 * SS, 1.6 * SS], s + 4)
    h = dome(d, .2 * n, .085 * n, .6) + grain * .0007 * n + fbm(m.shape, [7 * SS], s) * .006 * n
    alb = np.broadcast_to(C('#FBFAF5'), m.shape + (3,)).copy()
    alb = mix(alb, C('#EDE6D3'), np.clip(-grain * .25 + .1, 0, 1))
    top = np.clip(d / (.2 * n), 0, 1)
    alb = mix(alb, C('#E8C98E'), sstep(.7, 1.0, top + fbm(m.shape, [5 * SS], s + 6) * .15) * .45)
    rgb = shade(alb, h, gloss=.08, shin=12, amb=.6, ao=.3, aos=3 * SS, edge_dark=.2, d=d)
    return finish(rgb, m, (0.03, 0.045, 0.04, 0.4))


def g_gorgonzola(n, s):
    m = blob(n, .25 * n, .42, s, kmax=11)
    m = nd.gaussian_filter(m, 1.2 * SS)
    d = edt(m)
    h = dome(d, .14 * n, .05 * n, .6) + fbm(m.shape, [5 * SS, 11 * SS], s) * .003 * n
    alb = np.broadcast_to(C('#F4EDD7'), m.shape + (3,)).copy()
    alb = mix(alb, C('#E6D6A8'), 1 - np.clip(d / (.08 * n), 0, 1))
    v = np.abs(fbm(m.shape, [4 * SS, 10 * SS], s + 8))
    vein = 1 - sstep(.05, .22, v)
    vein *= sstep(-.2, .6, fbm(m.shape, [12 * SS], s + 11))
    alb = mix(alb, C('#4F7466'), vein * .85)
    spots = sstep(1.7, 2.3, fbm(m.shape, [1.5 * SS], s + 12))
    alb = mix(alb, C('#3E6156'), spots * .8)
    rgb = shade(alb, h, gloss=.25, shin=22, amb=.58, ao=.12, aos=5 * SS, edge_dark=.15, d=d)
    return finish(rgb, m, (0.025, 0.04, 0.03, 0.35))


def g_parmigiano(n, s):
    r = np.random.default_rng(s)
    th = np.linspace(0, TAU, 9, endpoint=False) + r.uniform(0, 1)
    rr = 1 + r.uniform(-.25, .2, th.size)
    rot = r.uniform(0, TAU)
    x, y = np.cos(th) * rr * .33 * n, np.sin(th) * rr * .13 * n
    pts = np.stack([n / 2 + x * math.cos(rot) - y * math.sin(rot), n / 2 + x * math.sin(rot) + y * math.cos(rot)], 1)
    m = poly_mask(n, pts, .8 * SS)
    d = edt(m)
    xx, yy = grid(n)
    v = -xx * math.sin(rot) + yy * math.cos(rot)
    h = .03 * n * np.cos(v / (.13 * n) * 1.4) * m + fbm(m.shape, [1.2 * SS, 3 * SS], s) * .002 * n + dome(d, .03 * n, .01 * n)
    alb = np.broadcast_to(C('#EBD397'), m.shape + (3,)).copy()
    alb = mix(alb, C('#F8EBC4'), 1 - np.clip(d / (.03 * n), 0, 1))
    alb = mix(alb, C('#D9B868'), np.clip(fbm(m.shape, [3 * SS], s + 1) * .3, 0, 1))
    alb = mix(alb, C('#FFF8E0'), sstep(1.9, 2.4, fbm(m.shape, [.8 * SS], s + 2)))
    rgb = shade(alb, h, gloss=.18, shin=18, amb=.55, ao=.3, edge_dark=.1, d=d)
    return finish(rgb, m, (0.025, 0.045, 0.03, 0.42))


def g_salame(n, s):
    m = blob(n, .31 * n, .05, s, kmax=7)
    d = edt(m)
    dm = d.max()
    rn = 1 - d / dm
    h = .045 * n * rn ** 3.2 + dome(d, .015 * n, .012 * n) + fbm(m.shape, [6 * SS, 12 * SS], s) * .0015 * n
    h = nd.gaussian_filter(h, .8 * SS)
    alb = np.broadcast_to(C('#A3271B'), m.shape + (3,)).copy()
    alb = mix(alb, C('#7E1A12'), np.clip(fbm(m.shape, [3 * SS, 8 * SS], s) * .35 + .2, 0, 1))
    r = np.random.default_rng(s + 1)
    xx, yy = grid(n)
    fat = np.zeros(m.shape)
    for _ in range(15):
        a_, rr_ = r.uniform(0, TAU), math.sqrt(r.uniform()) * .26 * n
        cx, cy, rad = math.cos(a_) * rr_, math.sin(a_) * rr_, r.uniform(.012, .03) * n
        e = np.hypot((xx - cx) / r.uniform(.7, 1.3), yy - cy)
        fat = np.maximum(fat, 1 - sstep(rad * .6, rad, e))
    alb = mix(alb, C('#F1D2C2'), fat * .92)
    pep = sstep(2.3, 2.7, noise(m.shape, .9 * SS, s + 2))
    alb = mix(alb, C('#2A0B05'), pep * .9)
    rim = 1 - np.clip(d / (.035 * n), 0, 1)
    alb = mix(alb, C('#4A1209'), rim ** 1.5 * .85)
    oil = np.clip(.45 + rn * .3 - fat * .2, 0, 1)
    rgb = shade(alb, h, gloss=oil * .5, shin=45, amb=.52, ao=.1, edge_dark=.0, d=d, specc=(1, .92, .8))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.4))


def g_cotto(n, s):
    m = blob(n, .3 * n, .28, s, kmax=6, sx=1.15, sy=.82, rot=s * .9)
    d = edt(m)
    h = dome(d, .03 * n, .008 * n) + fbm(m.shape, [12 * SS, 24 * SS], s) * .01 * n
    xx, yy = grid(n)
    ang = s * 2.3
    u = xx * math.cos(ang) + yy * math.sin(ang)
    stri = np.sin(u / (.035 * n) + fbm(m.shape, [8 * SS], s + 3) * 2.5)
    alb = np.broadcast_to(C('#EBA595'), m.shape + (3,)).copy()
    alb = mix(alb, C('#D9887A'), np.clip(stri * .25 + .15, 0, 1))
    fatband = 1 - sstep(.02 * n, .045 * n, d)
    fatside = sstep(-.3, .3, fbm(m.shape, [25 * SS], s + 4))
    alb = mix(alb, C('#F8E3DA'), fatband * fatside)
    rgb = shade(alb, h, gloss=.22, shin=24, amb=.58, ao=.12, aos=10 * SS, edge_dark=.12, d=d)
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.3))


def g_salsiccia(n, s):
    r = np.random.default_rng(s)
    m = np.zeros((n, n))
    for i in range(5):
        a_, rr_ = r.uniform(0, TAU), r.uniform(0, .13) * n
        m = np.maximum(m, blob(n, r.uniform(.09, .14) * n, .4, s * 10 + i, kmax=9, cx=math.cos(a_) * rr_, cy=math.sin(a_) * rr_))
    d = edt(m)
    lump = fbm(m.shape, [3 * SS, 7 * SS], s)
    h = dome(d, .09 * n, .07 * n, .55) + lump * .012 * n
    h = nd.gaussian_filter(h, .8 * SS)
    alb = np.broadcast_to(C('#9A5A35'), m.shape + (3,)).copy()
    alb = mix(alb, C('#6B341C'), np.clip(lump * .4 + .3, 0, 1))
    alb = mix(alb, C('#C98E6E'), sstep(1.4, 2.1, -lump) * .6)
    alb = mix(alb, C('#EAD5B8'), sstep(2.2, 2.7, noise(m.shape, 1.2 * SS, s + 4)) * .7)
    alb = mix(alb, C('#4E4A20'), sstep(2.4, 2.8, noise(m.shape, .8 * SS, s + 5)))
    rgb = shade(alb, h, gloss=.32, shin=30, amb=.45, ao=1.0, aos=3 * SS, edge_dark=.3, d=d, specc=(1, .9, .75))
    return finish(rgb, m, (0.025, 0.045, 0.03, 0.5))


def g_nduja(n, s):
    m = blob(n, .22 * n, .45, s, kmax=11)
    halo = nd.gaussian_filter(blob(n, .31 * n, .4, s + 1, kmax=9), 4 * SS)
    d = edt(m)
    h = dome(d, .1 * n, .03 * n, .6) + fbm(m.shape, [4 * SS, 9 * SS], s) * .003 * n
    alb = np.broadcast_to(C('#9C1E10'), m.shape + (3,)).copy()
    alb = mix(alb, C('#6E1208'), np.clip(fbm(m.shape, [3 * SS], s + 2) * .4 + .2, 0, 1))
    alb = mix(alb, C('#D2451F'), sstep(1.5, 2.3, fbm(m.shape, [1.5 * SS], s + 3)) * .7)
    rgb_in = shade(alb, h, gloss=.6, shin=50, amb=.5, ao=.4, d=d, specc=(1, .85, .7))
    oil = np.broadcast_to(C('#D9561E'), m.shape + (3,))
    a_oil = halo * .55
    a = m + a_oil * (1 - m)
    rgb = (rgb_in * m[..., None] + oil * (a_oil * (1 - m))[..., None]) / np.maximum(a, 1e-6)[..., None]
    return finish(rgb, a, (0.01, 0.02, 0.02, 0.2))


def ribbon(n, s, length, width, amp, waves):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    ph = r.uniform(0, TAU)
    N = 60
    t = np.linspace(0, 1, N)
    cx = (t - .5) * length * n
    cy = np.sin(t * TAU * waves / 2 + ph) * amp * n
    w = width * n * (.75 + .35 * np.sin(t * math.pi)) * (1 + .12 * np.sin(t * 9 + ph))
    dx = np.gradient(cx); dy = np.gradient(cy); ln = np.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    top = np.stack([cx + nx * w, cy + ny * w], 1)
    bot = np.stack([cx - nx * w, cy - ny * w], 1)
    pts = np.concatenate([top, bot[::-1]])
    cr, sr = math.cos(rot), math.sin(rot)
    P = np.stack([n / 2 + pts[:, 0] * cr - pts[:, 1] * sr, n / 2 + pts[:, 0] * sr + pts[:, 1] * cr], 1)
    xx, yy = grid(n)
    u = (xx * cr + yy * sr) / (length * n) + .5
    v = (-xx * sr + yy * cr)
    centre_y = np.sin(np.clip(u, 0, 1) * TAU * waves / 2 + ph) * amp * n
    across = (v - centre_y) / (width * n)
    return poly_mask(n, P, .8 * SS), u, across, rot


def g_crudo(n, s):
    m, u, across, rot = ribbon(n, s, .82, .13, .07, 1.6)
    d = edt(m)
    fold = np.cos(u * TAU * 1.8 + s) * .02 * n
    h = dome(d, .05 * n, .025 * n, .5) + fold
    alb = np.broadcast_to(C('#C24E52'), m.shape + (3,)).copy()
    alb = mix(alb, C('#A63A43'), np.clip(fbm(m.shape, [4 * SS, 10 * SS], s + 1) * .35 + .2, 0, 1))
    marb = 1 - sstep(.03, .12, np.abs(fbm(m.shape, [3 * SS, 7 * SS], s + 2)))
    alb = mix(alb, C('#E8A2A2'), marb * .45)
    fat = sstep(.45, .75, across)
    alb = mix(alb, C('#F7E8E0'), fat)
    rgb = shade(alb, h, gloss=.35 + fat * .1, shin=34, amb=.58, ao=.15, aos=8 * SS, edge_dark=.1, d=d)
    a = m * (.92 + .08 * fat)
    return finish(rgb, a, (0.03, 0.05, 0.04, 0.4))


def g_alici(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    t = np.linspace(-1, 1, 120)
    bend = r.uniform(-.06, .06)
    cx = t * .4 * n
    cy = bend * n * (1 - t * t) * 2
    w = .1 * n * np.sqrt(np.clip(1 - t ** 2, 0, 1)) * (1 - .25 * t)
    pts = np.concatenate([np.stack([cx, cy - w], 1), np.stack([cx, cy + w], 1)[::-1]])
    cr, sr = math.cos(rot), math.sin(rot)
    P = np.stack([n / 2 + pts[:, 0] * cr - pts[:, 1] * sr, n / 2 + pts[:, 0] * sr + pts[:, 1] * cr], 1)
    m = poly_mask(n, P, .7 * SS)
    xx, yy = grid(n)
    u = (xx * cr + yy * sr) / (.4 * n)
    v = (-xx * sr + yy * cr) - bend * n * (1 - np.clip(u, -1, 1) ** 2) * 2
    across = v / (.1 * n)
    d = edt(m)
    h = dome(d, .06 * n, .02 * n, .6)
    alb = mix(np.broadcast_to(C('#9E7F6E'), m.shape + (3,)).copy(), C('#6A4A3C'), sstep(-.9, .6, -across))
    alb = mix(alb, C('#C9BDB3'), sstep(.2, .8, across) * .6)
    stri = np.sin(u * 60 + fbm(m.shape, [3 * SS], s) * 1.5)
    alb = mix(alb, C('#4F3529'), np.clip(stri, 0, 1) * .15)
    alb = mix(alb, C('#3A261D'), (1 - sstep(.0, .12, np.abs(across))) * .35)
    rgb = shade(alb, h, gloss=.7, shin=60, amb=.5, ao=.2, edge_dark=.15, d=d, specc=(1, 1, 1))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.4))


def g_funghi(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(-.5, .5) + (math.pi if s % 2 else 0)
    th = np.linspace(math.pi, TAU, 80)
    capw, caph = .33 * n * r.uniform(.9, 1.1), .25 * n * r.uniform(.85, 1.1)
    cap = np.stack([np.cos(th) * capw, np.sin(th) * caph], 1)
    sw, sl = .1 * n, .2 * n
    stem = np.array([[capw * .55, 0], [sw * 1.05, .02 * n], [sw * .95, sl], [0, sl + .02 * n], [-sw * .95, sl], [-sw * 1.05, .02 * n], [-capw * .55, 0]])
    pts = np.concatenate([cap, stem]) - np.array([0, -.04 * n])
    cr, sr = math.cos(rot), math.sin(rot)
    P = np.stack([n / 2 + pts[:, 0] * cr - pts[:, 1] * sr, n / 2 + pts[:, 0] * sr + pts[:, 1] * cr], 1)
    m = poly_mask(n, P, .9 * SS)
    d = edt(m)
    h = dome(d, .05 * n, .012 * n, .6) + fbm(m.shape, [7 * SS, 14 * SS], s) * .0015 * n
    alb = np.broadcast_to(C('#E6D5B5'), m.shape + (3,)).copy()
    alb = mix(alb, C('#CDB58D'), np.clip(fbm(m.shape, [5 * SS], s + 1) * .4 + .2, 0, 1))
    skin = 1 - sstep(.008 * n, .02 * n, d)
    xx, yy = grid(n)
    vy = -xx * sr + yy * cr
    capzone = sstep(.06 * n, .0, vy + .04 * n)
    alb = mix(alb, C('#7A5536'), skin * (.4 + .6 * capzone))
    gills = 1 - sstep(.0, .2, np.abs(np.sin((xx * cr + yy * sr) / (.012 * n))))
    alb = mix(alb, C('#B89A70'), gills * capzone * sstep(.0, .05 * n, d) * .35)
    alb = mix(alb, C('#9C7347'), sstep(1.6, 2.3, fbm(m.shape, [2 * SS, 5 * SS], s + 2)) * .5)
    rgb = shade(alb, h, gloss=.25, shin=24, amb=.55, ao=.3, edge_dark=.1, d=d)
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.3))


def g_melanzane(n, s):
    m = blob(n, .31 * n, .06, s, kmax=7, sx=1.05, sy=.95, rot=s)
    d = edt(m)
    h = dome(d, .04 * n, .012 * n, .6) + fbm(m.shape, [4 * SS], s) * .003 * n
    alb = np.broadcast_to(C('#DCC08A'), m.shape + (3,)).copy()
    alb = mix(alb, C('#C8A266'), np.clip(fbm(m.shape, [3 * SS, 8 * SS], s + 1) * .4 + .2, 0, 1))
    dm = d.max()
    ring = np.exp(-((d / dm - .45) / .12) ** 2)
    seeds = sstep(1.8, 2.3, noise(m.shape, 1.1 * SS, s + 2)) * ring
    alb = mix(alb, C('#8C6A3A'), seeds * .8)
    skin = 1 - sstep(.007 * n, .014 * n, d)
    alb = mix(alb, C('#4A2140'), skin * .9)
    xx, yy = grid(n)
    ang = .6 + s * .1
    u = xx * math.cos(ang) + yy * math.sin(ang)
    grill = nd.gaussian_filter(np.exp(-((((u / (.11 * n)) % 1) - .5) / .2) ** 2), 1.5 * SS)
    grill *= sstep(-.6, .4, fbm(m.shape, [6 * SS], s + 3))
    alb = mix(alb, C('#4A2C16'), grill * .6 * (1 - skin))
    h -= grill * .004 * n
    rgb = shade(alb, h, gloss=.35, shin=30, amb=.55, ao=.4, edge_dark=.1, d=d, specc=(1, .95, .85))
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.32))


def g_peperoni(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    bend = r.uniform(.15, .45)
    t = np.linspace(-1, 1, 80)
    cx = t * .38 * n
    cy = -bend * .25 * n * (1 - t * t)
    w = .085 * n * (1 - .2 * np.abs(t) ** 3)
    dx = np.gradient(cx); dy = np.gradient(cy); ln = np.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    pts = np.concatenate([np.stack([cx + nx * w, cy + ny * w], 1), np.stack([cx - nx * w, cy - ny * w], 1)[::-1]])
    cr, sr = math.cos(rot), math.sin(rot)
    P = np.stack([n / 2 + pts[:, 0] * cr - pts[:, 1] * sr, n / 2 + pts[:, 0] * sr + pts[:, 1] * cr], 1)
    m = poly_mask(n, P, .8 * SS)
    d = edt(m)
    h = dome(d, .06 * n, .03 * n, .5) + fbm(m.shape, [3 * SS], s) * .002 * n
    red = s % 2 == 0
    c1, c2 = (C('#C8281A'), C('#8E140C')) if red else (C('#EBA51B'), C('#C57A0E'))
    alb = mix(np.broadcast_to(c1, m.shape + (3,)).copy(), c2, np.clip(fbm(m.shape, [4 * SS, 10 * SS], s + 1) * .35 + .25, 0, 1))
    char = sstep(1.5, 2.2, fbm(m.shape, [2 * SS, 5 * SS], s + 2))
    alb = mix(alb, C('#2B140A'), char * .85)
    rgb = shade(alb, h, gloss=.75, shin=70, amb=.5, ao=.2, edge_dark=.15, d=d, specc=(1, 1, .96))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.42))


def g_cipolla(n, s):
    r = np.random.default_rng(s)
    xx, yy = grid(n)
    rr = np.hypot(xx, yy)
    th = np.arctan2(yy, xx)
    a0 = r.uniform(0, TAU)
    span = r.uniform(.9, 1.6) * math.pi
    rel = (th - a0) % TAU
    arcm = sstep(0, .12, rel) * sstep(span, span - .12, rel)
    m = np.zeros((n, n)); facecol = np.zeros((n, n))
    rings = [(.3, .05)] + ([(.2, .045)] if r.uniform() < .65 else [])
    hh = np.zeros((n, n))
    for R0, W in rings:
        e = np.abs(rr - R0 * n) / (W * n)
        ring = 1 - sstep(.85, 1.0, e)
        m = np.maximum(m, ring)
        hh = np.maximum(hh, (1 - np.clip(e, 0, 1) ** 2) * .022 * n)
        facecol = np.maximum(facecol, sstep(.9, .55, e))
    m *= arcm
    d = edt(m)
    alb = mix(np.broadcast_to(C('#86275F'), m.shape + (3,)).copy(), C('#E6C3D4'), facecol * .75)
    alb = mix(alb, C('#5A2A12'), sstep(1.6, 2.2, fbm(m.shape, [2 * SS], s + 1)) * .6)
    rgb = shade(alb, hh, gloss=.45, shin=40, amb=.55, d=d)
    a = m * .96
    return finish(rgb, a, (0.015, 0.03, 0.02, 0.35))


def g_carciofi(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    t = np.linspace(0, TAU, 200, endpoint=False)
    x = np.sin(t) * .24 * n * (1 - .25 * np.cos(t))
    y = -np.cos(t) * .3 * n
    cr, sr = math.cos(rot), math.sin(rot)
    P = np.stack([n / 2 + x * cr - y * sr, n / 2 + x * sr + y * cr], 1)
    m = poly_mask(n, P, .9 * SS)
    d = edt(m)
    xx, yy = grid(n)
    vy = (-xx * sr + yy * cr) / (.3 * n)
    vx = (xx * cr + yy * sr) / (.24 * n)
    layer = np.hypot(vx * 1.0, (vy - .9) * .75)
    bands = np.sin(layer * 22 + fbm(m.shape, [4 * SS], s) * .8)
    h = dome(d, .1 * n, .05 * n, .6) + np.clip(bands, 0, 1) * .003 * n
    alb = mix(np.broadcast_to(C('#E7DCA2'), m.shape + (3,)).copy(), C('#8C9447'), sstep(.6, 1.6, layer))
    alb = mix(alb, C('#6E7533'), (1 - sstep(.0, .5, bands + 1)) * .25)
    alb = mix(alb, C('#7A4C5C'), sstep(1.5, 1.9, layer) * .35)
    rgb = shade(alb, h, gloss=.45, shin=36, amb=.55, ao=.6, aos=2 * SS, edge_dark=.15, d=d, specc=(1, .98, .85))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.4))


def leaf_outline(n, length, width, s, lobes=0, lobe_amt=0.0, tip=1.0):
    r = np.random.default_rng(s)
    t = np.linspace(0, 1, 160)
    prof = np.sin(np.pi * t ** .8) ** tip * (1 - .15 * t)
    if lobes:
        prof = prof * (1 - lobe_amt * (.5 + .5 * np.cos(t * TAU * lobes + r.uniform(0, TAU))) * sstep(.05, .2, t))
    x = (t - .5) * length * n
    w = width * n * prof
    top = np.stack([x, -w], 1)
    bot = np.stack([x, w * (1 if not lobes else 1)], 1)
    if lobes:
        prof2 = np.sin(np.pi * t ** .8) * (1 - .15 * t) * (1 - lobe_amt * (.5 + .5 * np.cos(t * TAU * lobes + 1.3 + r.uniform(0, 1))) * sstep(.05, .2, t))
        bot = np.stack([x, width * n * prof2], 1)
    return np.concatenate([top, bot[::-1]])


def place(n, pts, rot):
    cr, sr = math.cos(rot), math.sin(rot)
    return np.stack([n / 2 + pts[:, 0] * cr - pts[:, 1] * sr, n / 2 + pts[:, 0] * sr + pts[:, 1] * cr], 1)


def g_basilico(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    P = place(n, leaf_outline(n, .62, .2, s, tip=.9), rot)
    m = poly_mask(n, P, .8 * SS)
    d = edt(m)
    xx, yy = grid(n)
    cr, sr = math.cos(rot), math.sin(rot)
    u = (xx * cr + yy * sr) / (.31 * n)
    v = (-xx * sr + yy * cr) / (.2 * n)
    mid = np.exp(-(v / .05) ** 2) * sstep(1.0, .7, np.abs(u))
    lat = np.exp(-((np.abs(v) * .9 - (u + 1) * .35 % .35 + .0) / .04) ** 2) * 0
    veins = np.exp(-((((u * 3.2 - np.abs(v) * 2.2) % 1) - .5) / .06) ** 2) * sstep(.05, .2, np.abs(v)) * sstep(.95, .5, np.abs(v))
    h = dome(d, .09 * n, .03 * n, .5) - mid * .006 * n - veins * .0025 * n + np.cos(u * 2.2) * .006 * n
    alb = mix(np.broadcast_to(C('#3E9A3E'), m.shape + (3,)).copy(), C('#1F6A27'), sstep(-1, 1, u * .6 + v * .4 + fbm(m.shape, [8 * SS], s) * .3))
    alb = mix(alb, C('#7FBE6A'), mid * .5)
    alb = mix(alb, C('#173F14'), sstep(.0, .5, 1 - np.clip(d / (.02 * n), 0, 1)) * .35)
    rgb = shade(alb, h, gloss=.55, shin=40, amb=.5, ao=.4, aos=2 * SS, edge_dark=.1, d=d, specc=(.95, 1, .92))
    return finish(rgb, m, (0.03, 0.05, 0.035, 0.45))


def g_rucola(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    P = place(n, leaf_outline(n, .74, .15, s, lobes=3, lobe_amt=.5, tip=.75), rot)
    m = poly_mask(n, P, .7 * SS)
    d = edt(m)
    xx, yy = grid(n)
    cr, sr = math.cos(rot), math.sin(rot)
    u = (xx * cr + yy * sr) / (.39 * n)
    v = (-xx * sr + yy * cr) / (.15 * n)
    mid = np.exp(-(v / .07) ** 2) * sstep(1.05, .9, np.abs(u))
    stemx = sstep(-1.0, -1.15, u) * np.exp(-(v / .12) ** 2)
    h = dome(d, .04 * n, .012 * n, .5) + mid * .004 * n + fbm(m.shape, [3 * SS], s) * .002 * n
    alb = mix(np.broadcast_to(C('#4E8A2F'), m.shape + (3,)).copy(), C('#2E5E1C'), np.clip(fbm(m.shape, [5 * SS, 12 * SS], s + 1) * .4 + .3, 0, 1))
    alb = mix(alb, C('#A8C77A'), mid * .7)
    rgb = shade(alb, h, gloss=.18, shin=20, amb=.55, ao=.3, edge_dark=.1, d=d)
    return finish(rgb, m, (0.025, 0.045, 0.03, 0.42))


def g_friarielli(n, s):
    r = np.random.default_rng(s)
    m = np.zeros((n, n)); h = np.zeros((n, n)); tint = np.zeros((n, n))
    for i in range(6):
        rot = r.uniform(0, TAU)
        off = np.array([r.uniform(-.1, .1), r.uniform(-.1, .1)]) * n
        pts = leaf_outline(n, r.uniform(.3, .42), r.uniform(.07, .1), s * 10 + i, lobes=2, lobe_amt=.4, tip=.8)
        P = place(n, pts, rot) + off
        lm = poly_mask(n, P, .7 * SS)
        ld = edt(lm)
        lh = dome(ld, .04 * n, .02 * n, .5) + i * .004 * n
        sel = lm > .5
        h = np.where(sel, np.maximum(h, lh), h)
        tint = np.where(sel, r.uniform(0, 1), tint)
        m = np.maximum(m, lm)
    d = edt(m)
    h = nd.gaussian_filter(h, .8 * SS)
    alb = mix(np.broadcast_to(C('#3D6322'), m.shape + (3,)).copy(), C('#22401A'), tint * .8 + fbm(m.shape, [4 * SS], s) * .15)
    rgb = shade(alb, h, gloss=.5, shin=36, amb=.45, ao=1.2, aos=3 * SS, edge_dark=.25, d=d, specc=(.95, 1, .85))
    return finish(rgb, m, (0.025, 0.045, 0.03, 0.45))


def g_pomodorini(n, s):
    m = blob(n, .26 * n, .05, s, kmax=6, sx=1.05, sy=.95, rot=s)
    d = edt(m)
    dm = d.max()
    xx, yy = grid(n)
    rr = np.hypot(xx, yy) / (.26 * n)
    th = np.arctan2(yy, xx) + s
    h = dome(d, .12 * n, .05 * n, .5) + fbm(m.shape, [2 * SS], s) * .002 * n
    alb = np.broadcast_to(C('#E0412A'), m.shape + (3,)).copy()
    skin = 1 - sstep(.015 * n, .03 * n, d)
    alb = mix(alb, C('#A9170E'), skin)
    loc = np.zeros(m.shape)
    for k in range(3):
        a_ = k * TAU / 3
        ex, ey = math.cos(a_) * .5, math.sin(a_) * .5
        e = np.hypot(rr * np.cos(th) - ex, (rr * np.sin(th) - ey) * 1.3)
        loc = np.maximum(loc, 1 - sstep(.22, .32, e))
    alb = mix(alb, C('#F0A04E'), loc * .8)
    seeds = sstep(1.7, 2.2, noise(m.shape, 1.0 * SS, s + 1)) * loc
    alb = mix(alb, C('#F7E3A6'), seeds)
    core = 1 - sstep(.08, .16, rr)
    alb = mix(alb, C('#F2856A'), core * .7)
    alb = mix(alb, C('#3A1408'), sstep(1.9, 2.5, fbm(m.shape, [2 * SS, 4 * SS], s + 3)) * .6 * skin)
    rgb = shade(alb, h, gloss=.7, shin=60, amb=.5, ao=.3, edge_dark=.15, d=d, specc=(1, 1, 1))
    return finish(rgb, m, (0.025, 0.04, 0.03, 0.45))


def g_olive(n, s):
    xx, yy = grid(n)
    r = np.random.default_rng(s)
    sx = r.uniform(.92, 1.08)
    rr = np.hypot(xx / sx, yy / (2 - sx)) / n
    m = (1 - sstep(.255, .27, rr)) * sstep(.105, .12, rr)
    d = edt(m)
    mid = .19
    h = (1 - ((rr - mid) / .08) ** 2).clip(0) * .035 * n
    alb = np.broadcast_to(C('#2E1A26'), m.shape + (3,)).copy()
    alb = mix(alb, C('#4B2C3C'), np.clip(fbm(m.shape, [4 * SS], s) * .4 + .2, 0, 1))
    alb = mix(alb, C('#6E4A54'), 1 - sstep(.12, .145, rr))
    rgb = shade(alb, h, gloss=.75, shin=55, amb=.45, d=d, specc=(1, 1, 1))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.42))


ING = {
    'fiordilatte': (g_fiordilatte, 224), 'provola': (g_provola, 224), 'bufala': (g_bufala, 224),
    'ricotta': (g_ricotta, 192), 'gorgonzola': (g_gorgonzola, 160), 'parmigiano': (g_parmigiano, 192),
    'salame': (g_salame, 192), 'cotto': (g_cotto, 224), 'salsiccia': (g_salsiccia, 176),
    'nduja': (g_nduja, 176), 'crudo': (g_crudo, 288), 'alici': (g_alici, 256),
    'funghi': (g_funghi, 192), 'melanzane': (g_melanzane, 208), 'peperoni': (g_peperoni, 240),
    'cipolla': (g_cipolla, 176), 'carciofi': (g_carciofi, 192), 'friarielli': (g_friarielli, 208),
    'pomodorini': (g_pomodorini, 144), 'olive': (g_olive, 128), 'rucola': (g_rucola, 256),
    'basilico': (g_basilico, 208),
}


# ------------------------------------------------------------------- basi
DOUGH = {
    'classico': dict(d='#F2DDB0', g='#DFA45A', b='#A9652C', c='#22130A', spots=1.0, bran=0, cen='#EED6A2'),
    'integrale': dict(d='#DDBF91', g='#BF8644', b='#7E4720', c='#1E1108', spots=1.0, bran=1, cen='#D9BA8A'),
    'sg': dict(d='#F6E7C2', g='#E8BD74', b='#BE8644', c='#4A2C14', spots=.5, bran=0, cen='#F3E2B8'),
}


def g_base(kind, imp, n=1920):
    D = DOUGH[imp]
    r = np.random.default_rng(7)
    xx, yy = grid(n)
    rr = np.hypot(xx, yy)
    th = np.arctan2(yy, xx)
    R = .47 * n
    wob = sum(r.normal() / k ** 1.3 * np.cos(k * th + r.uniform(0, TAU)) for k in range(3, 14))
    edge = R * (1 + .016 * wob)
    alpha = sstep(1.2 * SS, -1.2 * SS, rr - edge)
    rn = rr / edge
    # cornicione gonfio: lato interno dolce, esterno piu' ripido
    rim_c = .875 + .012 * fbm((n, n), [40 * SS], 31)
    w = np.where(rn > rim_c, .07, .1)
    prof = np.exp(-((rn - rim_c) / w) ** 2)
    rimH = .09 * R * (1 + .22 * fbm((n, n), [25 * SS, 60 * SS], 11))
    lumps = fbm((n, n), [7 * SS, 16 * SS], 27)
    h = prof * (rimH + lumps * .01 * R)
    bub = np.zeros((n, n))
    for _ in range(60):
        a_, d_ = r.uniform(0, TAU), r.uniform(.84, .95) * R
        cx, cy = math.cos(a_) * d_, math.sin(a_) * d_
        br = r.uniform(.018, .045) * R
        bub = np.maximum(bub, np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / br ** 2)) * r.uniform(.3, 1))
    h += bub * .02 * R
    h += fbm((n, n), [3 * SS, 7 * SS], 12) * .0007 * R
    h = nd.gaussian_filter(h, 1.0 * SS)
    # colore del cornicione
    dough = C(D['d']); gold = C(D['g']); brown = C(D['b']); char = C(D['c'])
    top = np.clip(h / (.09 * R), 0, 1.2)
    tone = fbm((n, n), [14 * SS, 35 * SS], 13)
    alb = mix(np.broadcast_to(dough, (n, n, 3)).copy(), gold, np.clip(top ** .8 * (.8 + .2 * tone) + sstep(.95, 1.0, rn) * .5, 0, 1))
    bz = sstep(.35, 1.25, fbm((n, n), [12 * SS, 30 * SS], 28) * .6 + top * .9 + bub * .4 - .25)
    alb = mix(alb, brown, bz * .7)
    rimz = sstep(.79, .85, rn)
    leo = fbm((n, n), [4 * SS, 8 * SS], 14)
    spot = sstep(2.25, 2.7, leo + top * .5) * rimz
    if D['spots'] < 1:
        spot *= .5
    halo = sstep(1.6, 2.25, leo + top * .5) * rimz * (1 - spot)
    alb = mix(alb, brown * .7, halo * .55)
    alb = mix(alb, char, spot * .92)
    flour = sstep(2.4, 2.9, noise((n, n), .8 * SS, 15)) * sstep(.9, .96, rn)
    alb = mix(alb, C('#F7F1E3'), flour * .6)
    if D['bran']:
        bran = sstep(2.1, 2.6, noise((n, n), .9 * SS, 16))
        alb = mix(alb, C('#5E3A1E'), bran * .55)
    gloss = np.full((n, n), .05)
    # centro
    sedge = R * (.8 + .012 * fbm((n, n), [40 * SS], 17)) + fbm((n, n), [12 * SS], 18) * .006 * R
    centre = sstep(2 * SS, -4 * SS, rr - sedge)
    if kind == 'rossa':
        st = fbm((n, n), [6 * SS, 16 * SS, 40 * SS], 20)
        sc = mix(np.broadcast_to(C('#B3261A'), (n, n, 3)).copy(), C('#CC3E26'), np.clip(st * .3 + .5, 0, 1))
        pulp = fbm((n, n), [1.6 * SS, 3.2 * SS], 21)
        sc = mix(sc, C('#DF5536'), sstep(1.7, 2.5, pulp) * .4)
        sc = mix(sc, C('#861A0E'), sstep(1.7, 2.5, -pulp) * .3)
        caramel = sstep(1.9, 2.6, fbm((n, n), [4 * SS, 10 * SS], 22)) * sstep(.55, .76, rn)
        sc = mix(sc, C('#5E160B'), caramel * .55)
        thin = sstep(.0, .03 * R, sedge - rr)
        sc = mix(sc, C('#C4502C'), (1 - thin) * .35)
        alb = mix(alb, sc, centre)
        h = h + centre * (.006 * R + st * .0008 * R + pulp * .0002 * R)
        gloss = gloss * (1 - centre) + centre * np.clip(.32 + fbm((n, n), [14 * SS, 30 * SS], 23) * .12, .12, .5)
    else:
        bubc = np.zeros((n, n))
        for _ in range(45):
            a_, d_ = r.uniform(0, TAU), math.sqrt(r.uniform()) * .74 * R
            cx, cy = math.cos(a_) * d_, math.sin(a_) * d_
            br = r.uniform(.012, .04) * R
            bubc = np.maximum(bubc, np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / br ** 2)) * r.uniform(.4, 1))
        bc = mix(np.broadcast_to(C(D['cen']), (n, n, 3)).copy(), gold, np.clip(bubc * .8 + tone * .12 + .12, 0, 1))
        bc = mix(bc, brown, sstep(.7, 1.0, bubc) * .6)
        bc = mix(bc, char, sstep(.9, 1.0, bubc) * sstep(1.4, 2.2, leo) * .6)
        oilp = sstep(-.3, .6, fbm((n, n), [12 * SS, 30 * SS], 24))
        bc = mix(bc, C('#DDB25A'), oilp * .3)
        salt = sstep(2.6, 3.0, noise((n, n), .7 * SS, 25))
        bc = mix(bc, C('#FFFFFF'), salt * .7)
        alb = mix(alb, bc, centre)
        lift = sstep(sedge + .04 * R, sedge - .04 * R, rr)
        h = h + lift * .006 * R + centre * bubc * .012 * R
        gloss = gloss * (1 - centre) + centre * (.08 + oilp * .38 + salt * .4)
    rgb = shade(alb, h, gloss=gloss, shin=34, amb=.42, ao=.03, aos=16 * SS, specc=(1, .97, .9))
    rgb *= (1 - .08 * sstep(.7, 1.0, rn))[..., None]
    sh_a = nd.gaussian_filter(nd.shift(alpha, (.014 * n, .007 * n), order=1), .013 * n) * .5
    a = alpha + sh_a * (1 - alpha)
    sc = np.array([.06, .04, .1])
    orgb = (rgb * alpha[..., None] + sc * (sh_a * (1 - alpha))[..., None]) / np.maximum(a, 1e-6)[..., None]
    img = np.dstack([np.clip(orgb, 0, 1), np.clip(a, 0, 1)])
    im = Image.fromarray((img * 255 + .5).astype(np.uint8), 'RGBA')
    return im.convert('RGBa').resize((n // SS, n // SS), Image.LANCZOS).convert('RGBA')


if __name__ == '__main__':
    meta = {}
    for name, (fn, px) in ING.items():
        if ONLY and name not in ONLY and 'ing' not in ONLY:
            continue
        n = px * SS
        strip = Image.new('RGBA', (px * VARS, px))
        for v in range(VARS):
            strip.paste(fn(n, 1000 + v * 17 + len(name)), (px * v, 0))
        strip.save(os.path.join(OUT, f'{name}.webp'), 'WEBP', quality=88, method=6)
        meta[name] = px
        print(name, flush=True)
    if not ONLY or 'basi' in ONLY:
        for kind in ('rossa', 'bianca'):
            for imp in DOUGH:
                g_base(kind, imp).save(os.path.join(OUT, f'base-{kind}-{imp}.webp'), 'WEBP', quality=84, method=6)
                print('base', kind, imp, flush=True)
