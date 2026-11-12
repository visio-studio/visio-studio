#!/usr/bin/env python3
"""Genera un video con Seedance 2.5 tramite l'SDK ufficiale di Higgsfield.

    pip install -r strumenti/higgsfield/requirements.txt
    python3 strumenti/higgsfield/main.py

Le credenziali stanno in .env.local nella radice del repository (ignorato da git):

    HF_KEY=key-id:key-secret

Ogni esecuzione e' una generazione A PAGAMENTO.
Lo script non stampa mai la chiave e non dichiara riuscita una richiesta che non lo e'.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

RADICE = Path(__file__).resolve().parents[2]
load_dotenv(RADICE / '.env.local')          # prima di importare l'SDK, che legge HF_KEY dall'ambiente

import higgsfield_client                     # noqa: E402
from higgsfield_client.exceptions import CredentialsMissedError, HiggsfieldClientError  # noqa: E402

MODELLO = 'bytedance/seedance-2.5/text-to-video'
ARGOMENTI = {
    'prompt': 'A cinematic scene at sunset',
    'duration': 5,
    'resolution': '720p',
    'aspect_ratio': '16:9',
}


def url_video(risultato):
    """Cerca l'indirizzo del video nella risposta, senza darne per scontata la forma."""
    if not isinstance(risultato, dict):
        return None
    v = risultato.get('video')
    if isinstance(v, dict) and v.get('url'):
        return v['url']
    if isinstance(v, str):
        return v
    for chiave in ('videos', 'outputs', 'results'):
        elenco = risultato.get(chiave)
        if isinstance(elenco, list) and elenco:
            primo = elenco[0]
            if isinstance(primo, dict) and primo.get('url'):
                return primo['url']
            if isinstance(primo, str):
                return primo
    return risultato.get('url') or risultato.get('video_url')


def main() -> int:
    def in_coda(request_id):
        print(f'Richiesta accodata: {request_id}', flush=True)

    ultimo = [None]

    def aggiornamento(stato):
        nome = type(stato).__name__
        if nome != ultimo[0]:
            ultimo[0] = nome
            print(f'Stato: {nome}', flush=True)

    try:
        risultato = higgsfield_client.subscribe(
            MODELLO, arguments=ARGOMENTI,
            on_enqueue=in_coda, on_queue_update=aggiornamento,
        )
    except CredentialsMissedError:
        print('ERRORE: credenziali mancanti. Scrivi HF_KEY=key-id:key-secret in .env.local', file=sys.stderr)
        return 2
    except HiggsfieldClientError as e:
        print(f'ERRORE dall\'API Higgsfield: {e}', file=sys.stderr)
        return 1
    except Exception as e:                      # rete bloccata, DNS, timeout
        print(f'ERRORE di rete o imprevisto: {type(e).__name__}: {e}', file=sys.stderr)
        return 1

    stato = (risultato or {}).get('status') if isinstance(risultato, dict) else None
    if stato == 'failed':
        print('NON RIUSCITA: la generazione e\' fallita.', file=sys.stderr); return 1
    if stato == 'canceled':
        print('NON RIUSCITA: la richiesta e\' stata annullata.', file=sys.stderr); return 1
    if stato == 'nsfw':
        print('NON RIUSCITA: la richiesta e\' stata bloccata dalla moderazione.', file=sys.stderr); return 1
    if stato != 'completed':
        print(f'NON RIUSCITA: stato finale inatteso: {stato!r}', file=sys.stderr); return 1

    url = url_video(risultato)
    if not url:
        print('Completata, ma nella risposta non trovo l\'indirizzo del video. Chiavi presenti: '
              + ', '.join(sorted(risultato.keys())), file=sys.stderr)
        return 1
    print(f'Video: {url}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
