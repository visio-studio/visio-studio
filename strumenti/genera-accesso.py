#!/usr/bin/env python3
"""
Genera la riga da incollare nell'elenco ACCESSI dentro index.html.

Uso:
    python3 strumenti/genera-accesso.py hduudku /mariorossi

Stampa una riga tipo:
    {h:"9f2c…", u:"KxwR…"},   // Mario Rossi

Perche' cosi: nel sito non finiscono ne' il codice ne' la destinazione in chiaro.
Del codice si salva solo l'impronta SHA-256, e l'indirizzo e' cifrato con il codice
stesso: senza il codice giusto non e' ricavabile leggendo il sorgente.

Attenzione: e' una porta di cortesia, non una serratura. Chi conosce il codice
puo' passarlo ad altri, e chi arriva per caso sull'indirizzo lo apre comunque.
Per una protezione vera serve una password lato server.
"""
import base64
import hashlib
import sys


def impronta(codice: str) -> str:
    return hashlib.sha256(codice.strip().lower().encode()).hexdigest()


def cifra(url: str, codice: str) -> str:
    k = codice.strip().lower()
    grezzo = url.encode("utf-8")
    xor = bytes(b ^ ord(k[i % len(k)]) for i, b in enumerate(grezzo))
    return base64.b64encode(xor).decode()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    codice, url = sys.argv[1], sys.argv[2]
    if len(codice.strip()) < 6:
        print("Usa un codice di almeno 6 caratteri, altrimenti e' facile indovinarlo.")
        return 1
    print()
    print("Incolla questa riga nell'elenco ACCESSI dentro index.html:")
    print()
    print('  {h:"%s", u:"%s"},' % (impronta(codice), cifra(url, codice)))
    print()
    print("Codice da consegnare al cliente: %s" % codice.strip())
    print("Destinazione:                    %s" % url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
