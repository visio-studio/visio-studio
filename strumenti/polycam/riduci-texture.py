# texture delle scansioni per il visore: nomeN.src.jpg -> nomeN.jpg, lato massimo 2048 (scena-a-blocchi.mjs)
# uso: python -I riduci-texture.py cartella [lato]
import sys, glob, os
from PIL import Image
d = sys.argv[1]; lato = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
for f in sorted(glob.glob(os.path.join(d, '*.src.jpg'))):
    im = Image.open(f).convert('RGB'); s = im.size; im.thumbnail((lato, lato), Image.LANCZOS)
    o = f.replace('.src.jpg', '.jpg'); im.save(o, quality=82, optimize=True, progressive=True); os.remove(f)
    print(os.path.basename(o), s, '->', im.size, os.path.getsize(o) // 1024, 'KB')
