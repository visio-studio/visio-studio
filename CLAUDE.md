# VISIO Studio — Sito web

Sito vetrina one-page di **VISIO Studio**, studio di rendering architettonico a Roma.

- Repository GitHub: https://github.com/visio-studio/visio-studio
- **Sito live (GitHub Pages): https://visio-studio.github.io/visio-studio/** — ogni push su `main` aggiorna il sito pubblico dopo 1-2 minuti.
- **Hosting principale: Netlify** (attivo e collegato al repo GitHub, deploy automatico a ogni push su `main`). Il form contatti (`#ct-form`) usa Netlify Forms (`data-netlify="true"`, invio AJAX via fetch, honeypot `bot-field`, allegato max 8 MB) — funzionante, richieste nella tab "Forms" del pannello Netlify + notifica email. Il form NON funziona su GitHub Pages né in locale (mostra il messaggio d'errore con i contatti alternativi). GitHub Pages è da considerare deprecato: il sito di riferimento è quello su Netlify.

## Struttura del progetto

- **`index.html`** — l'UNICO file su cui lavorare. Contiene tutto: HTML, CSS (nel `<style>`) e JavaScript inline. Nessun build step, nessuna dipendenza: si apre direttamente nel browser.
- `index-backup.html` — copia di sicurezza, NON modificarla (la vera cronologia è su git).
- `img/journey/frame-0001.jpg … frame-0145.jpg` — sequenza di frame (12fps) per la sezione journey con scrub allo scroll (ha sostituito il vecchio video mp4).
- `img/room-360-tour.jpg` — panorama equirettangolare per la stanza 360° della sezione VR.
- `img/` — altre immagini (render, lidar, luci).
- I file `visio-journey*.mp4` eventualmente presenti in locale sono residui non più usati dal sito.
- `.nojekyll` — necessario per il deploy su GitHub Pages, non rimuoverlo.

## Contenuto della pagina (sezioni in ordine)

1. **Loader** con logo SVG VISIO animato "a disegno" (`.logo-draw`, stroke-dashoffset) + cursore custom dorato (`#cur-d`, `#cur-r`)
2. **Navbar** (`#nav`) con logo SVG (`.nl-logo`), cambia tema chiaro/scuro allo scroll
3. **Journey** (`#journey`) — canvas sticky (`#sv`) che disegna la sequenza di frame `img/journey/` legata allo scroll, testi che cambiano (`#stag`, `#stxt`), barra progresso (`#spb`)
4. **Intro servizi** (`#intro-servizi`)
5. **Render gallery** (`#render-gallery`) — strip orizzontale sticky con contatore e aggancio morbido allo scroll
6. **Sezione LiDAR** (`#lidar-section`, canvas `#lidar-cv`)
7. **Sito dedicato** (`#sito-dedicato`)
8. **Sezione VR** — zoom nel visore + stanza 360° navigabile: rendering WebGL con proiezione prospettica (`#vr-room-canvas`, panorama `img/room-360-tour.jpg`)
9. **Illuminazione** (`#illumino`) — confronto luci
10. **Statement** (`#statement`) + footer/contatti

## Stile e convenzioni

- Palette: oro `#C9A96E` su dark `#0A0A0A`, varianti light `#FAFAF8` (variabili CSS in `:root`)
- Font: Cormorant Garamond (titoli, classe `.serif`) + Inter (testo)
- CSS compatto su una riga per regola, ID/classi molto corti (es. `#stw`, `.nl`, `.ncta`) — mantieni questo stile
- Lingua del sito: italiano
- Testare sempre anche su mobile/Safari iOS (fix specifici WebKit e overscroll orizzontale bloccato)

## Workflow

- L'utente a volte lavora da un altro PC: **all'inizio della sessione fai sempre `git pull`** per essere sicuri di partire dall'ultima versione, e verifica con `git status` che non ci siano sorprese.
- Lavora direttamente su `index.html`
- Committa spesso con messaggi brevi in italiano (come lo storico esistente)
- Push su `origin main` quando l'utente lo chiede (il push pubblica sul sito live)
