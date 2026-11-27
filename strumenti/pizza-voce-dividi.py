#!/usr/bin/env python3
"""Divide la voce della presentazione «Pizza su Misura» in un file per schermata.

La voce si genera in un colpo solo (un audio con tutte le 16 frasi di
pizza/presentazione/voce/voce.json, nell'ordine): così tono e volume restano
uguali dall'inizio alla fine. Questo script trascrive l'audio con faster-whisper,
trova dove finisce ogni schermata, taglia nel silenzio fra una frase e l'altra e
scrive 01.mp3 … 16.mp3 accanto al JSON, aggiornando la durata ("ms").

Uso:
  pip install faster-whisper
  python3 strumenti/pizza-voce-dividi.py voce-intera.mp3 [NN=file.mp3 …]

«NN=file.mp3» sostituisce una schermata con un audio rifatto a parte
(es. 14=frase14.mp3). Serve ffmpeg. Il modello di trascrizione «small» si
scarica da Hugging Face la prima volta (con HF_HUB_DISABLE_XET=1 se il
download si blocca).
"""
import difflib, json, os, re, subprocess, sys, tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
CARTELLA = os.path.join(QUI, '..', 'pizza', 'presentazione', 'voce')
JSON = os.path.join(CARTELLA, 'voce.json')
FILTRO = ('highpass=f=60,loudnorm=I=-16:TP=-1.5:LRA=11,'
          'silenceremove=start_periods=1:start_threshold=-50dB,'
          'areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse')


def pcm(f):
    import numpy as np
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', f, '-f', 'f32le', '-ac', '1', '-ar', '16000', '-'])
    return np.frombuffer(raw, dtype=np.float32)


def durata_ms(f):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f])
    return round(float(out) * 1000)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    import numpy as np
    from faster_whisper import WhisperModel
    intera = sys.argv[1]
    sostituti = {int(k): v for k, v in (a.split('=', 1) for a in sys.argv[2:])}
    voci = json.load(open(JSON, encoding='utf-8'))
    a = pcm(intera)
    m = WhisperModel('small', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(a, language='it', word_timestamps=True, beam_size=5)
    W = [(w.word, w.start, w.end) for s in segs for w in s.words]
    norm = lambda x: re.sub(r'[^a-zà-ù0-9]', '', x.lower())
    ref, chi = [], []
    for i, v in enumerate(voci):
        for tok in re.split(r"[\s']+", v['testo']):
            if norm(tok):
                ref.append(norm(tok)); chi.append(i)
    sm = difflib.SequenceMatcher(None, ref, [norm(w[0]) for w in W], autojunk=False)
    r2h = {blk.a + k: blk.b + k for blk in sm.get_matching_blocks() for k in range(blk.size)}
    da, fine = [], []
    for i in range(len(voci)):
        idx = [r2h[k] for k in range(len(ref)) if chi[k] == i and k in r2h]
        da.append(W[min(idx)][1]); fine.append(W[max(idx)][2])
    # taglio nel punto più silenzioso fra la fine di una frase e l'inizio della successiva
    tagli = [0.0]
    for i in range(len(voci) - 1):
        x0, x1 = fine[i] - 0.15, da[i + 1] + 0.15
        best, bt = 1e9, (fine[i] + da[i + 1]) / 2
        for t in np.arange(x0, x1, 0.01):
            y = a[int(t * 16000):int((t + 0.03) * 16000)]
            e = float((y * y).mean()) if len(y) else 1e9
            if e < best:
                best, bt = e, t + 0.015
        tagli.append(bt)
    tagli.append(len(a) / 16000)
    with tempfile.TemporaryDirectory() as tmp:
        for i, v in enumerate(voci):
            n = i + 1
            mp3 = os.path.join(CARTELLA, v['file'])
            if n in sostituti:
                src = ['-i', sostituti[n]]
            else:
                src = ['-ss', f'{tagli[i]:.3f}', '-to', f'{tagli[i + 1]:.3f}', '-i', intera]
            subprocess.run(['ffmpeg', '-v', 'error', '-y', *src, '-af', FILTRO,
                            '-ar', '44100', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '96k', mp3], check=True)
            v['ms'] = durata_ms(mp3)
            print(f'{n:2d}  {v["ms"] / 1000:5.1f} s  {v["file"]}')
    with open(JSON, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(' ' + json.dumps(v, ensure_ascii=False) for v in voci) + '\n]\n')


if __name__ == '__main__':
    main()
