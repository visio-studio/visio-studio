# Progetto Mario: piante ante e post operam in un PDF (tre tavole A2 orizzontali, scala 1:50), stesso ritaglio per tutte.
# uso: python -I impagina-ante-post.py cartella info.json stanze.json etichette.json uscita.pdf cartella_anteprime
#   cartella = ante-post-mario.py (ante.png, post.png, confronto.png, ante-post.json); info.json, stanze.json, etichette.json
#   come per impagina-mario.py. Le anteprime per la pagina web si chiamano ante.jpg, post.jpg, confronto.jpg.
import sys, json, datetime, io, numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
D, inf, stz, etj, out, ANT = sys.argv[1:7]
I = json.load(open(inf)); X0, Z0, PX = I['X0'], I['Z0'], I['PX']
ST = {s['n']: s for s in json.load(open(stz))['stanze']}; ET = json.load(open(etj))
IM = {n: Image.open(f'{D}/{n}.png').convert('RGB') for n in ('ante', 'post', 'confronto')}
# ritaglio comune: tutto ciò che non è bianco in almeno una tavola, con 30 cm di margine
m = np.zeros(IM['ante'].size[::-1], bool)
for im in IM.values(): m |= (np.asarray(im) < 245).any(2)
ys, xs = np.where(m); r = int(0.3 * PX); W0, H0 = IM['ante'].size
x0, x1, y0, y1 = max(xs.min() - r, 0), min(xs.max() + r, W0), max(ys.min() - r, 0), min(ys.max() + r, H0)
IM = {k: v.crop((x0, y0, x1, y1)) for k, v in IM.items()}
SCALA = 50; MMPM = 1000 / SCALA; PW, PH = 594 * mm, 420 * mm
w, h = IM['ante'].size; dw, dh = w / PX * MMPM * mm, h / PX * MMPM * mm
CART = 92 * mm; MAR = 12 * mm; ox = MAR + (PW - 2 * MAR - CART - dw) / 2; oy = (PH - dh) / 2
def carta(x, z): return ox + ((x - X0) * PX - x0) / PX * MMPM * mm, oy + dh - ((z - Z0) * PX - y0) / PX * MMPM * mm
c = canvas.Canvas(out, pagesize=(PW, PH)); c.setTitle('Progetto Mario — Piante ante e post operam'); c.setAuthor('VISIO Studio')
OGGI = datetime.date.today().strftime('%d/%m/%Y')
TAV = [
 ('ante', 'Stato attuale', 'Ante operam', 'rilievo Polycam (scansione unica)',
  [((.094, .094, .094), 'Muri e ingombri rilevati'), ((.55, .55, .55), 'Vista dall\'alto della scansione')],
  "Stato di fatto dalla scansione 3D del rilievo, vista dall'alto con le sue fotografie. I muri sono ricavati dalla "
  "scansione: le strisce non rilevate fra due stanze. Le parti non scansionate (facce esterne dei muri perimetrali, "
  "interno degli armadi) non compaiono o compaiono come ingombri. Misure da confermare al rilievo "
  "metrico prima dei disegni esecutivi."),
 ('post', 'Progetto', 'Post operam', 'modello SketchUp di progetto',
  [((.094, .094, .094), 'Muri tagliati dalla sezione'), ((.68, .5, .33), 'Parquet a spina di pesce in rovere'), ((.27, .27, .27), 'Arredi e infissi: linea sottile')],
  "Progetto definitivo con gli arredi, dalla sezione del modello 3D a 1,20 m. Superfici nette e indicative, misurate sul "
  "disegno fino alle porte; la zona giorno è un unico ambiente aperto. Arredi, tessili e oggetti sono indicativi."),
 ('confronto', 'Demolizioni e costruzioni', 'Confronto', 'rilievo sovrapposto al progetto',
  [((.37, .37, .37), 'Muri esistenti che restano'), ((.82, .14, .14), 'Muri nuovi'), ((.92, .71, 0), 'Da demolire'),
   ((.69, .69, .69), 'Fuori dalla zona rilevata'), ((.59, .67, .8), 'Bordo della scansione')],
  "Rilievo allineato al modello sui muri (rotazione e spostamento calcolati, il 60 % dei muri rilevati cade entro 15 cm "
  "da quelli di progetto). Un muro di progetto è esistente se a meno di 45 cm c'è un muro rilevato. Le campiture gialle "
  "sono indicative e vanno verificate in sopralluogo: possono essere arredi fissi o armadi rilevati come ingombri."),
]
for k, tit, sot, fonte, leg, nota in TAV:
    c.setStrokeColorRGB(.1, .1, .1); c.setLineWidth(.5); c.rect(MAR / 2, MAR / 2, PW - MAR, PH - MAR)
    b = io.BytesIO(); IM[k].save(b, 'JPEG', quality=90, optimize=True); b.seek(0); c.drawImage(ImageReader(b), ox, oy, dw, dh)
    if k != 'ante':
        for nome, x, z, sup in ET:
            px_, py_ = carta(x, z); s = ST.get(nome); sup = sup and s and k == 'post'
            c.setFillColorRGB(1, 1, 1); c.setFillAlpha(.78)
            ww = max(c.stringWidth(nome.upper(), 'Helvetica', 8.5), c.stringWidth('00,0 m²', 'Helvetica', 7.5) if sup else 0) + 6 * mm
            hh = (11 if sup else 6.5) * mm
            c.roundRect(px_ - ww / 2, py_ - hh / 2, ww, hh, 1.2 * mm, stroke=0, fill=1); c.setFillAlpha(1)
            c.setFillColorRGB(.08, .08, .08); c.setFont('Helvetica', 8.5); c.drawCentredString(px_, py_ + (1.2 * mm if sup else -1.1 * mm), nome.upper())
            if sup: c.setFont('Helvetica', 7.5); c.setFillColorRGB(.35, .3, .22); c.drawCentredString(px_, py_ - 3.4 * mm, f"{s['m2']:.1f}".replace('.', ',') + ' m²')
    sx, sy = ox, oy - 9 * mm
    for i in range(5):
        c.setFillColorRGB(*((.1, .1, .1) if i % 2 == 0 else (1, 1, 1))); c.rect(sx + i * MMPM * mm, sy, MMPM * mm, 1.8 * mm, stroke=1, fill=1)
    c.setFillColorRGB(.1, .1, .1); c.setFont('Helvetica', 7)
    for i in range(6): c.drawCentredString(sx + i * MMPM * mm, sy - 3.6 * mm, f'{i}')
    c.drawString(sx + 5 * MMPM * mm + 3 * mm, sy, 'm')
    cx = PW - MAR / 2 - CART; cw = CART
    c.setLineWidth(.4); c.line(cx, MAR / 2, cx, PH - MAR / 2)
    y = PH - MAR - 10 * mm
    c.setFillColorRGB(.79, .66, .43); c.setFont('Helvetica', 7.5); c.drawString(cx + 7 * mm, y, 'V I S I O   S T U D I O')
    y -= 16 * mm; c.setFillColorRGB(.08, .08, .08); c.setFont('Times-Roman', 26); c.drawString(cx + 7 * mm, y, 'Progetto Mario')
    y -= 9 * mm; c.setFont('Helvetica', 11); c.drawString(cx + 7 * mm, y, tit)
    y -= 6 * mm; c.setFont('Helvetica', 8.5); c.setFillColorRGB(.35, .35, .35); c.drawString(cx + 7 * mm, y, sot)
    def riga(y, a, v):
        c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 7); c.drawString(cx + 7 * mm, y, a.upper())
        c.setFillColorRGB(.08, .08, .08); c.setFont('Helvetica', 9.5); c.drawString(cx + 7 * mm, y - 4.6 * mm, v)
        c.setStrokeColorRGB(.85, .85, .85); c.line(cx + 7 * mm, y - 7.5 * mm, cx + cw - 7 * mm, y - 7.5 * mm)
    y -= 16 * mm
    for a, v in (('Tavola', f'{[t[0] for t in TAV].index(k) + 1} di {len(TAV)}'), ('Scala', '1:50 sul foglio A2'), ('Sezione orizzontale', 'a 1,20 m dal pavimento'), ('Fonte', fonte), ('Data', OGGI)):
        riga(y, a, v); y -= 13 * mm
    y -= 2 * mm; c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 7); c.drawString(cx + 7 * mm, y, 'LEGENDA'); y -= 6 * mm
    for col, t in leg:
        c.setFillColorRGB(*col); c.rect(cx + 7 * mm, y - .6 * mm, 6 * mm, 3.2 * mm, stroke=0, fill=1)
        c.setFillColorRGB(.1, .1, .1); c.setFont('Helvetica', 8); c.drawString(cx + 16 * mm, y, t); y -= 6.5 * mm
    y -= 4 * mm; c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 7); c.drawString(cx + 7 * mm, y, 'NOTE'); y -= 5 * mm
    p = Paragraph(nota, ParagraphStyle('n', fontName='Helvetica', fontSize=7.8, leading=10.5, textColor=(.2, .2, .2)))
    _, ph = p.wrap(cw - 14 * mm, 200 * mm); p.drawOn(c, cx + 7 * mm, y - ph)
    c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 6.8)
    for i, t in enumerate(('Michelessi Corporation Srl · P.IVA 03294220599', 'info@visiorender.it · +39 342 668 4232 · visiorender.it')):
        c.drawString(cx + 7 * mm, MAR + 6 * mm - i * 4 * mm, t)
    c.showPage()
    t = IM[k].copy(); t.thumbnail((2400, 2400)); t.save(f'{ANT}/{k}.jpg', quality=86, optimize=True, progressive=True)
c.save(); print('pdf', out, 'disegno', round(dw / mm), 'x', round(dh / mm), 'mm')
