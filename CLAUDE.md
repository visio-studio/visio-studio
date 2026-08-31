# VISIO Studio — Sito web

Sito vetrina one-page di **VISIO Studio**, studio di rendering architettonico a Roma.

- Repository GitHub: https://github.com/visio-studio/visio-studio
- **Sito live (GitHub Pages): https://visio-studio.github.io/visio-studio/** — ogni push su `main` aggiorna il sito pubblico dopo 1-2 minuti.
- **Hosting principale: Netlify — https://visiorender.it** (dominio Aruba puntato su Netlify dal 25 agosto 2026, certificato HTTPS dal 26; `visiorender.netlify.app` resta l'indirizzo tecnico). Netlify è collegato al repo GitHub: deploy automatico a ogni push su `main`. Il form contatti (`#ct-form`) usa Netlify Forms (`data-netlify="true"`, invio AJAX via fetch, honeypot `bot-field`, allegato max 8 MB) — funzionante, richieste nella tab "Forms" del pannello Netlify + notifica email. Il form NON funziona su GitHub Pages né in locale (mostra il messaggio d'errore con i contatti alternativi). GitHub Pages è da considerare deprecato: il sito di riferimento è quello su Netlify.

## Prima di iniziare

**Leggi `NOTE-DI-LAVORO.md`**: contiene lo stato del progetto, le cose ancora da
fare, le decisioni già prese e i tranelli tecnici di questo ambiente. Sta nel
repository apposta, così è disponibile da qualsiasi computer dopo un `git pull`.
Aggiornalo quando cambia qualcosa di strutturale.

## Struttura del progetto

- **`index.html`** — l'UNICO file su cui lavorare. Contiene tutto: HTML, CSS (nel `<style>`) e JavaScript inline. Nessun build step, nessuna dipendenza: si apre direttamente nel browser.
- `index-backup.html` — copia di sicurezza, NON modificarla (la vera cronologia è su git).
- `img/journey/frame-0001.jpg … frame-0145.jpg` — sequenza di frame (12fps) per la sezione journey con scrub allo scroll (ha sostituito il vecchio video mp4).
- `img/esterni-2/frame-0001.jpg … frame-0060.jpg` — sequenza dell'area esterna (ha sostituito `img/esterni`, che aveva la filigrana di Gemini). Se si rigenera, creare `esterni-3`: la cache `immutable` di `netlify.toml` servirebbe i vecchi file a chi c'è già stato.
- `img/room-360-tour.jpg` — panorama equirettangolare per la stanza 360° della sezione VR.
- `img/` — altre immagini (render, lidar, luci).
- I file `visio-journey*.mp4` eventualmente presenti in locale sono residui non più usati dal sito.
- `faq.html` — pagina Domande frequenti, con schema JSON-LD `FAQPage`.
- `preventivo.html` — configuratore di preventivo con fasce di prezzo (vedi `NOTE-DI-LAVORO.md`). I prezzi stanno tutti nel blocco `LISTINO` in cima al file.
- `esempio/index.html` — sito cliente di esempio (Villa Ferrara), in `noindex`.
- `strumenti/genera-accesso.py` — genera i codici cifrati dell'area riservata.
- `modelli/madia.glb` + `madia-3d.json` — la madia è un modello 3D vero, disegnato in WebGL scritto a mano (niente three.js). Il JSON si rigenera dal GLB con `strumenti/glb-a-json.py`; `strumenti/verifica-montaggio.py` controlla che i pezzi non si compenetrino durante il montaggio.
- `_test-madia.html` — banco di prova isolato della madia 3D (in `noindex`).
- `backup/esploso-madia-svg.html` — vecchia versione vettoriale dell'esploso madia, sostituita prima dai fotogrammi e ora dal modello 3D.
- `.nojekyll` — necessario per il deploy su GitHub Pages, non rimuoverlo.
- `favicon.svg`, `favicon.ico`, `apple-touch-icon.png` — icona del sito (la V dorata su tessera scura), collegata nel `<head>` di tutte le pagine. Se si rigenera, tenere gli stessi nomi: Google e i browser si aspettano indirizzi stabili.
- `netlify.toml` — configurazione del deploy su Netlify: cartella da pubblicare (la radice, nessun build step), cache lunga e `immutable` sulle sequenze di fotogrammi (`img/journey`, `img/esterni-2`) e intestazioni di sicurezza. Se si aggiunge o rigenera una sequenza, aggiornare la regola qui.
- `robots.txt`, `sitemap.xml`, `llms.txt` — file per l'indicizzazione da parte di motori di ricerca e crawler AI (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, ecc.). Se cambia l'URL del sito o l'elenco dei servizi, aggiornali insieme a `index.html`.

## SEO / ottimizzazione per motori AI (GEO)

- Il `<head>` contiene meta description, Open Graph, Twitter Card, canonical e uno schema JSON-LD `ProfessionalService` con nome, email, telefono, area servita e lista servizi (`makesOffer`). I contatti reali (email `info@visiorender.it`, telefono/WhatsApp `+39 342 668 4232`) sono allineati fra pagina, JSON-LD e `llms.txt`: se cambiano, aggiornali in tutti e tre. Non ci sono profili social (i segnaposto Instagram/LinkedIn sono stati rimossi): quando ci saranno account reali, aggiungerli in pagina e come array `sameAs` nel JSON-LD.
- C'è un `<h1>` e un blocco di riepilogo dei servizi, entrambi nascosti visivamente con la classe `.sr-only` (stessa tecnica standard di accessibilità: il contenuto esiste nel DOM per crawler/screen reader, ma non altera il design).
- I testi della sezione journey (`#stag`, `#stxt`) partono ora precompilati con il testo della prima fase (invece che vuoti), perché molti crawler AI non eseguono JavaScript e altrimenti non vedrebbero mai quel testo. La funzione di scrub in JS è stata adattata (controlla anche l'assenza della classe `.v`, non solo il testo) per gestire correttamente il caso in cui il testo sia già quello atteso.

## Contenuto della pagina (sezioni in ordine)

L'ordine segue una logica narrativa voluta: aggancio → panoramica servizi → prova (render) → metodo (LiDAR) → esperienza (VR/AR) → garanzia di completezza (documenti) → servizi di dettaglio (arredo, esterni, luce) → bonus finale (sito dedicato) → fiducia (stats, chi siamo) → chiusura (statement, contatti). Se si aggiungono nuove sezioni, inserirle nel punto della sequenza che rispetta questa logica, non in fondo per comodità.

1. **Loader** con logo SVG VISIO animato "a disegno" (`.logo-draw`, stroke-dashoffset) + cursore custom dorato (`#cur-d`, `#cur-r`). Si alza quando il primo fotogramma della journey è pronto (min 1,5 s, max 9 s), non a tempo fisso, e blocca lo scroll finché è su — vedi `NOTE-DI-LAVORO.md` §3 "Apertura del sito"
2. **Navbar** (`#nav`) — solo logo (cliccabile, torna in cima) e hamburger, a ogni larghezza. Voci e CTA vivono nel menu a schermo intero `#mmenu`
3. **Journey** (`#journey`) — canvas sticky (`#sv`) che disegna la sequenza di frame `img/journey/` legata allo scroll, testi che cambiano (`#stag`, `#stxt`), barra progresso (`#spb`)
4. **Intro servizi** (`#intro-servizi`) — griglia di 8 card cliccabili (`.sv-card`, attributo `data-go="#id-sezione"`) che scrollano alla sezione corrispondente. **L'ordine delle card deve rispecchiare l'ordine reale delle sezioni in pagina** (e i valori `--i:0..7` lo stile del loro effetto di comparsa in cascata) — se si sposta una sezione, riordinare anche la card qui.
5. **Render gallery** (`#render-gallery`) — strip orizzontale sticky con contatore e aggancio morbido allo scroll
6. **Sezione LiDAR** (`#lidar-section` + `#lidar-after`) — nuvola di punti 3D animata (canvas `#lidar-cv`) e il render finale
7. **VR scroll** (`#vr-scroll`) — zoom nel visore fino a entrare nella stanza 360° navigabile: rendering WebGL con proiezione prospettica, panorama `img/room-360-tour.jpg`
8. **VR/AR** (`#vrar`) — demo interattiva telefono-mirino sulla stanza (vuota/arredata)
9. **Documenti** (`#documenti`) — documentazione tecnica completa: planimetrie quotate, modello 3D, schemi impianti, computo metrico, render alta risoluzione, video
10. **Arredo** (`#arredo`) — montaggio della madia in 3D (canvas WebGL `#madia-cv` in `#esploso-wrap`, modello `madia-3d.json`) legato allo scroll, con le quattro finiture + i tre modi di servizio (fornitori, scheda tecnico-esecutiva, chiavi in mano) e il confronto prima/dopo render-realtà
11. **Esterni** (`#esterni`) — progettazione area esterna, timelapse allo scroll (`img/esterni-2`, caricato in differita poco prima di servire)
12. **Illuminazione** (`#illumino`) — confronto luci interattivo
13. **Sito dedicato** (`#sito-dedicato`) — presentato come servizio "bonus" verso fine pagina, non tra i servizi tecnici. L'accesso all'area riservata sta nel menu (vedi `NOTE-DI-LAVORO.md` §4)
14. **Stats + processo** (`#stats`) — otto numeri in tessere di vetro, con conteggio animato e comparsa a cascata (`.stat-i`, variabile `--i`)
15. **Recensioni** (`#recensioni`) — fascia di sei recensioni di clienti veri, che scorre da sola su desktop (in pausa al passaggio del mouse) e si scorre col dito su mobile. **Qui dentro non si scrivono testi inventati**: sarebbero recensioni false, vietate dal Codice del consumo
16. **Chi siamo** (`#chi`)
17. **Statement** (`#statement`) + **Contatti** (`#contatti`)

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
- **Un push = una build Netlify contata**: accumulare le modifiche della sessione e pubblicare una volta sola, committando in locale quanto si vuole
