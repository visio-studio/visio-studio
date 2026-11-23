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


POM_ROSSO = ('#E0412A', '#A9170E', '#F0A04E', '#F7E3A6', '#F2856A')
POM_GIALLO = ('#F2BE2E', '#D99210', '#F7D86E', '#FBF0C0', '#F8D888')


def g_pomodorini(n, s, pal=POM_ROSSO):
    m = blob(n, .26 * n, .05, s, kmax=6, sx=1.05, sy=.95, rot=s)
    d = edt(m)
    dm = d.max()
    xx, yy = grid(n)
    rr = np.hypot(xx, yy) / (.26 * n)
    th = np.arctan2(yy, xx) + s
    h = dome(d, .12 * n, .05 * n, .5) + fbm(m.shape, [2 * SS], s) * .002 * n
    alb = np.broadcast_to(C(pal[0]), m.shape + (3,)).copy()
    skin = 1 - sstep(.015 * n, .03 * n, d)
    alb = mix(alb, C(pal[1]), skin)
    loc = np.zeros(m.shape)
    for k in range(3):
        a_ = k * TAU / 3
        ex, ey = math.cos(a_) * .5, math.sin(a_) * .5
        e = np.hypot(rr * np.cos(th) - ex, (rr * np.sin(th) - ey) * 1.3)
        loc = np.maximum(loc, 1 - sstep(.22, .32, e))
    alb = mix(alb, C(pal[2]), loc * .8)
    seeds = sstep(1.7, 2.2, noise(m.shape, 1.0 * SS, s + 1)) * loc
    alb = mix(alb, C(pal[3]), seeds)
    core = 1 - sstep(.08, .16, rr)
    alb = mix(alb, C(pal[4]), core * .7)
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


# ------------------------------------------------- ingredienti del menu (novembre 2026)
def full(h, n):
    return np.broadcast_to(C(h), (n, n, 3)).copy()


def g_stracciatella(n, s):
    r = np.random.default_rng(s)
    pool = nd.gaussian_filter(blob(n, .3 * n, .45, s, kmax=11), 2 * SS)
    d = edt(pool)
    fib = nd.gaussian_filter1d(noise((n, n), 1.0 * SS, s + 1), 8 * SS, axis=1)
    fib = nd.rotate(fib, r.uniform(0, 180), reshape=False, mode='reflect')
    fib = (fib - fib.mean()) / (fib.std() + 1e-9)
    h = nd.gaussian_filter(dome(d, .1 * n, .02 * n, .6) + np.clip(fib, 0, None) * .006 * n, .7 * SS)
    alb = mix(full('#F1ECE0', n), C('#FFFFFF'), sstep(-.2, 1.2, fib))
    rgb = shade(alb, h, gloss=.55, shin=40, amb=.62, ao=.3, aos=2 * SS, d=d, specc=(1, 1, 1))
    return finish(rgb, pool * (.78 + .22 * np.clip(d / (.04 * n), 0, 1)), (0.01, 0.02, 0.02, 0.18))


def g_burrata(n, s):
    r = np.random.default_rng(s)
    m = blob(n, .32 * n, .12, s, kmax=7)
    d = edt(m)
    xx, yy = grid(n)
    ox, oy = r.uniform(-.08, .08, 2) * n
    op = 1 - sstep(.08 * n, .15 * n, np.hypot(xx - ox, yy - oy) + fbm(m.shape, [3 * SS], s) * .025 * n)
    h = dome(d, .3 * n, .16 * n, .5) - op * .035 * n + op * fbm(m.shape, [2 * SS], s + 1) * .004 * n
    alb = mix(full('#FDFDFB', n), C('#F2E9D4'), op)
    tr = sstep(2.0, 2.5, noise(m.shape, 1 * SS, s + 2)) * (.25 + op)
    alb = mix(alb, C('#2B2018'), np.clip(tr, 0, 1) * .9)
    rgb = shade(alb, h, gloss=.6 - op * .3, shin=45, amb=.6, ao=.4, aos=3 * SS, edge_dark=.2, d=d, specc=(1, 1, 1))
    return finish(rgb, m, (0.035, 0.06, 0.05, 0.45))


def flakes(n, s, count, rmin, rmax, palette, spread=.3, jit=.45, elong=1.0, hgt=.006, gloss=.15, shin=20, shadow=(0.01, 0.016, 0.012, 0.35), amb=.55):
    r = np.random.default_rng(s)
    mi = Image.new('L', (n, n), 0); ci = Image.new('L', (n, n), 0)
    dm, dc = ImageDraw.Draw(mi), ImageDraw.Draw(ci)
    for _ in range(count):
        a = r.uniform(0, TAU); d = math.sqrt(r.uniform()) * spread * n
        cx, cy = n / 2 + math.cos(a) * d, n / 2 + math.sin(a) * d
        rad = r.uniform(rmin, rmax) * n; k = int(r.integers(5, 9))
        th = np.sort(r.uniform(0, TAU, k)); rr = rad * (1 + r.uniform(-jit, jit, k)); rot = r.uniform(0, TAU)
        xs, ys = np.cos(th) * rr * elong, np.sin(th) * rr
        pts = [(cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)) for x, y in zip(xs, ys)]
        dm.polygon(pts, fill=255); dc.polygon(pts, fill=1 + int(r.integers(0, len(palette))))
    m = nd.gaussian_filter(np.asarray(mi, float) / 255, .6 * SS)
    idx = np.asarray(ci).astype(int)
    pal = np.array([C(p) for p in palette])
    alb = nd.gaussian_filter(pal[np.clip(idx - 1, 0, len(palette) - 1)], (.5 * SS, .5 * SS, 0))
    d = edt(m)
    h = dome(d, .01 * n, hgt * n, .6) + fbm(m.shape, [1 * SS], s) * .001 * n
    rgb = shade(alb, h, gloss=gloss, shin=shin, amb=amb, ao=.2, aos=2 * SS, d=d)
    return finish(rgb, m, shadow)


def g_pecorino(n, s):
    return flakes(n, s, 70, .008, .022, ['#F3E7C4', '#EAD9A8', '#F8F0D8'], spread=.3)


def g_pepe(n, s):
    return flakes(n, s, 70, .003, .007, ['#1E1A16', '#2E2620', '#3A2F25'], spread=.33, hgt=.002, shadow=(0.004, 0.006, 0.005, 0.2))


def g_origano(n, s):
    return flakes(n, s, 60, .004, .011, ['#5E6B2E', '#6F7A3A', '#4E5A24'], spread=.33, hgt=.002, shadow=(0.004, 0.006, 0.005, 0.2))


def g_polvere_olive(n, s):
    return flakes(n, s, 110, .003, .008, ['#2A1D22', '#3A2A30', '#1E1418'], spread=.32, hgt=.002, shadow=(0.004, 0.006, 0.005, 0.15))


def g_granella(n, s):
    return flakes(n, s, 45, .008, .02, ['#8DB04A', '#A5C25E', '#6E8C34', '#B8A47A'], spread=.3, gloss=.2)


def g_tarallo(n, s):
    return flakes(n, s, 40, .01, .03, ['#D9A85E', '#E8C07A', '#C58C45', '#F0D49A'], spread=.3, jit=.5, hgt=.008)


def g_cipolla_croccante(n, s):
    return flakes(n, s, 32, .01, .028, ['#8A4E1E', '#A8662A', '#6E3A14'], spread=.28, elong=2.2, gloss=.25)


def g_aglio(n, s):
    return flakes(n, s, 6, .05, .07, ['#F3EBD3', '#EEE2C2'], spread=.18, jit=.1, elong=1.35, hgt=.004, gloss=.4, shin=30)


def g_wurstel(n, s):
    m = blob(n, .25 * n, .04, s, kmax=6, sx=1.06, sy=.96, rot=s)
    d = edt(m); rn = 1 - d / d.max()
    h = dome(d, .06 * n, .02 * n, .6) + .02 * n * rn ** 4 + fbm(m.shape, [4 * SS], s) * .001 * n
    alb = mix(full('#E3A285', n), C('#D88C6C'), np.clip(fbm(m.shape, [3 * SS, 8 * SS], s + 1) * .3 + .3, 0, 1))
    skin = 1 - sstep(.012 * n, .024 * n, d)
    alb = mix(alb, C('#9C4A2A'), skin)
    alb = mix(alb, C('#F2C2A8'), sstep(1.6, 2.2, noise(m.shape, 1.2 * SS, s + 2)) * .5 * (1 - skin))
    alb = mix(alb, C('#6E2E16'), sstep(1.5, 2.2, fbm(m.shape, [3 * SS], s + 3)) * (rn > .5) * .5)
    rgb = shade(alb, h, gloss=.45, shin=40, amb=.55, ao=.1, d=d, specc=(1, .92, .85))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.4))


def g_mortadella(n, s):
    r = np.random.default_rng(s)
    m = blob(n, .33 * n, .14, s, kmax=7, rot=s)
    d = edt(m)
    h = dome(d, .02 * n, .006 * n) + fbm(m.shape, [14 * SS, 28 * SS], s) * .006 * n
    alb = mix(full('#F2B7B4', n), C('#E99E9B'), np.clip(fbm(m.shape, [5 * SS, 12 * SS], s + 1) * .3 + .3, 0, 1))
    xx, yy = grid(n)
    fat = np.zeros(m.shape); pis = np.zeros(m.shape)
    for i in range(16):
        a_, rr_ = r.uniform(0, TAU), math.sqrt(r.uniform()) * .27 * n
        cx, cy, w_ = math.cos(a_) * rr_, math.sin(a_) * rr_, r.uniform(.012, .028) * n
        rot = r.uniform(0, TAU)
        u = (xx - cx) * math.cos(rot) + (yy - cy) * math.sin(rot); v = -(xx - cx) * math.sin(rot) + (yy - cy) * math.cos(rot)
        if i < 12:
            fat = np.maximum(fat, 1 - sstep(w_ * .8, w_, np.maximum(np.abs(u), np.abs(v))))
        else:
            pis = np.maximum(pis, 1 - sstep(w_ * .5, w_ * .7, np.hypot(u, v * 1.4)))
    alb = mix(alb, C('#FBF1EA'), fat * .95)
    alb = mix(alb, C('#7FA046'), pis * .9)
    rgb = shade(alb, h, gloss=.3, shin=30, amb=.62, ao=.03, aos=10 * SS, edge_dark=.08, d=d)
    return finish(rgb, m, (0.012, 0.02, 0.02, 0.25))


def g_lonza(n, s):
    m = blob(n, .3 * n, .12, s, kmax=7, sx=1.2, sy=.75, rot=s * 1.3)
    d = edt(m)
    h = dome(d, .02 * n, .006 * n) + fbm(m.shape, [12 * SS, 24 * SS], s) * .01 * n
    alb = mix(full('#B6434A', n), C('#8E2E38'), np.clip(fbm(m.shape, [4 * SS, 10 * SS], s + 1) * .35 + .3, 0, 1))
    alb = mix(alb, C('#E8A9A8'), (1 - sstep(.04, .14, np.abs(fbm(m.shape, [3 * SS, 8 * SS], s + 2)))) * .35)
    fat = (1 - sstep(.03 * n, .06 * n, d)) * sstep(-.2, .5, fbm(m.shape, [30 * SS], s + 3))
    alb = mix(alb, C('#F7E7DE'), fat)
    rgb = shade(alb, h, gloss=.35, shin=34, amb=.58, ao=.15, aos=8 * SS, edge_dark=.1, d=d)
    return finish(rgb, m, (0.012, 0.02, 0.02, 0.28))


def g_guanciale(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    pts = np.array([[-.3, -.07], [.3, -.08], [.31, .08], [-.29, .07]]) * n + r.uniform(-.015, .015, (4, 2)) * n
    m = poly_mask(n, place(n, pts, rot), 1.2 * SS)
    d = edt(m)
    xx, yy = grid(n)
    v = (-xx * math.sin(rot) + yy * math.cos(rot)) / (.08 * n)
    h = dome(d, .05 * n, .03 * n, .6) + np.sin(v * 3) * .003 * n + fbm(m.shape, [2 * SS, 5 * SS], s) * .003 * n
    layer = .5 + .5 * np.sin(v * 2.6 + fbm(m.shape, [6 * SS], s + 1) * .8)
    alb = mix(full('#F0D9B5', n), C('#A04A2A'), sstep(.45, .65, layer))
    crisp = 1 - sstep(.0, .035 * n, d)
    alb = mix(alb, C('#C37A35'), np.clip(crisp * .8 + fbm(m.shape, [3 * SS], s + 2) * .2, 0, 1))
    alb = mix(alb, C('#6A2E12'), sstep(1.6, 2.3, fbm(m.shape, [2 * SS], s + 3)) * .6)
    rgb = shade(alb, h, gloss=.5, shin=36, amb=.5, ao=.3, aos=3 * SS, edge_dark=.15, d=d, specc=(1, .92, .8))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.42))


def g_porchetta(n, s):
    m = blob(n, .3 * n, .1, s, kmax=7, sx=1.08, sy=.94, rot=s)
    d = edt(m)
    xx, yy = grid(n)
    th = np.arctan2(yy, xx); rr = np.hypot(xx, yy) / (.3 * n)
    sp = .5 + .5 * np.sin(rr * 18 - th + fbm(m.shape, [5 * SS], s) * 1.2)
    h = dome(d, .03 * n, .008 * n) + sp * .002 * n + fbm(m.shape, [10 * SS], s + 1) * .006 * n
    alb = mix(full('#E7C3A6', n), C('#F3E2CF'), sstep(.55, .8, sp))
    alb = mix(alb, C('#C98F6E'), sstep(.0, .3, sp) * .4)
    alb = mix(alb, C('#4E5A26'), sstep(2.0, 2.5, noise(m.shape, .9 * SS, s + 2)) * sstep(.25, .1, np.abs(sp - .5)) * .8)
    crack = 1 - sstep(.02 * n, .045 * n, d)
    alb = mix(alb, C('#9A5622'), crack)
    alb = mix(alb, C('#6A3410'), crack * sstep(1.0, 2.0, fbm(m.shape, [2 * SS], s + 3)) * .7)
    h = h + crack * fbm(m.shape, [1.5 * SS], s + 4) * .003 * n
    rgb = shade(alb, h, gloss=.3, shin=30, amb=.55, ao=.25, aos=3 * SS, edge_dark=.1, d=d)
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.3))


def g_polpette(n, s):
    m = blob(n, .25 * n, .1, s, kmax=7)
    d = edt(m)
    h = dome(d, .25 * n, .17 * n, .5) + fbm(m.shape, [1.2 * SS, 3 * SS], s) * .006 * n
    alb = mix(full('#8A4E2E', n), C('#5E2E16'), np.clip(fbm(m.shape, [2 * SS, 6 * SS], s + 1) * .4 + .3, 0, 1))
    alb = mix(alb, C('#B07A4A'), sstep(1.5, 2.2, fbm(m.shape, [1.2 * SS], s + 2)) * .5)
    rgb = shade(alb, h, gloss=.4, shin=30, amb=.45, ao=.6, aos=2 * SS, edge_dark=.25, d=d, specc=(1, .9, .75))
    return finish(rgb, m, (0.03, 0.05, 0.04, 0.5))


def g_tonno(n, s):
    r = np.random.default_rng(s)
    m = np.zeros((n, n))
    for i in range(4):
        a_, rr_ = r.uniform(0, TAU), r.uniform(0, .12) * n
        m = np.maximum(m, blob(n, r.uniform(.1, .15) * n, .35, s * 10 + i, kmax=8, cx=math.cos(a_) * rr_, cy=math.sin(a_) * rr_, sx=1.3, sy=.8, rot=r.uniform(0, TAU)))
    d = edt(m)
    fl = nd.rotate(nd.gaussian_filter1d(noise((n, n), 1 * SS, s + 1), 5 * SS, axis=0), r.uniform(0, 180), reshape=False, mode='reflect')
    fl = (fl - fl.mean()) / (fl.std() + 1e-9)
    h = dome(d, .06 * n, .03 * n, .6) + fl * .004 * n
    alb = mix(full('#D4B097', n), C('#B98E74'), np.clip(fl * .3 + .3, 0, 1))
    alb = mix(alb, C('#E8CDB8'), sstep(.8, 1.8, fl) * .6)
    rgb = shade(alb, h, gloss=.45, shin=34, amb=.55, ao=.5, aos=2 * SS, edge_dark=.2, d=d, specc=(1, .97, .9))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.4))


def g_porcini(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(-.5, .5) + (math.pi if s % 2 else 0)
    th = np.linspace(math.pi, TAU, 80)
    capw, caph = .32 * n * r.uniform(.9, 1.1), .17 * n
    cap = np.stack([np.cos(th) * capw, np.sin(th) * caph], 1)
    sw = .17 * n
    stem = np.array([[capw * .7, .01 * n], [sw, .04 * n], [sw * 1.15, .2 * n], [0, .27 * n], [-sw * 1.15, .2 * n], [-sw, .04 * n], [-capw * .7, .01 * n]])
    pts = np.concatenate([cap, stem]) + np.array([0, -.04 * n])
    m = poly_mask(n, place(n, pts, rot), .9 * SS)
    d = edt(m)
    xx, yy = grid(n)
    vy = -xx * math.sin(rot) + yy * math.cos(rot)
    capzone = sstep(.0 * n, -.04 * n, vy)
    h = dome(d, .05 * n, .014 * n, .6) + fbm(m.shape, [6 * SS], s) * .0015 * n
    alb = mix(full('#EFE3C8', n), C('#D8C4A0'), np.clip(fbm(m.shape, [5 * SS], s + 1) * .3 + .2, 0, 1))
    alb = mix(alb, C('#9A6A3E'), capzone * .45)
    alb = mix(alb, C('#5E361C'), np.clip((1 - sstep(.0, .07 * n, d)) * capzone * 1.3, 0, 1))
    alb = mix(alb, C('#9A7044'), sstep(1.5, 2.3, fbm(m.shape, [2 * SS, 5 * SS], s + 2)) * .4)
    rgb = shade(alb, h, gloss=.3, shin=28, amb=.55, ao=.3, edge_dark=.1, d=d)
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.32))


def g_fiori_zucca(n, s):
    r = np.random.default_rng(s)
    rot = r.uniform(0, TAU)
    m = poly_mask(n, place(n, leaf_outline(n, .76, .14, s, lobes=3, lobe_amt=.35, tip=.6), rot), .8 * SS)
    d = edt(m)
    xx, yy = grid(n); cr, sr = math.cos(rot), math.sin(rot)
    u = (xx * cr + yy * sr) / (.38 * n); v = (-xx * sr + yy * cr) / (.14 * n)
    veins = np.exp(-((((v * 3) % 1) - .5) / .12) ** 2) * sstep(.95, .3, np.abs(u))
    h = dome(d, .05 * n, .02 * n, .5) + veins * .003 * n + fbm(m.shape, [5 * SS], s) * .004 * n
    alb = mix(full('#F4A62A', n), C('#E07612'), sstep(-.6, .9, u + fbm(m.shape, [8 * SS], s + 1) * .3))
    alb = mix(alb, C('#F9D06A'), veins * .4)
    alb = mix(alb, C('#6E8A2E'), sstep(-.6, -.95, u) * .9)
    alb = mix(alb, C('#8A4A10'), sstep(1.7, 2.4, fbm(m.shape, [2 * SS], s + 2)) * .35)
    rgb = shade(alb, h, gloss=.35, shin=30, amb=.55, ao=.3, edge_dark=.1, d=d)
    return finish(rgb, m * .97, (0.02, 0.035, 0.025, 0.38))


def g_zucchine(n, s):
    m = blob(n, .24 * n, .05, s, kmax=6, sx=1.04, sy=.96, rot=s)
    d = edt(m)
    xx, yy = grid(n); rr = np.hypot(xx, yy) / (.24 * n)
    h = dome(d, .05 * n, .012 * n, .6) + fbm(m.shape, [3 * SS], s) * .0015 * n
    alb = mix(full('#E8E3B0', n), C('#D6D08E'), np.clip(fbm(m.shape, [4 * SS], s + 1) * .3 + .3, 0, 1))
    alb = mix(alb, C('#C4BE7A'), sstep(.45, .3, rr) * sstep(1.4, 2.0, noise(m.shape, 1.2 * SS, s + 2)) * .6)
    alb = mix(alb, C('#2F5E22'), 1 - sstep(.01 * n, .025 * n, d))
    alb = mix(alb, C('#9A7A3A'), sstep(1.4, 2.1, fbm(m.shape, [3 * SS, 7 * SS], s + 3)) * .55)
    rgb = shade(alb, h, gloss=.45, shin=34, amb=.55, ao=.15, d=d)
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.32))


def sticks(n, s, count, length, width, c1, c2, burn, spread=.12, gloss=.35):
    r = np.random.default_rng(s)
    m = np.zeros((n, n)); h = np.zeros((n, n)); t = np.zeros((n, n))
    for i in range(count):
        rot = r.uniform(0, TAU); off = r.uniform(-spread, spread, 2) * n
        L = length * n * r.uniform(.75, 1.1); W = width * n * r.uniform(.8, 1.15)
        pts = np.array([[-L / 2, -W / 2], [L / 2, -W / 2], [L / 2, W / 2], [-L / 2, W / 2]]) + r.uniform(-.004, .004, (4, 2)) * n
        sm = poly_mask(n, place(n, pts, rot) + off, .9 * SS)
        sel = sm > .5
        h = np.where(sel, dome(edt(sm), W / 2, W * .35, .5) + i * .002 * n, h)
        t = np.where(sel, r.uniform(), t)
        m = np.maximum(m, sm)
    d = edt(m)
    h = nd.gaussian_filter(h, .7 * SS)
    alb = mix(full(c1, n), C(c2), np.clip(t * .6 + fbm(m.shape, [2 * SS], s) * .2, 0, 1))
    alb = mix(alb, C(burn), sstep(1.3, 2.1, fbm(m.shape, [2 * SS, 4 * SS], s + 1)) * .5)
    rgb = shade(alb, h, gloss=gloss, shin=30, amb=.5, ao=.8, aos=2 * SS, edge_dark=.25, d=d, specc=(1, .95, .8))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.45))


def g_patatine(n, s):
    return sticks(n, s, 4, .42, .07, '#EFC768', '#E0AE48', '#A8682A')


def g_zucchine_fritte(n, s):
    return sticks(n, s, 9, .34, .035, '#D9BE6A', '#BFA552', '#7A6A2A')


def g_patate(n, s):
    m = blob(n, .27 * n, .07, s, kmax=6, sx=1.1, sy=.9, rot=s)
    d = edt(m)
    h = dome(d, .03 * n, .008 * n, .6) + fbm(m.shape, [8 * SS], s) * .004 * n
    alb = mix(full('#F2D58A', n), C('#E6BC5E'), np.clip(fbm(m.shape, [5 * SS], s + 1) * .3 + .3, 0, 1))
    alb = mix(alb, C('#B9772E'), (1 - sstep(.0, .04 * n, d)) * .7)
    alb = mix(alb, C('#8A5222'), sstep(1.5, 2.2, fbm(m.shape, [2 * SS, 5 * SS], s + 2)) * .5)
    rgb = shade(alb, h, gloss=.4, shin=30, amb=.55, ao=.15, d=d, specc=(1, .95, .8))
    return finish(rgb, m, (0.012, 0.02, 0.02, 0.28))


def g_crocchetta(n, s):
    r = np.random.default_rng(s)
    m = blob(n, .14 * n, .08, s, kmax=6, sx=2.3, sy=1.0, rot=r.uniform(0, TAU))
    d = edt(m)
    cr = fbm(m.shape, [.9 * SS, 2 * SS], s + 1)
    h = dome(d, .14 * n, .09 * n, .5) + cr * .004 * n
    alb = mix(full('#D9963E', n), C('#B86E26'), np.clip(cr * .3 + .4, 0, 1))
    alb = mix(alb, C('#F0C070'), sstep(1.2, 2.0, cr) * .6)
    rgb = shade(alb, h, gloss=.3, shin=26, amb=.5, ao=.5, aos=1.5 * SS, edge_dark=.25, d=d, specc=(1, .92, .8))
    return finish(rgb, m, (0.03, 0.05, 0.04, 0.5))


def g_cipolla_caramellata(n, s):
    r = np.random.default_rng(s)
    im = Image.new('L', (n, n), 0); dr = ImageDraw.Draw(im)
    for _ in range(7):
        a0 = r.uniform(0, TAU); cx, cy = n / 2 + r.uniform(-.1, .1) * n, n / 2 + r.uniform(-.1, .1) * n
        rad = r.uniform(.08, .2) * n; span = r.uniform(1.2, 2.6); sq = r.uniform(.6, 1)
        pts = [(cx + math.cos(t) * rad, cy + math.sin(t) * rad * sq) for t in np.linspace(a0, a0 + span, 30)]
        dr.line(pts, fill=255, width=int(r.uniform(.02, .035) * n), joint='curve')
    m = nd.gaussian_filter(np.asarray(im, float) / 255, .8 * SS)
    d = edt(m)
    h = dome(d, .02 * n, .012 * n, .5)
    alb = mix(full('#B8732E', n), C('#7E4214'), np.clip(fbm(m.shape, [3 * SS, 7 * SS], s) * .4 + .3, 0, 1))
    alb = mix(alb, C('#D9A060'), sstep(1.2, 2.0, fbm(m.shape, [2 * SS], s + 1)) * .4)
    rgb = shade(alb, h, gloss=.6, shin=44, amb=.5, ao=.6, aos=2 * SS, d=d, specc=(1, .9, .75))
    return finish(rgb, m, (0.012, 0.02, 0.02, 0.3))


def g_melanzane_fritte(n, s):
    m = blob(n, .29 * n, .08, s, kmax=7, sx=1.12, sy=.9, rot=s)
    d = edt(m)
    h = dome(d, .04 * n, .01 * n, .6) + fbm(m.shape, [4 * SS], s) * .003 * n
    alb = mix(full('#D9A55A', n), C('#B97A36'), np.clip(fbm(m.shape, [3 * SS, 8 * SS], s + 1) * .4 + .3, 0, 1))
    ring = np.exp(-((d / d.max() - .45) / .12) ** 2)
    alb = mix(alb, C('#7A4E22'), sstep(1.8, 2.3, noise(m.shape, 1.1 * SS, s + 2)) * ring * .7)
    alb = mix(alb, C('#3E1C34'), (1 - sstep(.006 * n, .014 * n, d)) * .9)
    rgb = shade(alb, h, gloss=.55, shin=40, amb=.55, ao=.2, edge_dark=.1, d=d, specc=(1, .93, .8))
    return finish(rgb, m, (0.015, 0.025, 0.02, 0.32))


def g_melanzane_funghetto(n, s):
    r = np.random.default_rng(s)
    xx, yy = grid(n)
    m = np.zeros((n, n)); h = np.zeros((n, n)); sk = np.zeros((n, n))
    for i in range(5):
        rot = r.uniform(0, TAU); cx, cy = r.uniform(-.13, .13, 2) * n; w_ = r.uniform(.06, .09) * n
        pts = np.array([[-w_, -w_], [w_, -w_], [w_, w_], [-w_, w_]]) + r.uniform(-.008, .008, (4, 2)) * n
        sm = poly_mask(n, place(n, pts, rot) + np.array([cx, cy]), 1.4 * SS)
        sel = sm > .5
        h = np.where(sel, dome(edt(sm), w_ * .6, w_ * .5, .5) + i * .003 * n, h)
        u = (xx - cx) * math.cos(rot) + (yy - cy) * math.sin(rot)
        sk = np.where(sel, (u > w_ * .55) * 1.0, sk)
        m = np.maximum(m, sm)
    d = edt(m)
    alb = mix(full('#D7B27A', n), C('#B8884A'), np.clip(fbm(m.shape, [2 * SS, 5 * SS], s) * .4 + .3, 0, 1))
    alb = mix(alb, C('#3E1C34'), nd.gaussian_filter(sk, .8 * SS))
    rgb = shade(alb, nd.gaussian_filter(h, .8 * SS), gloss=.5, shin=36, amb=.5, ao=.8, aos=2 * SS, edge_dark=.3, d=d, specc=(1, .93, .82))
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.42))


def g_noci(n, s):
    r = np.random.default_rng(s)
    m = np.zeros((n, n))
    for i, ox in enumerate((-.07, .07)):
        m = np.maximum(m, blob(n, .12 * n, .3, s * 7 + i, kmax=9, cx=ox * n, sx=.8, sy=1.2))
    m = np.clip(nd.rotate(m, r.uniform(0, 180), reshape=False, order=1), 0, 1)
    d = edt(m)
    gro = np.abs(fbm(m.shape, [2.5 * SS, 5 * SS], s + 1))
    h = dome(d, .08 * n, .05 * n, .5) - (1 - sstep(.0, .25, gro)) * .008 * n
    alb = mix(full('#A9763E', n), C('#6E4420'), 1 - sstep(.0, .3, gro))
    alb = mix(alb, C('#C79A5E'), sstep(.6, 1.4, gro) * .4)
    rgb = shade(alb, h, gloss=.3, shin=28, amb=.5, ao=.7, aos=1.5 * SS, edge_dark=.25, d=d)
    return finish(rgb, m, (0.02, 0.035, 0.025, 0.45))


def g_panna(n, s):
    return cheese_pool(n, s, '#FFFFFF', '#F3EEE2', '#FFFFFF', '#F3EEE2', 0.0)


def g_fonduta(n, s):
    return cheese_pool(n, s, '#F6E2A0', '#E9C87A', '#F0D080', '#D9A848', 0.3)


def g_pachino_giallo(n, s):
    return g_pomodorini(n, s, POM_GIALLO)


ING = {
    # nome dello sprite: (funzione, lato in px). Piu' ingredienti del listino possono usare lo stesso sprite.
    'fiordilatte': (g_fiordilatte, 224), 'provola': (g_provola, 224), 'bufala': (g_bufala, 224),
    'gorgonzola': (g_gorgonzola, 160), 'parmigiano': (g_parmigiano, 192),
    'salame': (g_salame, 192), 'cotto': (g_cotto, 224), 'salsiccia': (g_salsiccia, 176),
    'nduja': (g_nduja, 176), 'crudo': (g_crudo, 288), 'alici': (g_alici, 256),
    'funghi': (g_funghi, 192), 'peperoni': (g_peperoni, 240),
    'carciofi': (g_carciofi, 192), 'friarielli': (g_friarielli, 208),
    'pomodorini': (g_pomodorini, 144), 'olive': (g_olive, 128), 'rucola': (g_rucola, 256),
    'basilico': (g_basilico, 208),
    'stracciatella': (g_stracciatella, 224), 'burrata': (g_burrata, 224), 'pecorino': (g_pecorino, 192),
    'wurstel': (g_wurstel, 160), 'mortadella': (g_mortadella, 256), 'lonza': (g_lonza, 240),
    'guanciale': (g_guanciale, 192), 'porchetta': (g_porchetta, 224), 'polpette': (g_polpette, 144),
    'tonno': (g_tonno, 192), 'porcini': (g_porcini, 208), 'fiori_zucca': (g_fiori_zucca, 256),
    'zucchine': (g_zucchine, 160), 'zucchine_fritte': (g_zucchine_fritte, 224), 'patate': (g_patate, 192),
    'patatine': (g_patatine, 224), 'crocchetta': (g_crocchetta, 192),
    'cipolla_caramellata': (g_cipolla_caramellata, 192), 'cipolla_croccante': (g_cipolla_croccante, 176),
    'melanzane_fritte': (g_melanzane_fritte, 208), 'melanzane_funghetto': (g_melanzane_funghetto, 192),
    'noci': (g_noci, 144), 'granella': (g_granella, 192), 'tarallo': (g_tarallo, 176),
    'polvere_olive': (g_polvere_olive, 192), 'pepe': (g_pepe, 192), 'origano': (g_origano, 192),
    'aglio': (g_aglio, 160), 'panna': (g_panna, 224), 'fonduta': (g_fonduta, 224),
    'pachino_giallo': (g_pachino_giallo, 144),
}


# ------------------------------------------------------------------- basi
DOUGH = dict(d='#F2DDB0', g='#DFA45A', b='#A9652C', c='#22130A', cen='#EED6A2')
CREME = {
    'crema_pistacchi': ('#9DB45A', '#7E9A3E', 40), 'vellutata_zucchine': ('#B9C97C', '#97AB5C', 41),
    'crema_zucca': ('#E8963A', '#D47528', 42), 'crema_funghi': ('#CDB28A', '#A88C64', 43),
}


def g_base(kind, ricotta=False, n=1920):
    D = DOUGH
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
    rimH = .09 * R * (1 + .22 * fbm((n, n), [25 * SS, 60 * SS], 11)) * (1.15 if ricotta else 1)
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
    dough = C(D['d']); gold = C(D['g']); brown = C(D['b']); char = C(D['c'])
    top = np.clip(h / (.09 * R), 0, 1.2)
    tone = fbm((n, n), [14 * SS, 35 * SS], 13)
    alb = mix(np.broadcast_to(dough, (n, n, 3)).copy(), gold, np.clip(top ** .8 * (.8 + .2 * tone) + sstep(.95, 1.0, rn) * .5, 0, 1))
    bz = sstep(.35, 1.25, fbm((n, n), [12 * SS, 30 * SS], 28) * .6 + top * .9 + bub * .4 - .25)
    alb = mix(alb, brown, bz * .7)
    rimz = sstep(.79, .85, rn)
    leo = fbm((n, n), [4 * SS, 8 * SS], 14)
    spot = sstep(2.25, 2.7, leo + top * .5) * rimz
    halo = sstep(1.6, 2.25, leo + top * .5) * rimz * (1 - spot)
    alb = mix(alb, brown * .7, halo * .55)
    alb = mix(alb, char, spot * .92)
    flour = sstep(2.4, 2.9, noise((n, n), .8 * SS, 15)) * sstep(.9, .96, rn)
    alb = mix(alb, C('#F7F1E3'), flour * .6)
    gloss = np.full((n, n), .05)
    if ricotta:
        # ricotta che affiora dalle crepe del cornicione ripieno
        r2 = np.random.default_rng(99)
        rc = np.zeros((n, n))
        for _ in range(34):
            a_, d_ = r2.uniform(0, TAU), r2.uniform(.86, .91) * R
            cx, cy = math.cos(a_) * d_, math.sin(a_) * d_
            br = r2.uniform(.012, .03) * R
            rc = np.maximum(rc, np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / br ** 2)))
        rcm = sstep(.35, .7, rc + fbm((n, n), [2 * SS], 98) * .1)
        alb = mix(alb, C('#F8F4EA'), rcm * .95)
        h = h + rcm * .004 * R
        gloss = gloss + rcm * .15
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


def g_crema(c1, c2, seed, n=1920):
    """Strato di crema steso sul centro (stessa scala delle basi: raggio 0.47 n)."""
    xx, yy = grid(n)
    rr = np.hypot(xx, yy)
    R = .47 * n
    sedge = R * (.77 + .015 * fbm((n, n), [40 * SS], seed)) + fbm((n, n), [10 * SS], seed + 1) * .008 * R
    a = sstep(3 * SS, -6 * SS, rr - sedge)
    st = fbm((n, n), [5 * SS, 14 * SS, 36 * SS], seed + 2)
    swirl = np.sin(np.arctan2(yy, xx) * 3 + rr / (.06 * R) + st * 1.5)
    alb = mix(full(c1, n), C(c2), np.clip(st * .3 + .5 + swirl * .08, 0, 1))
    h = .004 * R * a + st * .0012 * R + swirl * .0006 * R
    rgb = shade(alb, h, gloss=.38, shin=36, amb=.58, specc=(1, .97, .92))
    img = np.dstack([rgb, np.clip(a * .97, 0, 1)])
    im = Image.fromarray((img * 255 + .5).astype(np.uint8), 'RGBA')
    return im.convert('RGBa').resize((n // SS, n // SS), Image.LANCZOS).convert('RGBA')


if __name__ == '__main__':
    for name, (fn, px) in ING.items():
        if ONLY and name not in ONLY and 'ing' not in ONLY:
            continue
        n = px * SS
        strip = Image.new('RGBA', (px * VARS, px))
        for v in range(VARS):
            strip.paste(fn(n, 1000 + v * 17 + len(name)), (px * v, 0))
        strip.save(os.path.join(OUT, f'{name}.webp'), 'WEBP', quality=88, method=6)
        print(name, flush=True)
    if not ONLY or 'basi' in ONLY:
        for kind in ('rossa', 'bianca'):
            g_base(kind).save(os.path.join(OUT, f'base-{kind}.webp'), 'WEBP', quality=84, method=6)
            g_base(kind, True).save(os.path.join(OUT, f'base-{kind}-ricotta.webp'), 'WEBP', quality=84, method=6)
            print('base', kind, flush=True)
    if not ONLY or 'creme' in ONLY:
        for name, (c1, c2, seed) in CREME.items():
            g_crema(c1, c2, seed).save(os.path.join(OUT, f'{name}.webp'), 'WEBP', quality=84, method=6)
            print('crema', name, flush=True)
