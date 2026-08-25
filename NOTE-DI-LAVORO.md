# Note di lavoro — VISIO Studio

Stato del progetto, decisioni prese e cose ancora da fare.
**Questo file sta nel repository**, quindi si sincronizza con `git pull` ed è
disponibile su qualsiasi computer. Aggiornalo quando cambia qualcosa di
strutturale: è la memoria condivisa del progetto.

Ultimo aggiornamento: 19 agosto 2026.

---

## 1. Cose da fare, in ordine di urgenza

### Netlify — ripubblicare il sito, fermo al 7 agosto
Online c'è ancora la versione di `c98017d` (7 agosto): i commit successivi sono
risultati *Skipped — account credit usage exceeded*, perché i crediti del piano
gratuito (300/mese, ciclo 14 luglio → 13 agosto) erano esauriti.

- **I crediti sono tornati il 13 agosto**, ma i deploy saltati restano *Skipped*,
  non in coda: **non ripartono da soli**. Per ripubblicare serve un nuovo push su
  `main` — il deploy parte da sé — oppure *Trigger deploy* dal pannello Netlify.
- I 18 deploy di sviluppo sono costati 270 dei 308 crediti consumati, circa 15
  l'uno. Il traffico ha inciso solo per 38. A regime, con 2-3 pubblicazioni al
  mese, il piano gratuito basta ampiamente, ma **ogni push su `main` è un deploy
  pagato**: meglio raggruppare le modifiche invece di pubblicare a raffica.
- Dal 19 agosto c'è **`netlify.toml`** nel repository: dichiara la cartella da
  pubblicare (la radice, nessun build step), mette la cache lunga sulle tre
  sequenze di fotogrammi (~27 MB, il grosso del traffico) e aggiunge le
  intestazioni di sicurezza. Le altre immagini restano sulla riconvalida
  predefinita, così una foto ricompressa si aggiorna al primo deploy.

### Dominio visiorender.it — collegato il 25 agosto 2026
Comprato su Aruba l'8 agosto insieme alla casella email. Dominio **attivo**
(`Status: ok`, scadenza 2027-08-08), posta configurata (`MX: mx.visiorender.it`).

**Record impostati** nel pannello Aruba (Dominio → Gestione DNS e Name Server,
che apre `dns-panel.aruba.it`):

| Tipo  | Nome | Valore                    |
|-------|------|---------------------------|
| A     | `@`  | `75.2.60.5` (era 62.149.128.40, parcheggio Aruba) |
| CNAME | `www`| `visiorender.netlify.app` (era visiorender.it)    |

Su Netlify il dominio era già stato aggiunto l'8 agosto (`visiorender.it`
principale, `www` che reindirizza).

**I record MX non sono stati toccati.** Nel pannello Aruba i record `mail` e
`mx` sono protetti (*Nessuna operazione*) e gli MX stanno in una scheda
separata: la posta non rischia nulla modificando A e CNAME.

**Correzione a una nota precedente: Aruba supporta i record ALIAS.** Netlify li
preferisce all'A record (`ALIAS @ → apex-loadbalancer.netlify.com`) perché
seguono automaticamente eventuali cambi di IP. Abbiamo usato l'A record, che è
il ripiego documentato da Netlify e funziona; **se un domani il sito smettesse
di rispondere sul dominio senza motivo apparente, la prima cosa da verificare è
se Netlify ha cambiato quell'IP** — e in quel caso conviene passare ad ALIAS.

**Propagazione completata il 25 agosto 2026.** I nameserver autoritativi Aruba
(`dns.technorail.com`) e i resolver pubblici (8.8.8.8, 1.1.1.1) rispondono
`75.2.60.5`, `www` punta a `visiorender.netlify.app`, gli MX sono intatti. Il
sito risponde in HTTP.

**Resta da fare: il certificato HTTPS.** Netlify non l'ha ancora emesso, quindi
`https://visiorender.it` non risponde (errore SSL, `curl` esce con codice 60).
Va sbloccato dal pannello Netlify → Domain management → HTTPS → *Verify DNS
configuration* e poi *Provision certificate*. Di solito parte da solo entro
un'ora dalla propagazione; se non parte, il pulsante lo forza.

Attenzione a una trappola nel diagnosticare: **il resolver di macOS tiene in
cache il vecchio IP Aruba** (`62.149.128.40`, server Microsoft-IIS) molto più a
lungo dei resolver pubblici. Se `curl` mostra ancora la pagina Aruba mentre
`dig` dice `75.2.60.5`, non è un problema di DNS: è la cache locale. Confrontare
sempre `dscacheutil -q host -a name visiorender.it` con `dig @8.8.8.8`, e
provare il sito con `curl --resolve visiorender.it:443:75.2.60.5`.

**Posta: attiva.** Il servizio è provvisionato e l'account amministratore
`postmaster@visiorender.it` esiste con password impostata (pannello Aruba →
Servizi di posta → Caselle di posta). Da lì, con il pulsante *Gestisci caselle*,
si creano e configurano gli indirizzi del dominio: quel passaggio richiede le
credenziali del postmaster, quindi lo fa Matteo.

Parametri per il client: `imaps.aruba.it` 993 SSL in arrivo, `smtps.aruba.it`
465 SSL in uscita, nome utente = **indirizzo email completo** (l'errore più
comune è metterci solo la parte prima della chiocciola). Se il client dà errore
di autenticazione con parametri giusti, verificare che **IMAP sia attivo**: su
Aruba è un servizio aggiuntivo, e senza si ha solo POP3 — inadatto a chi lavora
da più computer, perché i messaggi scaricati spariscono dagli altri dispositivi.


### Listino interno collegato al form preventivi
Richiesta esplicita di Matteo, da sviluppare insieme: un listino **non
pubblico** che permetta di stimare rapidamente un preventivo a partire da ciò
che il cliente indica nel form. Implica probabilmente di arricchire il form
contatti con i campi che alimentano la stima (tipo progetto, numero ambienti,
servizi richiesti). Al pubblico si continua a comunicare "preventivo su misura,
si va a progetto e non a singola vista".

### Madia — da migliorare
Il montaggio fotorealistico funziona (vedi §3) ma è incompleto:

- **Configuratore rimosso**: finiture, maniglia e base pilotavano i tracciati
  SVG e senza quelli lanciavano errori. Per riaverli servono immagini dedicate
  del mobile finito in noce, salvia e antracite (3 generazioni, ~18 crediti),
  da mostrare al click sul canvas. Le regole CSS (`.esp-sw`, `.esp-opt`,
  `.esp-swatches`, `.esp-optrow`) sono rimaste nel foglio di stile, pronte.
- Il **backup della versione vettoriale** con tutte le sue funzioni sta in
  `backup/esploso-madia-svg.html`.

### Pagine cliente vere
La struttura è pronta ma esiste solo l'esempio. Per ogni cliente: creare la
cartella con la sua pagina e generare il codice (vedi §4).

### Titoli disallineati nella gallery render
Le slide 02, 03 e 06 hanno titoli che non corrispondono alle foto: un soggiorno
intitolato "Vialetto d'Ingresso", la villa notturna "Bagno Padronale", la
terrazza "Cabina Armadio". Da sistemare quando si decidono i titoli giusti.

---

## 2. Come si lavora su questo progetto

- **`git pull` all'inizio di ogni sessione.** Matteo lavora da due computer.
- Si lavora su `index.html` (tutto inline: HTML, CSS, JS). Le pagine separate
  sono `faq.html` e `esempio/index.html`.
- Commit brevi in italiano, push su `origin main`.
- Quando cambia l'elenco dei servizi o l'URL, aggiornare **anche**
  `sitemap.xml`, `llms.txt` e il JSON-LD nel `<head>`.

### Il pannello di anteprima integrato non basta
Questo è il tranello che fa perdere più tempo. Nel Browser pane di Claude Code:

- `requestAnimationFrame` **non gira** e lo scroll con gesture va in timeout;
- gli screenshot vengono renderizzati a scroll ≈ 0 e diventano neri se la
  pagina è scrollata altrove.

Quindi **journey, LiDAR, VR 360, realtà aumentata, timelapse esterni e
montaggio madia lì non si animano.** Non è un bug del sito. Per verificarli
davvero serve un browser vero:

```bash
cd ~/Desktop/visio-studio && python3 -m http.server 4601
open -a "Google Chrome" http://localhost:4601/index.html
```

Il server configurato in `.claude/launch.json` **non funziona su questo Mac**
(permessi macOS sulla cartella Scrivania): il file è stato svuotato apposta.

Per verificare una singola sezione senza browser, il metodo che funziona è
estrarla in una pagina di prova temporanea, simulare il progresso
sovrascrivendo `wrap.getBoundingClientRect` e poi fare lo screenshot.

---

## 3. Sezioni animate allo scroll

Tutte seguono lo stesso schema: un contenitore alto più schermate, un figlio
`position:sticky`, e il progresso calcolato come
`-wrap.getBoundingClientRect().top / (wrap.offsetHeight - innerHeight)`.

| Sezione | Contenitore | Contenuto |
|---|---|---|
| Journey | `#journey` | 145 fotogrammi in `img/journey/` |
| LiDAR | `#lidar-section` | nuvola di punti su canvas |
| VR 360 | `#vr-scroll` (450vh) | panorama WebGL |
| Esterni | `#ex-wrap` (430vh) | 120 fotogrammi in `img/esterni/` |
| Sito dedicato | `#sd-wrap` | dispositivi + mini-sito |
| Madia | `#esploso-wrap` (340vh) | 96 fotogrammi in `img/madia/` |

**Usare sempre il ciclo `requestAnimationFrame`, non l'evento `scroll`**: è lo
schema della journey, l'unico collaudato su tutti i browser qui.

### Da video a fotogrammi
`ffmpeg` non è installato: si usa quello incluso in Python.

```bash
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -i ~/Desktop/video.mp4 -vf "fps=12" -q:v 3 img/CARTELLA/frame-%04d.jpg
```

12 fps è la densità giusta: 8 secondi danno 96 fotogrammi, circa 4 MB.
**Controllare le bande nere**: i video generati da AI escono spesso 4:3 dentro
un fotogramma 16:9. Se ci sono, verificare che il soggetto stia dentro l'area
utile anche nell'ultimo fotogramma e poi ritagliare **in modo uniforme** tutti i
fotogrammi. Riempire le bande estendendo lo sfondo produce striature: scartato.

### Il tour 360
I panorami generati da AI **non chiudono mai la sfera**: i due bordi non
combaciano. La cucitura si misura confrontando prima e ultima colonna con una
colonna a caso — in un 360 vero il rapporto è ~20×, in uno generato ~1×.

La dissolvenza circolare **non** è la soluzione: crea una banda a doppia
esposizione che si nota subito. Ha funzionato il **raccordo speculare**:
sostituire la coda con una copia specchiata della testa (~27°), ammorbidendo
solo l'innesto. Giuntura misurata: 0,0.

Di conseguenza la rotazione è limitata alla porzione pulita: **da -93° a +115°**
(`sweep = π·1.1556`, offset `+0.192`), che apre sulla vetrata con piscina e
chiude sul camino. FOV 75°, mappatura verticale piena.

**Attenzione al segno dello yaw**: lo shader usa `d.z = -1` e
`lon = atan(d.x, -d.z)`. Una riproiezione scritta a mano in Python con `dz=+f`
dà la **rotazione invertita** e porta a diagnosticare il lato sbagliato.

---

### La madia in 3D (in linea dal 26 agosto 2026, ha sostituito il video)

Il mobile e un modello vero: `modelli/madia.glb` (32 KB, esportato da SimLab,
2,04 x 0,77 x 0,54 m, 15 pezzi, gia con l'asse verticale giusto).
`strumenti/glb-a-json.py` ne estrae la geometria in `madia-3d.json` (21 KB)
applicando le trasformazioni dei nodi e ricentrando il mobile con la base a
Y = 0. Se il modello viene riesportato, rigenerare con:

    python3 strumenti/glb-a-json.py modelli/madia.glb madia-3d.json

Il renderer e **WebGL scritto a mano**, come il tour 360: niente three.js,
niente dipendenze. Vive in `index.html` dentro `#esploso-wrap`; `_test-madia.html`
resta come banco di prova isolato (in `noindex`).

Il montaggio occupa il primo 60% dello scroll della sezione, poi le quattro
finiture si succedono da sole. Barra e tasti **non sono comandi paralleli**:
trascinare la barra o cliccare una finitura sposta lo scroll, cosi posizione
nella pagina, barra e tasto acceso non possono mai discordare.

I 96 fotogrammi in `img/madia/` (4,4 MB) non sono piu usati da nessuna pagina:
si possono togliere dal deploy quando si vuole, restano comunque nella storia
di git. In tutto pesa 45 KB
contro i 4,4 MB dei 96 fotogrammi che sostituisce.

Tre inciampi gia pagati, da non ripetere:

- **`smoothstep(a,b,x)` con `a > b` e comportamento indefinito in GLSL** e su
  questa GPU produce NaN, che si vede come nero pieno. Per invertire una
  rampa scrivere `1.0 - smoothstep(b,a,x)`, mai scambiare i bordi.
- Un uniform impostato a **NaN** annerisce tutto il pezzo senza alcun errore in
  console: gli shader compilano, il programma linka, e sembra un bug di
  rendering. Se una superficie e nera, controllare prima i valori passati con
  `gl.uniform*`.
- Il piano dell'ombra a terra va disegnato con il **culling disattivato**,
  altrimenti sparisce a seconda di come e avvolto il quad.

Il modello **non ha maniglie**: l'opzione gola/pomello del vecchio
configuratore non e ricreabile finche non vengono aggiunti i gruppi
`maniglia-gola` e `maniglia-pomello`. Le tre ante si chiamano tutte
`anta 1` e vengono distinte dalla posizione lungo X.

Le essenze sono texture vere (`img/essenza-rovere.jpg`, `img/essenza-noce.jpg`,
512x512 perche la ripetizione specchiata in WebGL 1 richiede potenze di due).
Il modello non ha coordinate UV: si ricavano nello shader proiettando la
posizione sui tre assi, scegliendo per ogni faccia il verso in cui deve correre
la venatura. Salvia e antracite restano tinte piene: sono laccati, ed e giusto
cosi.

## 4. Area riservata clienti

Nel menu, sotto le voci numerate, c'è un blocco separato "Accedi al tuo sito":
il cliente digita il codice e viene portato alla sua pagina.

**I codici non sono in chiaro nel sorgente.** Si salva l'impronta SHA-256 del
codice e l'indirizzo cifrato con il codice stesso, così chi legge il sorgente
non ricava l'elenco dei clienti. Per aggiungerne uno:

```bash
python3 strumenti/genera-accesso.py CODICE /cartella-cliente
```

Stampa la riga da incollare nell'elenco `ACCESSI` dentro `index.html`.

**È una porta di cortesia, non una serratura**: chi ha il codice può girarlo, e
chi arriva sull'indirizzo lo apre comunque. Le pagine cliente hanno `noindex`
per non finire su Google. Per una protezione vera serve una password lato
server, quindi il piano Netlify a pagamento.

Codice pubblico di esempio: **`visio`** → `/esempio` (Villa Ferrara), suggerito
in chiaro nel menu stesso.

---

## 5. Generazione immagini

MCP `nano-banana` su **imgeditor.co**, chiave nel Portachiavi
(`imgeditor-api-key`). **Chiedere sempre a Matteo quale modello usare e
riportare i crediti residui prima di generare**, anche per i lotti.

- **`nano-banana-pro`**, ~6 crediti a 2K: l'unico da usare. Rispetta i
  riferimenti, regge bene il testo dentro le immagini.
- `nano-banana` senza suffisso **ignora le immagini di riferimento**.
- Non esiste uno strumento per generare video: quelli li produce Matteo.

**Il metodo che funziona**: passare come riferimento i frame della villa
(`img/journey/frame-0075.jpg` per i materiali interni, `frame-0145.jpg` per
esterni e luce), e per gli elaborati successivi passare **il precedente** —
è così che schema impianti e planimetria sono risultati coerenti fra loro.

**Il testo è il punto debole**: la planimetria è uscita in inglese e con una
camera duplicata, ed è servito un secondo giro. Un oggetto isolato su fondo
neutro riesce invece molto bene al primo colpo.

Le immagini vanno **sempre ricompresse** prima di pubblicarle: i render
originali del sito pesavano 1,5-2,4 MB l'uno a fronte di 200 KB necessari.
Qualità 85-88, `optimize`, `progressive`.

---

## 6. Decisioni prese, per non rimetterle in discussione

- **Menu a hamburger su tutte le larghezze**, anche desktop. Navbar ridotta a
  logo e hamburger; le voci e la CTA vivono nel menu a schermo intero.
- **Niente voce "Contatti"** nel menu: era ridondante con "Richiedi info".
- **Il modello 3D sorgente non è compreso** nella consegna: il servizio è di
  visualizzazione. Dichiarato nelle FAQ, e coerente con la scheda "Modello 3D
  completo" nella sezione documenti — che prima prometteva erroneamente i file
  OBJ/FBX/nativo ed è stata corretta l'8 agosto. **Se si tocca quella scheda,
  non reintrodurre la promessa dei file sorgente.**
- **Il 360 mantiene FOV 75° e mappatura piena.** Una correzione della curvatura
  a 115° era stata provata e scartata: raddrizzava le linee ma zoomava,
  restringendo il campo visivo.
- **Immagini reali al posto delle illustrazioni** dove possibile: fatto per
  documentazione, realtà aumentata, esterni e madia.
