# Progetto Mario: pianta arredata in PDF (A2 orizzontale, scala 1:50) dal disegno di pianta-mario.py.
# Uso: python -I impagina-mario.py pianta.png stanze.json info.json etichette.json uscita.pdf anteprima.jpg
# etichette.json = [[nome, x, z, mostra_superficie], ...] in metri del modello; le superfici vengono da stanze.json.
import sys, json, datetime
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
png, stz, inf, etj, out, ant = sys.argv[1:7]
I = json.load(open(inf)); X0, Z0, PX = I['X0'], I['Z0'], I['PX']
ST = {s['n']: s for s in json.load(open(stz))['stanze']}; ET = json.load(open(etj))
im = Image.open(png).convert('RGB')
# ritaglio al disegno (tutto ciò che non è bianco) con 30 cm di margine
import numpy as np
a = np.asarray(im); m = (a < 245).any(2); ys, xs = np.where(m)
r = int(0.3 * PX); x0, x1, y0, y1 = max(xs.min() - r, 0), min(xs.max() + r, im.width), max(ys.min() - r, 0), min(ys.max() + r, im.height)
im = im.crop((x0, y0, x1, y1))
SCALA = 50; MMPM = 1000 / SCALA                       # mm di carta per metro
PW, PH = 594 * mm, 420 * mm                           # A2 orizzontale
dw, dh = im.width / PX * MMPM * mm, im.height / PX * MMPM * mm
CART = 92 * mm; MAR = 12 * mm
ox = MAR + (PW - 2 * MAR - CART - dw) / 2; oy = (PH - dh) / 2
def carta(x, z):  # metri del modello -> punto sulla carta
    return ox + ((x - X0) * PX - x0) / PX * MMPM * mm, oy + dh - ((z - Z0) * PX - y0) / PX * MMPM * mm
c = canvas.Canvas(out, pagesize=(PW, PH)); c.setTitle('Progetto Mario — Pianta arredata'); c.setAuthor('VISIO Studio')
c.setStrokeColorRGB(.1, .1, .1); c.setLineWidth(.5); c.rect(MAR / 2, MAR / 2, PW - MAR, PH - MAR)
import io as _io; _b = _io.BytesIO(); im.save(_b, 'JPEG', quality=90, optimize=True); _b.seek(0)   # JPEG: un terzo del peso
c.drawImage(ImageReader(_b), ox, oy, dw, dh)
# nomi delle stanze
for nome, x, z, sup in ET:
    px_, py_ = carta(x, z); s = ST.get(nome)
    c.setFillColorRGB(1, 1, 1); c.setFillAlpha(.78)
    w = max(c.stringWidth(nome.upper(), 'Helvetica', 8.5), c.stringWidth('00,0 m²', 'Helvetica', 7.5) if (sup and s) else 0) + 6 * mm
    hh = (11 if (sup and s) else 6.5) * mm
    c.roundRect(px_ - w / 2, py_ - hh / 2, w, hh, 1.2 * mm, stroke=0, fill=1); c.setFillAlpha(1)
    c.setFillColorRGB(.08, .08, .08); c.setFont('Helvetica', 8.5)
    c.drawCentredString(px_, py_ + (1.2 * mm if (sup and s) else -1.1 * mm), nome.upper())
    if sup and s:
        c.setFont('Helvetica', 7.5); c.setFillColorRGB(.35, .3, .22); c.drawCentredString(px_, py_ - 3.4 * mm, f"{s['m2']:.1f}".replace('.', ',') + ' m²')
# scala grafica 0-5 m sotto il disegno
sx, sy = ox, oy - 9 * mm
for i in range(5):
    c.setFillColorRGB(*((.1, .1, .1) if i % 2 == 0 else (1, 1, 1))); c.rect(sx + i * MMPM * mm, sy, MMPM * mm, 1.8 * mm, stroke=1, fill=1)
c.setFillColorRGB(.1, .1, .1); c.setFont('Helvetica', 7)
for i in range(6): c.drawCentredString(sx + i * MMPM * mm, sy - 3.6 * mm, f'{i}')
c.drawString(sx + 5 * MMPM * mm + 3 * mm, sy, 'm')
# cartiglio a destra
cx = PW - MAR / 2 - CART; cw = CART
c.setLineWidth(.4); c.line(cx, MAR / 2, cx, PH - MAR / 2)
y = PH - MAR - 10 * mm
c.setFillColorRGB(.79, .66, .43); c.setFont('Helvetica', 7.5); c.drawString(cx + 7 * mm, y, 'V I S I O   S T U D I O')
y -= 16 * mm; c.setFillColorRGB(.08, .08, .08); c.setFont('Times-Roman', 26); c.drawString(cx + 7 * mm, y, 'Progetto Mario')
y -= 9 * mm; c.setFont('Helvetica', 11); c.drawString(cx + 7 * mm, y, 'Pianta arredata')
y -= 6 * mm; c.setFont('Helvetica', 8.5); c.setFillColorRGB(.35, .35, .35); c.drawString(cx + 7 * mm, y, 'Progetto definitivo')
def riga(y, k, v):
    c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 7); c.drawString(cx + 7 * mm, y, k.upper())
    c.setFillColorRGB(.08, .08, .08); c.setFont('Helvetica', 9.5); c.drawString(cx + 7 * mm, y - 4.6 * mm, v)
    c.setStrokeColorRGB(.85, .85, .85); c.line(cx + 7 * mm, y - 7.5 * mm, cx + cw - 7 * mm, y - 7.5 * mm)
y -= 16 * mm
for k, v in (('Scala', '1:50 sul foglio A2'), ('Sezione orizzontale', 'a 1,20 m dal pavimento'), ('Fonte', 'modello SketchUp di progetto'), ('Data', datetime.date.today().strftime('%d/%m/%Y'))):
    riga(y, k, v); y -= 13 * mm
y -= 2 * mm; c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 7); c.drawString(cx + 7 * mm, y, 'LEGENDA'); y -= 6 * mm
for col, t in (((.094, .094, .094), 'Muri tagliati dalla sezione'), ((.68, .5, .33), 'Parquet a spina di pesce in rovere'), ((.27, .27, .27), 'Arredi e infissi tagliati: linea sottile')):
    c.setFillColorRGB(*col); c.rect(cx + 7 * mm, y - .6 * mm, 6 * mm, 3.2 * mm, stroke=0, fill=1)
    c.setFillColorRGB(.1, .1, .1); c.setFont('Helvetica', 8); c.drawString(cx + 16 * mm, y, t); y -= 6.5 * mm
y -= 4 * mm; c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 7); c.drawString(cx + 7 * mm, y, 'NOTE'); y -= 5 * mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
nota = ("Disegno ricavato dal modello 3D di progetto, arredi compresi. Le superfici sono nette e indicative, misurate "
        "sul disegno fino alle porte; la zona giorno è un unico ambiente aperto. Pianta non quotata: misure e spessori "
        "dei muri si confermano al rilievo prima dei disegni esecutivi. Arredi, tessili e oggetti sono indicativi.")
p = Paragraph(nota, ParagraphStyle('n', fontName='Helvetica', fontSize=7.8, leading=10.5, textColor=(.2, .2, .2)))
_, ph = p.wrap(cw - 14 * mm, 200 * mm); p.drawOn(c, cx + 7 * mm, y - ph)
c.setFillColorRGB(.45, .45, .45); c.setFont('Helvetica', 6.8)
for i, t in enumerate(('Michelessi Corporation Srl · P.IVA 03294220599', 'info@visiorender.it · +39 342 668 4232 · visiorender.it')):
    c.drawString(cx + 7 * mm, MAR + 6 * mm - i * 4 * mm, t)
c.showPage(); c.save()
# anteprima per la pagina web: il disegno da solo, largo 2400 px
t = im.copy(); t.thumbnail((2400, 2400)); t.save(ant, quality=86, optimize=True, progressive=True)
print('pdf', out, 'disegno', round(dw / mm), 'x', round(dh / mm), 'mm')
