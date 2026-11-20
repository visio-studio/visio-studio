# fogli A3 orizzontali in HTML (scala 1:50) con cartiglio, nomi delle stanze, quote d'ingombro, legenda e note
import json,sys
D=sys.argv[1];I=json.load(open(f'{D}/info.json'));X0,X1,Z0,Z1=I['ritaglio'];WM,HM=(X1-X0)*20,(Z1-Z0)*20  # mm a 1:50
def uv(x,z):return ((X1-x)*20,(Z1-z)*20)   # ruotato di 180°: come le piante del preventivo
ST={'terra':[('Soggiorno',9.8,-5.6),('Pranzo',14.75,-4.9),('Cucina',19.5,-3.6),('Scala',13.1,-2.0)],
    'camere':[('Camera A',9.4,-5.5),('Camera B',15.6,-6.1),('Camera C',16.4,-2.3),('Bagno D.1',12.0,-6.4),('Bagno D.2',8.7,-1.7),('Disimpegno',12.0,-2.8)]}
PIANO={'terra':'Piano terra','camere':'Piano camere'}
FOGLI=[('ante','terra','P01'),('post','terra','P02'),('confronto','terra','P03'),('ante','camere','P04'),('post','camere','P05'),('confronto','camere','P06')]
TIT={'ante':'Stato attuale · ante operam','post':'Progetto · post operam','confronto':'Demolizioni e costruzioni'}
NOTE={'ante':"Pianta ricavata dal rilievo Polycam del 6 ottobre 2026, sezione orizzontale a 1,20 m dal pavimento; in grigio la casa vista dall'alto. Le linee sono le superfici interne dei muri misurate: spessori e facce esterne non sono rilevati. Misure da confermare al rilievo.",
 'post':"Pianta ricavata dal modello SketchUp «Traversa definitivo», sezione orizzontale a 1,20 m; muri in nero, arredi visti dall'alto in grigio. Nel modello le dimensioni risultano circa il 4-5 % maggiori di quelle del rilievo Polycam: da verificare prima dei disegni esecutivi.",
 'confronto':"Confronto automatico fra rilievo e modello, indicativo: il rilievo è riscalato sul modello (×1,05 al piano terra, ×1,04 al piano camere). Le demolizioni e le nuove costruzioni da realizzare sono quelle indicate nel preventivo (voci A.1 e A.6) e nei disegni esecutivi."}
LEG={'ante':[('#141414','Superfici dei muri oggi (rilievo)')],
 'post':[('#191919','Muri di progetto, in sezione'),('#bdbdbd','Arredi visti dall’alto')],
 'confronto':[('#5f5f5f','Muri che restano'),('#ebb400','Da demolire'),('#d22323','Da costruire'),('#b9c3d7','Rilievo di oggi')]}
pag=[]
for tipo,piano,num in FOGLI:
    inf=I['info'][piano+'_ante' if tipo=='ante' else piano];bx0,bx1,bz0,bz1=inf['bbox'];u0,v0=uv(bx1,bz1);u1,v1=uv(bx0,bz0)
    et=''.join(f'<div class="st" style="left:{uv(x,z)[0]:.1f}mm;top:{uv(x,z)[1]:.1f}mm">{n}</div>' for n,x,z in ST[piano]) if tipo!='ante' else ''
    quote=f'''<svg class="q" width="{WM:.1f}mm" height="{HM:.1f}mm" viewBox="0 0 {WM:.1f} {HM:.1f}">
     <g stroke="#333" stroke-width=".18" fill="none"><line x1="{u0:.1f}" y1="-6" x2="{u1:.1f}" y2="-6"/><line x1="{u0:.1f}" y1="-8" x2="{u0:.1f}" y2="-4"/><line x1="{u1:.1f}" y1="-8" x2="{u1:.1f}" y2="-4"/>
     <line x1="-6" y1="{v0:.1f}" x2="-6" y2="{v1:.1f}"/><line x1="-8" y1="{v0:.1f}" x2="-4" y2="{v0:.1f}"/><line x1="-8" y1="{v1:.1f}" x2="-4" y2="{v1:.1f}"/></g>
     <text x="{(u0+u1)/2:.1f}" y="-7.2" text-anchor="middle">{str(inf['larg']).replace('.',',')} m{' (rilievo)' if tipo=='ante' else ''}</text>
     <text transform="translate(-7.2 {(v0+v1)/2:.1f}) rotate(-90)" text-anchor="middle">{str(inf['prof']).replace('.',',')} m</text></svg>'''
    leg=''.join(f'<span><i style="background:{c}"></i>{t}</span>' for c,t in LEG[tipo])
    pag.append(f'''<section class="f"><div class="dis" style="width:{WM:.1f}mm;height:{HM:.1f}mm"><img src="{tipo}-{piano}.png">{quote}{et}</div>
 <div class="car"><div class="c1"><b>Casa Traversa</b><span>Silvia e Stefano Traversa · Aprilia</span></div>
  <div class="c2"><b>{PIANO[piano]} · {TIT[tipo]}</b><p>{NOTE[tipo]}</p><div class="leg">{leg}</div></div>
  <div class="c3"><div class="sc"><svg width="50mm" height="6mm" viewBox="0 0 50 6"><g fill="#111"><rect x="0" y="1" width="10" height="1.6"/><rect x="20" y="1" width="20" height="1.6"/></g><rect x="0" y="1" width="50" height="1.6" fill="none" stroke="#111" stroke-width=".2"/>
   <g font-size="2.4" fill="#111"><text x="0" y="5.6">0</text><text x="9" y="5.6">0,5</text><text x="19.4" y="5.6">1</text><text x="39.4" y="5.6">2</text><text x="46" y="5.6">2,5 m</text></g></svg></div>
   <span>Scala 1:50 su A3 · sezione a 1,20 m</span><span>VISIO Studio · 20 novembre 2026</span><b class="n">{num}</b></div></div></section>''')
css='''@import url("font/visio.css");@page{size:420mm 297mm;margin:0}*{box-sizing:border-box;margin:0;padding:0}body{font-family:Inter,sans-serif;color:#111;background:#fff}
.f{width:420mm;height:297mm;position:relative;page-break-after:always;overflow:hidden}
.dis{position:absolute;left:54mm;top:24mm}.dis img{width:100%;height:100%;display:block}
.q{position:absolute;left:0;top:0;overflow:visible}.q text{font-size:3px;fill:#222}
.st{position:absolute;transform:translate(-50%,-50%);font-family:"Cormorant Garamond",serif;font-size:13pt;letter-spacing:.5px;background:rgba(255,255,255,.82);padding:.6mm 2mm;white-space:nowrap}
.car{position:absolute;left:12mm;right:12mm;bottom:10mm;height:42mm;border-top:.4mm solid #111;display:grid;grid-template-columns:70mm 1fr 92mm;gap:8mm;padding-top:4mm}
.c1 b{display:block;font-family:"Cormorant Garamond",serif;font-weight:400;font-size:24pt;line-height:1}.c1 span{font-size:8pt;color:#555;display:block;margin-top:2mm}
.c2 b{font-size:11pt;font-weight:500;letter-spacing:.3px}.c2 p{font-size:7.6pt;line-height:1.5;color:#444;margin-top:1.6mm;max-width:190mm}
.leg{display:flex;gap:6mm;flex-wrap:wrap;margin-top:2.2mm;font-size:7.6pt}.leg i{display:inline-block;width:6mm;height:2.6mm;margin-right:1.6mm;vertical-align:-.3mm;border:.1mm solid #888}
.c3{position:relative;font-size:7.6pt;color:#444}.c3 span{display:block;margin-top:1mm}.c3 .n{position:absolute;right:0;top:0;font-family:"Cormorant Garamond",serif;font-weight:400;font-size:30pt;color:#111}
.f::before{content:"";position:absolute;inset:8mm;border:.3mm solid #111;pointer-events:none}'''
open(f'{D}/fogli.html','w').write(f'<!doctype html><html lang="it"><meta charset="utf-8"><title>Casa Traversa — piante ante e post operam</title><style>{css}</style><body>{"".join(pag)}</body></html>')
print('fogli',len(pag))
