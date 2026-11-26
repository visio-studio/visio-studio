#!/usr/bin/env python3
"""Voce della presentazione «Pizza su Misura» (pizza/presentazione/).

Legge pizza/presentazione/voce/voce.json (un testo per schermata), genera con Piper
la voce italiana «Paola» e scrive un mp3 per schermata accanto al JSON, aggiornando
la durata in millisecondi (campo "ms") che la pagina usa per i tempi delle schermate.

Uso:
  pip install piper-tts
  # voce: https://huggingface.co/rhasspy/piper-voices/tree/main/it/it_IT/paola/medium
  python3 strumenti/pizza-voce.py percorso/it_IT-paola-medium.onnx [numeri schermate…]

Serve ffmpeg. Dopo aver cambiato i testi, rigenerare e ricaricare la pagina.
"""
import json, os, subprocess, sys, tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
CARTELLA = os.path.join(QUI, '..', 'pizza', 'presentazione', 'voce')
JSON = os.path.join(CARTELLA, 'voce.json')
LENTEZZA = '1.07'   # >1 parla più piano
PAUSA = '0.34'      # secondi di silenzio dopo ogni frase


def durata_ms(f):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f])
    return round(float(out) * 1000)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    modello = sys.argv[1]
    solo = {int(x) for x in sys.argv[2:]}
    voci = json.load(open(JSON, encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        for i, v in enumerate(voci, 1):
            if solo and i not in solo:
                continue
            wav = os.path.join(tmp, f'{i:02d}.wav')
            subprocess.run([sys.executable, '-m', 'piper', '-m', modello, '-f', wav,
                            '--length-scale', LENTEZZA, '--sentence-silence', PAUSA],
                           input=v['testo'].encode('utf-8'), check=True, capture_output=True)
            mp3 = os.path.join(CARTELLA, v['file'])
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav,
                            '-af', 'highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=7,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse',
                            '-ar', '44100', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '80k', mp3], check=True)
            v['ms'] = durata_ms(mp3)
            print(f'{i:2d}  {v["ms"]/1000:5.1f} s  {v["file"]}')
    with open(JSON, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(' ' + json.dumps(v, ensure_ascii=False) for v in voci) + '\n]\n')


if __name__ == '__main__':
    main()
