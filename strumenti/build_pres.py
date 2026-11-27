import json,re,os,shutil,sys
S,R=sys.argv[1],sys.argv[2]
D=S+'/deck/project';OUT=R+'/presentazione';os.makedirs(OUT+'/img',exist_ok=True)
M={'63f7541d94f2081a05b94e6cabc3615c':R+'/img/render-fotorealistico-soggiorno-villa-vista-mare.jpg','9c6621614cc10eb9bc33c76b5d3fec45':R+'/img/lidar-scan.jpg','e44dfcc1ee1e1f1386cbd96c3f275f51':R+'/img/render-3d-soggiorno-open-space-villa.jpg','8fef79a3ee182a5d9bc35c7628e418be':R+'/img/foto-realizzato-soggiorno-open-space-villa.jpg','a124438ee780e677c01e2f9cceae5faf':R+'/img/planimetria-quotata.jpg','04e981cf07d9cd3c30318b4acafbf4da':R+'/img/modello-3d-assonometria.jpg','b85489e9d211c9c7c562ea249c737c01':R+'/img/schema-impianti.jpg','75157ffb66e630bef278deca617d0ad6':R+'/img/render-esterno-1.jpg','a19c5e164443f24dda28d769aae515ae':R+'/img/render-notturna.jpg','fbd2aab2faa3ea5f0cbbea833ac8fdb6':R+'/img/light-natural.jpg','0b465545466e3cb8acb7a6c264dda712':R+'/img/room-360-tour.jpg','fa5e4a01db34ad6d96653678156f4386':R+'/img/ar-vuoto.jpg','48babebdeab34c410788dd196dbe665b':R+'/img/render-living.jpg','ec00d762c1a07016accc9e7f7bdb4192':S+'/aree/c-config.jpg','7bc35ceb486a3089df72bb2b32a669fd':S+'/aree/c-primadopo.jpg','f14cb15d9827bdc5486f72a1e803c61b':R+'/area-mr26/render/studio.jpg','818fe6d38b26933415d11654f47c2cbd':R+'/area-mr26/render/assonometria.jpg','ebcedbd8c157a3f1c6f98ac8b4ecf2d0':R+'/project1/img/modello-esploso.jpg','3c8b5e91b72bc12f7ca3428503ef77ad':R+'/project1/img/modello-v5.jpg','5a46ca118140ad45dee29208f3972fdc':R+'/img/light-off.jpg','984871274582d8fac7f665994eca56e8':R+'/img/light-direct.jpg','df8c001cfd8afad11c161f89cf0837b6':R+'/img/light-accent.jpg','60b77a4e772770fa4c8c1f14a2889368':R+'/img/light-ambient.jpg','5d4bfcbbf28a933800981b0fad0a7708':S+'/strum/u-luci.jpg','2e81af961c968453bead480bb976ebab':S+'/strum/u-solare.jpg','d0337de3fdcac5d601d0ca47b23d12b4':S+'/strum/u-vrar.jpg','8f2d558dbd2acdfec4947f504936b65e':S+'/strum/u-qr.jpg','fb02f2f9bac0bb1fcb8f97a5bc3f3b59':S+'/strum/u-arredo.jpg','7f54d70a268dd4851da8ee5dd5df5416':S+'/strum/u-sole.jpg','ac37e355e39997c3b947363a5ee3f765':S+'/strum/u-tour-sog.jpg','61dbf5fe9727f406b091b9f1d0b6e468':S+'/strum/u-tour-cuc.jpg','cc76160401666b722f591fe049409b73':S+'/strum/u-modello.jpg','47395e9d00aec87734b4c32011192faf':S+'/strum/t-attesa.jpg','17712eaf6ff0e525a92df35f5514ffa7':S+'/strum/t-ingresso.jpg','8f98099f7c9554d41d8740323806d3ec':S+'/strum/m-cammina.jpg','c1879e171c32c2dec0a57a6223baca85':S+'/strum/m-modello.jpg','250e3f7d27d815ac89c0ebeafe068a0f':S+'/mad/mad-esploso.jpg','faa63a8805c5ba1715d53807d475e073':S+'/mad/sc-esploso.jpg','5ec66cee72e96102db9803e8c37b8546':S+'/mad/sc-distinta.jpg','4875be47127f9dc91c6b8731bf1d71ba':S+'/strum/fn-tour.jpg','cddfeb3eb20465eccb1f530501f86f60':R+'/img/esterni-2/frame-0001.jpg','539995d2bba64ef6442e69c7df094c64':R+'/img/esterni-2/frame-0020.jpg','c1df75b1e331783e80122ff1e488e5a7':R+'/img/esterni-2/frame-0040.jpg','f487606a4232071c7415f003d7b542d2':R+'/img/esterni-2/frame-0060.jpg'}
IC={'Star':'star','Activity':'activity','Globe':'globe','Book':'book-open','Tool':'hammer','Home':'house','Clock':'clock','Lightbulb':'lightbulb','Link':'link','Search':'search','Verified':'badge-check','Lightning':'zap','Settings':'settings','CheckCircle':'circle-check','Database':'database','Users':'users','Trust':'handshake','Play':'play','Wrench':'wrench','Chart':'chart-column','Key':'qr-code','Lock':'door-open','Cloud':'sprout'}
def svg(n):
    s=open(S+'/luc/package/icons/'+IC[n]+'.svg').read()
    s=re.sub(r'<!--.*?-->','',s,flags=re.S).strip()
    s=re.sub(r'<svg[^>]*>','<svg class="xi" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">',s,1)
    return re.sub(r'\s+',' ',s)
deck=json.load(open(D+'/deck.json'));used={}
def img(m):
    i=m.group(1);src=M[i];name=i[:10]+'.jpg'
    if name not in used:shutil.copy(src,OUT+'/img/'+name);used[name]=1
    return 'src="img/'+name+'"'
parts=[]
for sid in deck['order']:
    h=open(D+'/slides/'+sid+'.html').read()
    h=re.sub(r'src="/_blob/([0-9a-f]{32})"',img,h)
    h=re.sub(r'<x-icon name="(\w+)"[^>]*></x-icon>',lambda m:svg(m.group(1)),h)
    h=re.sub(r'<aside>.*?</aside>','',h,flags=re.S)
    assert '_blob' not in h and 'x-icon' not in h,sid
    parts.append('<div class="slot">'+h.strip()+'</div>')
css=open(D+'/deck.css').read().replace('.ib x-icon','.ib svg')
page='''<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>VISIO Studio · I nostri servizi</title>
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../font/visio.css">
<style>
html,body{margin:0;background:#0A0A0A}
*{box-sizing:border-box}
.slot{width:100%;overflow:hidden;position:relative;margin:0 auto 12px}
.slot>section{width:1920px;height:1080px;position:relative;overflow:hidden;transform-origin:0 0;display:block}
.slot>section *{box-sizing:content-box}
.slot>section img{display:block}
.xi{width:42px;height:42px}
table{border-collapse:collapse}
.tab td,.tab th{padding:9px 14px;text-align:left;border-bottom:1px solid rgba(201,169,110,.25);font-weight:400}
.tab th{font-weight:600}
ul.lst{list-style:disc}
#bar{position:fixed;right:16px;bottom:16px;z-index:9;display:flex;gap:8px}
#bar a{font:500 14px Inter,Arial,sans-serif;letter-spacing:1px;color:#0A0A0A;background:#C9A96E;padding:12px 18px;border-radius:24px;text-decoration:none}
@media print{
 @page{size:1920px 1080px;margin:0}
 html,body{background:none}
 #bar{display:none}
 .slot{width:1920px!important;height:1080px!important;margin:0;page-break-after:always;break-after:page}
 .slot>section{transform:none!important}
 .arrive{animation:none!important}
}
'''+css+'''
</style></head><body>
<div id="bar"><a href="VISIO-Studio-servizi.pdf" download>Scarica il PDF</a></div>
'''+'\n'.join(parts)+'''
<script>
function fit(){var w=Math.min(innerWidth,1920);document.querySelectorAll('.slot').forEach(function(s){var k=w/1920;s.style.width=w+'px';s.style.height=(1080*k)+'px';s.firstElementChild.style.transform='scale('+k+')'})}
addEventListener('resize',fit);fit();
</script>
</body></html>'''
open(OUT+'/index.html','w').write(page);print('slide',len(parts),'immagini',len(used))
