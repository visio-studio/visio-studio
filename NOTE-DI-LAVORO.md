# Note di lavoro — VISIO Studio

Stato del progetto, decisioni prese e cose ancora da fare.
**Questo file sta nel repository**, quindi si sincronizza con `git pull` ed è
disponibile su qualsiasi computer. Aggiornalo quando cambia qualcosa di
strutturale: è la memoria condivisa del progetto.

Ultimo aggiornamento: 1 settembre 2026.

---

## 1. Cose da fare, in ordine di urgenza

### Legale — resta solo roba di pannello, non di codice
Fatto il 1 settembre: `privacy.html`, `cookie.html`, dati societari e P.IVA nel
piede di tutte le pagine, riga sull'informativa sotto i due moduli, font portati
in casa. Dettagli e ragionamento nel §7. Restano tre cose fuori dal repository:

- **La notifica dei moduli su Netlify** punta ancora al vecchio indirizzo:
  pannello → Forms → notifications → `info@visiorender.it`.
- **Roma o Aprilia?** La sede legale è ad Aprilia (LT), ma tutto il sito è
  costruito su "Roma": titolo, descrizione, `areaServed`, testi. Nello schema ho
  messo l'indirizzo vero come `address` e Roma+Lazio come `areaServed`, che è la
  lettura onesta (si opera a Roma, la società ha sede ad Aprilia). Se un domani
  si apre una scheda Google Business, l'indirizzo lì dev'essere quello vero,
  altrimenti la verifica salta.
- **I periodi di conservazione** nell'informativa (24 mesi per le richieste che
  non diventano incarico, 10 anni per i documenti contabili) sono una proposta
  ragionevole, non un dato che mi ha dato Matteo: se il commercialista dice
  altro, si cambia quella riga.

### Recensioni — fatte, ma se ne aggiungono altre si fa così
La fascia `#recensioni` (fra i numeri e "chi siamo") contiene **sei recensioni di
clienti veri**, date da Matteo il 31 agosto 2026. Nome puntato (`Marco R.`) per
non esporre il cognome; la seconda riga è il servizio di cui parla la recensione
stessa, ricavato dal testo — non inventarlo.

Le carte sono scritte **due volte** nell'HTML: la copia con `aria-hidden` serve a
far richiudere lo scorrimento senza salti. Se se ne aggiunge una, va aggiunta in
entrambi i gruppi. Su desktop la fascia scorre da sola e si ferma al passaggio
del mouse; dove non c'è il mouse l'animazione è spenta e si scorre col dito
(`@media (hover:none)`), altrimenti il testo scapperebbe mentre lo si legge.

**Non si scrivono recensioni inventate**, nemmeno "di esempio" e nemmeno con nomi
di fantasia credibili: chi legge le prende per vere ed è una pratica commerciale
ingannevole (Codice del consumo, art. 21-23). Servono clienti veri.

Non è stato messo il markup `AggregateRating` nel JSON-LD: Google non ammette i
"self-serving reviews" (recensioni sul proprio conto raccolte da sé) per i rich
snippet delle attività locali, e marcarle porterebbe una penalizzazione invece
che una stellina.

### La journey sfocata — mezzo passo fatto, manca il sorgente grande
**Il problema:** i fotogrammi sono **1152x864** e il canvas li disegna a tutto
schermo fino a 2x (su un portatile retina ~2880x1800). Vengono ingranditi due
volte e mezzo, ed e per questo che scorrendo si vedono molli. Nessuna riga di
codice puo inventare i pixel che mancano.

**Cosa e stato fatto il 31 agosto:** `img/journey-2` sostituisce `img/journey`.
Stessa misura e stessi 145 fotogrammi, ma con una **maschera di contrasto**
(PIL, `UnsharpMask(radius=1.1, percent=95, threshold=2)`, qualita 64,
`optimize`, `progressive`) applicata prima della compressione: il browser
ingrandisce un'immagine gia incisa e il risultato e visibilmente meno molle, a
parita di peso (8,2 MB contro 7,6). E un cerotto, non la cura.

    python3 -c "
    from PIL import Image, ImageFilter; import glob, os
    os.makedirs('img/journey-3', exist_ok=True)
    for f in sorted(glob.glob('img/journey-2/frame-*.jpg')):
        Image.open(f).convert('RGB').filter(ImageFilter.UnsharpMask(1.1,95,2)).save(
            'img/journey-3/'+os.path.basename(f),'JPEG',quality=64,optimize=True,progressive=True)"

**La cura vera:** rifare i fotogrammi da un sorgente piu grande.

- **Prima di generare un video nuovo, cercare l'mp4 originale** (`visio-journey*.mp4`
  sul Mac): se e a 1080p o piu, i fotogrammi attuali sono stati estratti
  rimpicciolendo, e basta ri-estrarli. Costa zero.
- Video nuovo, se serve: **almeno 1920 di larghezza**, meglio 2560, in **16:9**
  (il canvas ritaglia in "cover": un 4:3 viene tagliato e ingrandito ancora di
  piu), movimento di camera lento e continuo.
- **Controllare l'angolo in basso a destra**: i video generati con Gemini
  portano li il rombo della filigrana (e gia successo con `img/esterni`).
- Si estrae a 12 fps in una cartella **nuova** (`img/journey-3`) e si aggiorna la
  regola in `netlify.toml` piu i due riferimenti in `index.html`.
- Meglio **meno fotogrammi ma piu grandi**: 96 a 1920 pesano quanto 145 a 1152.

**Da questa sessione non si possono generare immagini ne video:** l'MCP
`nano-banana` sta sul Mac di Matteo e comunque fa solo immagini. Il video lo
produce lui.

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

**Il certificato HTTPS: stato bloccato, sbloccato il 26 agosto 2026.**
Per settimane Netlify ha risposto *"We could not provision a Let's Encrypt
certificate"* e il pulsante *Verify DNS configuration* non produceva alcun
effetto, nemmeno con il DNS ormai corretto. Non era un problema di DNS:
verificati e tutti a posto apex, www, assenza di CAA, assenza di DNSSEC,
nameserver, e nessun redirect nostro che intercettasse
`/.well-known/acme-challenge/` (`netlify.toml` non ha regole di redirect).

Era lo **stato interno di Netlify rimasto incastrato** dai tentativi falliti di
quando il dominio puntava ancora ad Aruba. La cura: *Options → Remove domain*
sul dominio primario e poi ri-aggiungerlo con *Add a domain → Add a domain you
already own*. Subito dopo *Verify DNS configuration* ha finalmente risposto
**"DNS verification was successful"**. Il sito non ha mai smesso di rispondere
durante l'operazione, e `www` si ricrea da solo come redirect.

L'emissione vera e propria puo restare indietro ancora un po': Let's Encrypt
limita i tentativi falliti (5 per host all'ora) e ne erano stati accumulati
molti. Se serve rifarlo: premere *Provision certificate* una volta sola e
aspettare, senza insistere, perche ogni tentativo fallito allunga l'attesa.

**Attenzione all'interfaccia di Netlify:** i dialoghi di conferma hanno una
dissolvenza in entrata, e un clic dato troppo presto viene assorbito senza fare
nulla — sembra che il pulsante non funzioni. Aspettare un paio di secondi e
cliccare il pulsante per riferimento, non a coordinate.

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

### Non pubblicare a ogni modifica

**Ogni push su `main` fa partire una ricostruzione su Netlify, e le build del
piano gratuito sono contate.** Accumulare tutte le modifiche di una sessione,
verificarle in locale, e fare **un solo push alla fine**. Committare in locale
quanto si vuole: e il push che costa, non il commit.


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
| Journey | `#journey` | 145 fotogrammi in `img/journey-2/` |
| LiDAR | `#lidar-section` | nuvola di punti su canvas |
| VR 360 | `#vr-scroll` (450vh) | panorama WebGL |
| Esterni | `#ex-wrap` (430vh) | 60 fotogrammi in `img/esterni-2/` |
| Sito dedicato | `#sd-wrap` | dispositivi + mini-sito |
| Madia | `#esploso-wrap` (620vh) | modello 3D WebGL (`madia-3d.json`) |

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

### La sequenza esterni e stata rifatta (26 agosto 2026)

I fotogrammi dei video generati con Gemini portano il **rombo del filigrana in
basso a destra**, a circa il 90% della larghezza e l'83% dell'altezza, sempre
nella stessa posizione. Nella vecchia `img/esterni` c'era in tutti e 120.
Controllate anche `img/journey` e le vecchie `img/madia`: quelle erano pulite.

`img/esterni-2` sostituisce `img/esterni`: **60 fotogrammi invece di 120**,
ritagliati a `1125x720` (il taglio del bordo destro porta via il rombo senza
inventare pixel) e ricompressi a qualita 72. Da **13,8 MB a 5,1 MB, -63%**,
senza perdere nulla di visibile: la sezione e a tutto schermo con ritaglio
"cover", quindi i bordi vengono comunque tagliati dal browser.

**La cartella e nuova apposta.** `netlify.toml` mette cache `immutable` su
queste sequenze: riscrivendo file con lo stesso nome, chi era gia stato sul
sito avrebbe continuato a vedere i vecchi. Se un giorno si rigenera di nuovo,
usare `esterni-3` e aggiornare la regola in `netlify.toml`.

`img/madia` (4,4 MB) e stata rimossa: non serviva piu dal passaggio al 3D.
Entrambe restano nella storia di git se dovessero servire.

**Se arriva un nuovo video generato con l'AI:** controllare sempre l'angolo in
basso a destra prima di spezzarlo in fotogrammi.

### Apertura del sito: cosa NON rifare

Il primo caricamento chiedeva **250 file per 20,5 MB**, perche journey (145
fotogrammi) ed esterni (120) partivano tutti insieme al primo istante. Il
fotogramma iniziale della journey — l'unico che serve subito — finiva in coda
dietro altri 264, e l'apertura restava nera. Peggio: il velo di caricamento
spariva dopo **2,2 secondi fissi** senza aspettare nulla, e nel frattempo la
pagina scorreva sotto, quindi l'utente si ritrovava gia a meta sito.

Ora:

- **Le sequenze lontane si caricano quando servono.** `img/esterni` parte da un
  IntersectionObserver con `rootMargin:'150% 0px'`, circa una schermata e mezza
  prima. Da sola vale 14 MB tolti all'apertura. Se si aggiunge una nuova
  sequenza pesante, differirla allo stesso modo — non lasciarla partire al
  caricamento.
- **La journey carica per priorita:** prima il fotogramma 0, poi uno ogni 12
  (cosi lo scrub e subito scorrevole), poi tutti gli altri, sei alla volta.
  Lo stato e in `window.VISIO_CARICA` (`primo`, `radi`, `radiTot`).
- **Il velo si alza quando `VISIO_CARICA.primo` e vero**, con un minimo di 1,5 s
  (il logo deve finire di disegnarsi) e un tetto di 9 s perche nessuno resti
  intrappolato. In piu c'e un salvagente in CSS (`@keyframes ldSalvagente`) che
  lo toglie a 12 s anche se il JavaScript non parte affatto.
- **Lo scorrimento e bloccato mentre il velo e su** (`overflow:hidden` su html e
  body) e alla chiusura si fa `scrollTo(0,0)`: si riparte sempre dall'inizio.
  Il gesto di scroll non muove la pagina, **spinge le due scritte** che scorrono
  in versi opposti sopra e sotto il logo. Sono solo testo: zero file da
  scaricare.

Misurato: da **20,5 MB a 10,8 MB** al primo caricamento, primo fotogramma a
117 ms invece che in coda.

**Come rimisurare** (in console, dopo un caricamento pulito):

    performance.getEntriesByType('resource').length
    performance.getEntriesByType('resource').reduce((s,e)=>s+(e.transferSize||0),0)/1048576

**Per ispezionare il velo** senza rete lenta: alzare temporaneamente `MIN` *e*
`MAX` nel blocco LOADER — alzare solo `MIN` non basta, chiude comunque `MAX`.

### La pagina preventivo (`preventivo.html`)

Configuratore: il cliente sceglie i servizi e ottiene una **forbice di prezzo**,
mai una cifra secca. Si arriva a `/preventivo` da tre punti:

1. **voce 04 del menu** a panino;
2. il **richiamo in vetro nella sezione contatti** della home, accanto al modulo,
   cosi chi e gia deciso sceglie fra scrivere e configurare;
3. **due link nella FAQ**, dentro le risposte "Quanto costa un render?" e
   "Come faccio ad avere un preventivo?" — che sono i momenti di massimo
   interesse su tutto il sito.

**Le risposte della FAQ sono state riscritte** perche contraddicevano il
listino: dicevano *"non lavoriamo a singola vista ma a progetto"* mentre il
configuratore prezza proprio a vista. Se un domani cambiano i prezzi, ricordarsi
che le cifre compaiono **anche nella FAQ**, sia nel testo visibile sia nello
schema JSON-LD per i motori — sono due copie, vanno cambiate tutte e due.

**Il meccanismo da capire prima di toccarla.** La forbice parte larga e **si
stringe a ogni risposta**: le fasce "non risposto" in `IGNOTO` contengono tutte
le risposte possibili, quindi rispondere puo solo restringere, mai allargare.
Se si aggiunge una nuova domanda, la sua fascia in `IGNOTO` deve contenere tutte
le opzioni, altrimenti il cliente vede il prezzo salire mentre risponde — che e
esattamente l'effetto opposto a quello voluto.

I moltiplicatori sono volutamente contenuti (±10-20%). Si moltiplicano fra loro:
allargandoli si ottengono massimi che nessun cliente riconosce come credibili.
La parte grossa del prezzo la decidono i servizi scelti e il numero di viste.

**I prezzi stanno tutti nel blocco `LISTINO` in cima al file**, insieme a
`SCONTO`, `MINIMO` e `IVA_ESCLUSA`. I prezzi dei servizi sono quelli dati da
Matteo il 26 agosto 2026 (`PREZZI_VERIFICATI = true`). L'IVA esclusa e confermata. Sconto (10%), minimo di progetto (300 €) e IVA esclusa sono stati
confermati il 26 agosto: `APERTI_CONFERMATI = true` e l'avviso giallo è sparito.
Se un domani si rimettono in discussione, rimetterlo a `false` e ricompare. Lo sconto in particolare finisce nero su bianco in pagina: e una promessa
al cliente, non un dettaglio.

**I pacchetti non sono la somma delle voci.** Ognuno porta in dote degli `extra`
compresi (alta risoluzione, formati social, PDF impaginato, giri di revisione,
archivio a fine lavori) che a listino non si comprano: e quello che li rende
convenienti rispetto al configurare a mano, altrimenti sceglierli non darebbe
alcun vantaggio al cliente. Gli extra crescono da Smart (3) a Chiavi in mano (7).

Quando si parte da un pacchetto, `stato.pacchetto` se lo ricorda: gli extra
compaiono nel riepilogo come "compreso" senza prezzo, e finiscono **nella bozza
che ci arriva per email**, marcati *da onorare nel preventivo*. Se si aggiungono
extra nuovi, ricordarsi che sono promesse contrattuali, non decorazione.

Attenzione al **minimo di progetto**: deve restare sotto al pacchetto Smart
(5 viste x 65 = 325), altrimenti la card mostra una cifra e il riepilogo un'altra.
Il minimo viene applicato sia al totale sia alle card dei pacchetti.

Il render di interni ha un **minimo di 5 viste** (`min:5`): scendere sotto quella
soglia con il "meno" toglie del tutto il servizio, invece di bloccarsi.

Altro che c'e dentro: quattro **pacchetti pronti** (Smart per una stanza sola,
Essenziale, Completo, Chiavi in mano) che riempiono il configuratore in un clic; l'elenco **"cosa ci serve da te"** che cambia in base alle scelte; i
**tempi indicativi**; la bozza **salvata in `localStorage`** (si ritrova
tornando); invio via **Netlify Forms** (`name="preventivo"`) con la bozza
completa in un campo nascosto.

### Le URL pubbliche puntano al dominio

Dal 26 agosto 2026 `canonical`, Open Graph, JSON-LD, `sitemap.xml`, `robots.txt`
e `llms.txt` usano `https://visiorender.it` e non piu `visiorender.netlify.app`:
altrimenti Google indicizza il sottodominio Netlify e il dominio vero resta un
doppione. Se si aggiunge una pagina, usarlo anche li.

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
(`img/journey-2/frame-0075.jpg` per i materiali interni, `frame-0145.jpg` per
esterni e luce), e per gli elaborati successivi passare **il precedente** —
è così che schema impianti e planimetria sono risultati coerenti fra loro.

**Il testo è il punto debole**: la planimetria è uscita in inglese e con una
camera duplicata, ed è servito un secondo giro. Un oggetto isolato su fondo
neutro riesce invece molto bene al primo colpo.

Le immagini vanno **sempre ricompresse** prima di pubblicarle: i render
originali del sito pesavano 1,5-2,4 MB l'uno a fronte di 200 KB necessari.
Qualità 85-88, `optimize`, `progressive`.

---

## 7. Legale, privacy e font

### Perché non c'è il banner dei cookie
Perché non serve. Il consenso si chiede per i cookie di profilazione e per gli
strumenti di statistica: **questo sito non ne ha nessuno**. Niente Analytics,
niente pixel, niente mappe o video incorporati. L'unico `localStorage` è la
bozza del preventivo, che resta sul dispositivo di chi la compila.

Mettere un banner "per sicurezza" costerebbe conversioni in cambio di niente.
**Se un domani si aggiunge Analytics o un pixel, il banner diventa obbligatorio**
e va aggiunto prima di pubblicare lo strumento, non dopo.

Quello che invece serve, e adesso c'è: informativa privacy (art. 13 GDPR, perché
i moduli raccolgono dati personali), pagina cookie, dati societari e partita IVA
in ogni piede di pagina — per una società con partita IVA è un obbligo di legge,
non un vezzo.

### I font stanno sul nostro dominio
Prima le pagine chiamavano `fonts.googleapis.com`: significa che l'indirizzo IP
di ogni visitatore finiva a Google prima ancora che decidesse di restare. È il
punto su cui in Europa sono arrivate le contestazioni. Ora i file stanno in
`font/` e il foglio di stile è `font/visio.css` — nessuna richiesta a terzi.

Sono solo i sottoinsiemi `latin` e `latin-ext` (cirillico, greco e vietnamita non
servono) e solo i pesi usati davvero: Cormorant Garamond 300/400 e corsivo
300/400, Inter 300/400/500. Se servisse un peso nuovo va aggiunto qui, altrimenti
il browser lo sintetizza e si vede.

Per rigenerarli (serve rete verso Google, una volta sola):

    curl -A "Mozilla/5.0" "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Inter:wght@300;400;500&display=swap" -o /tmp/gf.css

poi si tengono i blocchi `/* latin */` e `/* latin-ext */`, si scaricano i
`.woff2` in `font/` e si riscrivono le `@font-face` con `url(/font/nome.woff2)`.
`netlify.toml` mette su `/font/*` la cache `immutable`: i nomi non devono
cambiare, o chi è già stato sul sito continuerà a vedere i vecchi.

### Le due pagine
`privacy.html` e `cookie.html` girano sullo stesso guscio scuro delle FAQ, sono
indicizzabili e stanno in `sitemap.xml`. I dati del titolare compaiono in tre
posti — piede delle pagine, informativa, JSON-LD (`legalName`, `vatID`,
`address`): se cambiano, vanno cambiati in tutti e tre.

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
